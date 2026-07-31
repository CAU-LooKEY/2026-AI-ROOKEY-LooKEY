import copy
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from app.services.component_rules import supported_component_pins


class CircuitContractError(ValueError):
    pass


@dataclass(frozen=True)
class _PartReference:
    canonical_id: str
    component_key: str
    pins: frozenset[str]
    aliases: frozenset[str]


def _normalized_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise CircuitContractError(f"{field_name} must be an array.")
    return value


def _canonical_pin(pin: Any, part: _PartReference) -> str:
    if not isinstance(pin, str) or not pin.strip():
        return ""

    normalized_pin = _normalized_identifier(pin)
    matches = [
        allowed_pin
        for allowed_pin in part.pins
        if _normalized_identifier(allowed_pin) == normalized_pin
    ]
    return matches[0] if len(matches) == 1 else pin


def _resolve_part_reference(
    raw_id: Any,
    raw_pin: Any,
    *,
    connection_id: str,
    endpoint_name: str,
    alias_index: dict[str, list[_PartReference]],
    parts: list[_PartReference],
) -> _PartReference:
    if not isinstance(raw_id, str) or not raw_id.strip():
        raise CircuitContractError(
            f"Connection '{connection_id}' has an empty {endpoint_name} part id."
        )

    normalized_id = _normalized_identifier(raw_id)
    candidates = list(alias_index.get(normalized_id, []))

    # Repair common variants such as led_1 versus led-5mm-blue-1 only when the
    # result is unambiguous. Pin compatibility is used as a second constraint.
    if not candidates and len(normalized_id) >= 3:
        candidates = [
            part
            for part in parts
            if any(
                alias.startswith(normalized_id) or normalized_id.startswith(alias)
                for alias in part.aliases
                if len(alias) >= 3
            )
        ]

    if isinstance(raw_pin, str):
        normalized_pin = _normalized_identifier(raw_pin)
        pin_matches = [
            part
            for part in candidates
            if any(
                _normalized_identifier(allowed_pin) == normalized_pin
                for allowed_pin in part.pins
            )
        ]
        if pin_matches:
            candidates = pin_matches

    unique_candidates = {
        candidate.canonical_id: candidate for candidate in candidates
    }
    if len(unique_candidates) == 1:
        return next(iter(unique_candidates.values()))

    known_ids = ", ".join(part.canonical_id for part in parts)
    if not unique_candidates:
        raise CircuitContractError(
            f"Connection '{connection_id}' {endpoint_name} references unknown "
            f"part id '{raw_id}'. Known part ids: {known_ids}."
        )

    candidate_ids = ", ".join(sorted(unique_candidates))
    raise CircuitContractError(
        f"Connection '{connection_id}' {endpoint_name} part id '{raw_id}' is "
        f"ambiguous. Candidate part ids: {candidate_ids}."
    )


def normalize_circuit_contract(circuit_data: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic circuit document with canonical part references."""
    if not isinstance(circuit_data, dict):
        raise CircuitContractError("Circuit response must be a JSON object.")

    normalized = copy.deepcopy(circuit_data)
    circuit = normalized.get("circuit")
    if not isinstance(circuit, dict):
        raise CircuitContractError("circuit must be an object.")

    raw_parts = _require_list(circuit.get("parts"), "circuit.parts")
    raw_connections = _require_list(
        circuit.get("connections"), "circuit.connections"
    )
    known_pins = supported_component_pins()
    occurrence_by_component: dict[str, int] = defaultdict(int)
    part_references: list[_PartReference] = []
    alias_index: dict[str, list[_PartReference]] = defaultdict(list)

    for index, raw_part in enumerate(raw_parts):
        if not isinstance(raw_part, dict):
            raise CircuitContractError(
                f"circuit.parts[{index}] must be an object."
            )

        component_key = raw_part.get("componentKey")
        if not isinstance(component_key, str) or not component_key.strip():
            raise CircuitContractError(
                f"circuit.parts[{index}].componentKey must be a non-empty string."
            )

        occurrence_by_component[component_key] += 1
        canonical_id = (
            f"{component_key}-{occurrence_by_component[component_key]}"
        )
        original_id = raw_part.get("id")
        label = raw_part.get("label")
        aliases = {
            _normalized_identifier(value)
            for value in (
                canonical_id,
                component_key,
                f"{component_key}-{occurrence_by_component[component_key]}",
                original_id,
                label,
            )
            if isinstance(value, str) and value.strip()
        }
        aliases.discard("")

        part = _PartReference(
            canonical_id=canonical_id,
            component_key=component_key,
            pins=frozenset(known_pins.get(component_key, set())),
            aliases=frozenset(aliases),
        )
        raw_part["id"] = canonical_id
        part_references.append(part)
        for alias in aliases:
            alias_index[alias].append(part)

    for index, raw_connection in enumerate(raw_connections):
        if not isinstance(raw_connection, dict):
            raise CircuitContractError(
                f"circuit.connections[{index}] must be an object."
            )

        connection_id = raw_connection.get("id")
        if not isinstance(connection_id, str) or not connection_id.strip():
            connection_id = f"connection-{index + 1}"
            raw_connection["id"] = connection_id

        for endpoint_name, pin_name in (
            ("source", "sourcePin"),
            ("target", "targetPin"),
        ):
            raw_part_id = raw_connection.get(endpoint_name)
            raw_pin = raw_connection.get(pin_name)
            try:
                part = _resolve_part_reference(
                    raw_part_id,
                    raw_pin,
                    connection_id=connection_id,
                    endpoint_name=endpoint_name,
                    alias_index=alias_index,
                    parts=part_references,
                )
                repaired_pin = _canonical_pin(raw_pin, part)
            except CircuitContractError as reference_error:
                # K-EXAONE occasionally swaps an endpoint's part id and pin.
                # Repair only when both swapped values satisfy known contracts.
                try:
                    swapped_part = _resolve_part_reference(
                        raw_pin,
                        raw_part_id,
                        connection_id=connection_id,
                        endpoint_name=endpoint_name,
                        alias_index=alias_index,
                        parts=part_references,
                    )
                    swapped_pin = _canonical_pin(raw_part_id, swapped_part)
                except CircuitContractError:
                    raise reference_error
                if swapped_pin not in swapped_part.pins:
                    raise reference_error
                part = swapped_part
                repaired_pin = swapped_pin

            raw_connection[endpoint_name] = part.canonical_id
            raw_connection[pin_name] = repaired_pin

            if raw_connection[pin_name] not in part.pins:
                allowed_pins = ", ".join(sorted(part.pins)) or "(none)"
                raise CircuitContractError(
                    f"Connection '{connection_id}' {endpoint_name} pin "
                    f"'{raw_connection[pin_name]}' is invalid for part "
                    f"'{part.canonical_id}' ({part.component_key}). Allowed pins: "
                    f"{allowed_pins}."
                )

    return normalized

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
COMPONENT_RULES_PATH = (
    REPOSITORY_ROOT / "assets_db/validation_rules/component-rules.json"
)


class ComponentRulesError(RuntimeError):
    pass


@lru_cache
def load_component_rules() -> dict[str, dict[str, Any]]:
    try:
        with COMPONENT_RULES_PATH.open(encoding="utf-8") as source:
            document = json.load(source)
    except (OSError, ValueError) as exc:
        raise ComponentRulesError(
            f"Could not load component rules: {COMPONENT_RULES_PATH}"
        ) from exc

    components = document.get("components")
    if not isinstance(components, dict) or not components:
        raise ComponentRulesError("Component rules must define a components object.")

    for slug, rule in components.items():
        pins = rule.get("pins")
        if not isinstance(pins, list) or not pins or len(pins) != len(set(pins)):
            raise ComponentRulesError(
                f"Component {slug} must define unique pin names."
            )
        unknown = {
            pin
            for group in rule.get("capabilityGroups", {}).values()
            for pin in group
            if pin not in pins
        }
        if unknown:
            raise ComponentRulesError(
                f"Component {slug} capability groups reference unknown pins: "
                f"{sorted(unknown)}"
            )
        requirement_pins = set(rule.get("pinRequirements", {}))
        if not requirement_pins <= set(pins):
            raise ComponentRulesError(
                f"Component {slug} requirements reference unknown pins: "
                f"{sorted(requirement_pins - set(pins))}"
            )
        internal_pins = {
            pin
            for group in rule.get("internalConnections", [])
            for pin in group
        }
        if not internal_pins <= set(pins):
            raise ComponentRulesError(
                f"Component {slug} internal connections reference unknown pins: "
                f"{sorted(internal_pins - set(pins))}"
            )
        if rule.get("mountingMode") not in {"free", "breadboard"}:
            raise ComponentRulesError(
                f"Component {slug} has an unsupported mounting mode."
            )
        if rule.get("pinConnectorGender") not in {"male", "female"}:
            raise ComponentRulesError(
                f"Component {slug} has an unsupported connector gender."
            )
    return components


def component_rule(asset_slug: str) -> dict[str, Any]:
    try:
        return load_component_rules()[asset_slug]
    except KeyError as exc:
        raise ComponentRulesError(f"Unsupported component: {asset_slug}") from exc


def supported_component_pins() -> dict[str, set[str]]:
    return {
        slug: set(rule["pins"])
        for slug, rule in load_component_rules().items()
    }


def supported_component_keys() -> tuple[str, ...]:
    return tuple(sorted(load_component_rules()))


def supported_pin_keys() -> tuple[str, ...]:
    return tuple(sorted({
        pin
        for rule in load_component_rules().values()
        for pin in rule["pins"]
    }))


def component_category(asset_slug: str) -> str:
    return str(component_rule(asset_slug).get("category", "unknown"))


def component_mounting_mode(asset_slug: str) -> str:
    return str(component_rule(asset_slug).get("mountingMode", "breadboard"))


def required_wire_connector(asset_slug: str) -> str:
    component_gender = component_rule(asset_slug).get("pinConnectorGender", "male")
    if component_gender == "male":
        return "female"
    if component_gender == "female":
        return "male"
    raise ComponentRulesError(
        f"Unsupported connector gender for {asset_slug}: {component_gender}"
    )


def pin_capabilities(asset_slug: str, pin_key: str) -> set[str]:
    rule = component_rule(asset_slug)
    return {
        capability
        for capability, pins in rule.get("capabilityGroups", {}).items()
        if pin_key in pins
    }


def component_prompt_catalog() -> str:
    rows = []
    for slug, rule in sorted(load_component_rules().items()):
        rows.append(f"- {slug}: {', '.join(rule['pins'])}")
    return "\n".join(rows)

#!/usr/bin/env python3
"""Run all asset checks and emit JSON and Markdown approval reports."""

from __future__ import annotations

import argparse
import json
import math
import os
import struct
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = REPO_ROOT / "assets_db" / "3d_models"
METADATA_ROOT = ASSET_ROOT / "component_metadata"
DEFAULT_REPORT_DIR = REPO_ROOT / "artifacts" / "asset-validation"
PIN_POSITION_TOLERANCE_METER = 2e-6
DIMENSION_ABSOLUTE_TOLERANCE_MM = 0.25
DIMENSION_RELATIVE_TOLERANCE = 0.02

CHECKS = (
    ("glb-models", "GLB 파일·manifest 무결성", "validate_3d_models.py"),
    ("component-metadata", "컴포넌트 3D 메타데이터 규격", "validate_component_3d_metadata.py"),
    ("pin-anchors", "3D 핀 앵커 bounds", "validate_3d_pin_anchors.py"),
    ("pin-coordinates", "2D 핀 좌표", "validate_pin_coordinates.py"),
    ("breadboard-half", "2.54mm 브레드보드·점퍼 호환성", "validate_breadboard_half_candidate.py"),
    ("knowledge-base", "부품 지식 데이터", "validate_knowledge_base.py"),
)


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    asset_slug: str | None = None
    path: str | None = None


@dataclass
class CheckResult:
    id: str
    name: str
    status: str
    duration_seconds: float
    output: str = ""
    findings: list[Finding] = field(default_factory=list)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def relative(path: Path, root: Path = REPO_ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def read_glb_nodes(path: Path) -> dict[str, list[float]]:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("GLB file is smaller than its required header")
    magic, version, declared_length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(raw):
        raise ValueError("invalid GLB 2.0 header or declared length")
    json_length, json_type = struct.unpack_from("<II", raw, 12)
    if json_type != 0x4E4F534A:
        raise ValueError("first GLB chunk is not JSON")
    document = json.loads(raw[20 : 20 + json_length])
    return {
        node["name"]: node.get("translation", [0.0, 0.0, 0.0])
        for node in document.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("name"), str)
    }


def metadata_documents(root: Path = METADATA_ROOT) -> dict[str, list[tuple[str, Path, dict]]]:
    documents: dict[str, list[tuple[str, Path, dict]]] = {}
    for directory_name, status in (("candidates", "candidate"), ("approved", "approved")):
        directory = root / directory_name
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.json")):
            try:
                data = load_json(path)
            except (OSError, json.JSONDecodeError):
                continue
            slug = data.get("componentSlug")
            if isinstance(slug, str):
                documents.setdefault(slug, []).append((status, path, data))
    return documents


def changed_slugs(paths: Iterable[str], manifest: list[dict]) -> set[str]:
    slugs: set[str] = set()
    by_path = {
        f"assets_db/{item['storage_path']}": item["component_slug"]
        for item in manifest
    }
    for raw_path in paths:
        path = raw_path.strip().replace("\\", "/")
        if path in by_path:
            slugs.add(by_path[path])
        marker = "assets_db/3d_models/component_metadata/"
        if path.startswith(marker) and path.endswith(".json"):
            parts = path[len(marker) :].split("/")
            if parts[0] == "candidates" and len(parts) >= 3:
                slugs.add(parts[1])
            elif parts[0] == "approved" and len(parts) == 2:
                slugs.add(Path(parts[1]).stem)
    return slugs


def discover_changed_files(base_ref: str | None, explicit: list[str], root: Path) -> list[str]:
    if explicit:
        return sorted(set(explicit))
    if not base_ref:
        return []
    completed = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base_ref}...HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "git diff failed")
    return sorted({line for line in completed.stdout.splitlines() if line})


def run_script(check_id: str, name: str, script: str, root: Path) -> CheckResult:
    started = time.monotonic()
    completed = subprocess.run(
        [sys.executable, str(root / "assets_db" / "db_scripts" / script)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    output = "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    )
    return CheckResult(
        id=check_id,
        name=name,
        status="passed" if completed.returncode == 0 else "failed",
        duration_seconds=round(time.monotonic() - started, 3),
        output=output,
        findings=[] if completed.returncode == 0 else [
            Finding("error", "CHECK_FAILED", output or f"{script} failed")
        ],
    )


def validate_coverage(
    mode: str, changed_files: list[str], root: Path = REPO_ROOT
) -> CheckResult:
    started = time.monotonic()
    asset_root = root / "assets_db" / "3d_models"
    manifest = load_json(asset_root / "glb_model_manifest.json")
    documents = metadata_documents(asset_root / "component_metadata")
    manifest_slugs = {item["component_slug"] for item in manifest}
    disk_glbs = {path.stem: path for path in (asset_root / "glb").glob("*.glb")}
    findings: list[Finding] = []

    for slug in sorted(set(disk_glbs) - manifest_slugs):
        findings.append(Finding(
            "error", "GLB_NOT_IN_MANIFEST",
            "GLB 파일이 manifest에 등록되지 않았습니다.",
            slug, relative(disk_glbs[slug], root),
        ))
    for item in manifest:
        slug = item["component_slug"]
        if slug not in disk_glbs:
            findings.append(Finding(
                "error", "MANIFEST_GLB_MISSING",
                "manifest가 가리키는 GLB 파일이 없습니다.",
                slug, item.get("storage_path"),
            ))

    targets = manifest_slugs if mode == "release" else changed_slugs(changed_files, manifest)
    for slug in sorted(manifest_slugs):
        statuses = {status for status, _, _ in documents.get(slug, [])}
        if mode == "release" and "approved" not in statuses:
            findings.append(Finding(
                "error", "APPROVED_METADATA_REQUIRED",
                "릴리스 대상 GLB에는 approved 메타데이터가 필요합니다.", slug,
            ))
        elif slug in targets and not statuses:
            findings.append(Finding(
                "error", "METADATA_REQUIRED",
                "변경된 GLB에는 candidate 또는 approved 메타데이터가 필요합니다.", slug,
            ))
        elif not statuses:
            findings.append(Finding(
                "warning", "METADATA_MISSING_BASELINE",
                "기존 GLB에 candidate/approved 메타데이터가 아직 없습니다.", slug,
            ))

    has_errors = any(item.severity == "error" for item in findings)
    return CheckResult(
        "asset-coverage", "GLB·manifest·승인 메타데이터 대응",
        "failed" if has_errors else "passed",
        round(time.monotonic() - started, 3), findings=findings,
    )


def vectors_close(left: list[float], right: list[float]) -> bool:
    return len(left) == len(right) == 3 and all(
        math.isclose(float(a), float(b), rel_tol=0, abs_tol=PIN_POSITION_TOLERANCE_METER)
        for a, b in zip(left, right, strict=True)
    )


def validate_glb_pin_nodes(root: Path = REPO_ROOT) -> CheckResult:
    started = time.monotonic()
    documents = metadata_documents(
        root / "assets_db" / "3d_models" / "component_metadata"
    )
    findings: list[Finding] = []
    checked = 0
    for slug, entries in sorted(documents.items()):
        for _, metadata_path, data in entries:
            glb_value = data.get("asset", {}).get("path")
            if not isinstance(glb_value, str):
                continue
            glb_path = root / glb_value
            try:
                nodes = read_glb_nodes(glb_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                findings.append(Finding(
                    "error", "GLB_NODE_READ_FAILED", str(exc),
                    slug, relative(glb_path, root),
                ))
                continue
            for pin in data.get("pins", []):
                checked += 1
                node_name = pin.get("nodeName")
                if node_name not in nodes:
                    findings.append(Finding(
                        "error", "PIN_NODE_MISSING",
                        f"GLB 내부에 {node_name} 노드가 없습니다.",
                        slug, relative(metadata_path, root),
                    ))
                elif not vectors_close(nodes[node_name], pin.get("position", [])):
                    findings.append(Finding(
                        "error", "PIN_POSITION_MISMATCH",
                        f"{node_name}의 GLB 좌표와 메타데이터 좌표가 다릅니다.",
                        slug, relative(metadata_path, root),
                    ))
    has_errors = any(item.severity == "error" for item in findings)
    return CheckResult(
        "glb-pin-nodes", "GLB pin_* 노드·메타데이터 좌표 비교",
        "failed" if has_errors else "passed",
        round(time.monotonic() - started, 3),
        f"Compared {checked} metadata pins with embedded GLB pin nodes.",
        findings,
    )


def validate_physical_dimensions(root: Path = REPO_ROOT) -> CheckResult:
    """Compare declared real-world dimensions with measured manifest bounds."""
    started = time.monotonic()
    asset_root = root / "assets_db" / "3d_models"
    manifest = load_json(asset_root / "glb_model_manifest.json")
    manifest_by_slug = {item["component_slug"]: item for item in manifest}
    documents = metadata_documents(asset_root / "component_metadata")
    findings: list[Finding] = []
    checked = 0
    for slug, entries in sorted(documents.items()):
        manifest_item = manifest_by_slug.get(slug)
        if not manifest_item:
            continue
        size = manifest_item.get("bounds", {}).get("size")
        if not isinstance(size, list) or len(size) != 3:
            continue
        for _, metadata_path, data in entries:
            asset = data.get("asset", {})
            runtime = data.get("coordinateSystems", {}).get("runtime", {})
            dimensions = data.get("physicalDimensions", {})
            if (
                asset.get("scaleStatus") != "real-world"
                or runtime.get("unit") != "meter"
                or dimensions.get("measurementScope") == "body-only"
            ):
                continue
            checked += 1
            measured = {
                "width": float(size[0]) * 1000,
                "height": float(size[1]) * 1000,
                "depth": float(size[2]) * 1000,
            }
            for dimension_name, measured_mm in measured.items():
                declared = dimensions.get(dimension_name)
                if not isinstance(declared, (int, float)) or isinstance(declared, bool):
                    continue
                tolerance = max(
                    DIMENSION_ABSOLUTE_TOLERANCE_MM,
                    abs(measured_mm) * DIMENSION_RELATIVE_TOLERANCE,
                )
                if not math.isclose(
                    float(declared),
                    measured_mm,
                    rel_tol=0,
                    abs_tol=tolerance,
                ):
                    findings.append(Finding(
                        "error",
                        "PHYSICAL_DIMENSION_MISMATCH",
                        (
                            f"{dimension_name} 선언값 {declared:.3f}mm와 "
                            f"GLB bounds 측정값 {measured_mm:.3f}mm가 다릅니다."
                        ),
                        slug,
                        relative(metadata_path, root),
                    ))
    has_errors = any(item.severity == "error" for item in findings)
    return CheckResult(
        "physical-dimensions",
        "실제 크기·단위와 GLB bounds 비교",
        "failed" if has_errors else "passed",
        round(time.monotonic() - started, 3),
        f"Compared physical dimensions for {checked} real-world metadata files.",
        findings,
    )


def report_payload(
    mode: str, changed_files: list[str], results: list[CheckResult]
) -> dict:
    errors = sum(
        item.severity == "error" for result in results for item in result.findings
    )
    warnings = sum(
        item.severity == "warning" for result in results for item in result.findings
    )
    failed = sum(result.status == "failed" for result in results)
    return {
        "schemaVersion": "1.0",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "status": "failed" if errors or failed else "passed",
        "summary": {
            "checks": len(results),
            "passed": sum(result.status == "passed" for result in results),
            "failed": failed,
            "errors": errors,
            "warnings": warnings,
        },
        "changedFiles": changed_files,
        "checks": [
            {
                **asdict(result),
                "findings": [asdict(item) for item in result.findings],
            }
            for result in results
        ],
    }


def markdown_report(payload: dict) -> str:
    summary = payload["summary"]
    mark = "✅" if payload["status"] == "passed" else "❌"
    lines = [
        "# 에셋 검증 리포트",
        "",
        f"- 결과: {mark} **{payload['status'].upper()}**",
        f"- 모드: `{payload['mode']}`",
        f"- 검사: {summary['passed']}/{summary['checks']} 통과",
        f"- 오류: {summary['errors']}",
        f"- 경고: {summary['warnings']}",
        "",
        "| 검사 | 결과 | 시간 |",
        "| --- | --- | ---: |",
    ]
    for result in payload["checks"]:
        icon = "✅" if result["status"] == "passed" else "❌"
        lines.append(
            f"| {result['name']} | {icon} {result['status']} | "
            f"{result['duration_seconds']:.3f}s |"
        )
    findings = [
        (result["name"], finding)
        for result in payload["checks"]
        for finding in result["findings"]
    ]
    if findings:
        lines.extend(["", "## 발견 사항", ""])
        for check_name, finding in findings:
            asset = (
                f" `{finding['asset_slug']}`"
                if finding.get("asset_slug") else ""
            )
            path = f" — `{finding['path']}`" if finding.get("path") else ""
            lines.append(
                f"- **{finding['severity'].upper()}** "
                f"`{finding['code']}`{asset}: {finding['message']} "
                f"({check_name}){path}"
            )
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("pr", "all", "release"), default="all")
    parser.add_argument("--base-ref", help="Git base SHA/ref for changed files")
    parser.add_argument(
        "--changed-file", action="append", default=[],
        help="Explicit changed repository path; may be repeated",
    )
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")

    args = parse_args(argv)
    try:
        changed_files = discover_changed_files(
            args.base_ref, args.changed_file, REPO_ROOT
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    results = [
        run_script(check_id, name, script, REPO_ROOT)
        for check_id, name, script in CHECKS
    ]
    results.append(validate_coverage(args.mode, changed_files))
    results.append(validate_glb_pin_nodes())
    results.append(validate_physical_dimensions())
    payload = report_payload(args.mode, changed_files, results)
    report_dir = args.report_dir.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "asset-validation-report.json"
    markdown_path = report_dir / "asset-validation-report.md"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown = markdown_report(payload)
    markdown_path.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"JSON: {relative(json_path)}")
    print(f"Markdown: {relative(markdown_path)}")
    github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_summary:
        with Path(github_summary).open("a", encoding="utf-8") as handle:
            handle.write(markdown)
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

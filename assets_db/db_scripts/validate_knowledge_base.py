import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "db_scripts" / "008_seed_knowledge_qa.sql"
COMPONENTS_PATH = ROOT / "db_scripts" / "all_component_pin_coordinates.json"

components = set(json.loads(COMPONENTS_PATH.read_text(encoding="utf-8")).keys())
text = SQL_PATH.read_text(encoding="utf-8")


def json_block(tag):
    match = re.search(rf"\${tag}\$(.*?)\${tag}\$::jsonb", text, re.S)
    if not match:
        raise SystemExit(f"Missing ${tag}$ JSON block in {SQL_PATH.name}")
    return json.loads(match.group(1))


sources = json_block("sources")
specs = json_block("specs")
snippets = json_block("snippets")
tasks = json_block("tasks")
issues = json_block("issues")

source_keys = {row["source_key"] for row in sources}
snippet_keys = {row["snippet_key"] for row in snippets}
issue_keys = {row["issue_key"] for row in issues}


def require_sources(row, label):
    for key in row.get("source_keys", []):
        if key not in source_keys:
            raise SystemExit(f"{label} references missing source_key: {key}")


def require_components(row, label):
    for key in row.get("component_slugs", []):
        if key not in components:
            raise SystemExit(f"{label} references missing component slug: {key}")
    for key in row.get("board_slugs", []):
        if key not in components:
            raise SystemExit(f"{label} references missing board slug: {key}")


for row in specs:
    if row["slug"] not in components:
        raise SystemExit(f"spec references missing component slug: {row['slug']}")
    require_sources(row, f"spec/{row['slug']}/{row['spec_key']}")
    if not (0 <= row["confidence_score"] <= 1):
        raise SystemExit(f"spec confidence out of range: {row['slug']}/{row['spec_key']}")

for row in snippets:
    require_sources(row, f"snippet/{row['snippet_key']}")
    require_components(row, f"snippet/{row['snippet_key']}")
    if not row["code"].strip():
        raise SystemExit(f"snippet has empty code: {row['snippet_key']}")

for row in issues:
    require_sources(row, f"issue/{row['issue_key']}")
    require_components(row, f"issue/{row['issue_key']}")
    if not row["likely_causes"]:
        raise SystemExit(f"issue has no likely causes: {row['issue_key']}")

for row in tasks:
    require_sources(row, f"task/{row['task_key']}")
    require_components(row, f"task/{row['task_key']}")
    snippet_key = row.get("code_snippet_key")
    if snippet_key and snippet_key not in snippet_keys:
        raise SystemExit(f"task references missing snippet_key: {row['task_key']} -> {snippet_key}")
    for issue_key in row.get("troubleshooting_keys", []):
        if issue_key not in issue_keys:
            raise SystemExit(f"task references missing issue_key: {row['task_key']} -> {issue_key}")

print(
    "Validated knowledge QA seed: "
    f"{len(sources)} sources, {len(specs)} specs, {len(snippets)} snippets, "
    f"{len(tasks)} task-result templates, {len(issues)} troubleshooting guides."
)

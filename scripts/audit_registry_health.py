from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "REGISTRY_HEALTH_AUDIT_v0.1.7.3.md"

SCAN_GLOBS = [
    "config/**/*.yaml",
    "templates/**/*.j2",
    "templates/**/*.html",
    "src/prompts/**/*.py",
    "src/core/**/*.py",
    "README.md",
    "docs/*.md",
    "samples/*.yaml",
]

MOJIBAKE_PATTERNS = ("�", "Ã", "Â", "â€", "â€™", "â€œ", "â€\x9d", "ä¸", "çš", "ï»¿", "å\x90", "æ\x98", "è¯", "ä½", "å­¦")
LEGACY_PATTERNS = (
    "config/knowledge_points.yaml",
    "legacy_names",
    "legacy_aliases",
    "get_legacy_knowledge_points",
    "render_legacy_knowledge_points_for_prompt",
    "daughter_grade5",
    "math_tutor_system",
)
OLD_BARE_TAGS = ("C1", "C2", "C3", "C4", "F1", "F2", "F3", "R1", "R2", "R3", "R4", "M1", "M2", "M3", "U1", "G1", "K3")


@dataclass
class Hit:
    category: str
    path: Path
    line_no: int
    marker: str
    snippet: str
    active: bool
    fixed: bool


def main() -> int:
    hits = run_audit()
    write_report(hits)
    active_unfixed = [hit for hit in hits if hit.active and not hit.fixed]
    print(f"REGISTRY_HEALTH_AUDIT report={REPORT_PATH}")
    print(f"REGISTRY_HEALTH_AUDIT total_hits={len(hits)} active_unfixed={len(active_unfixed)}")
    if active_unfixed:
        for hit in active_unfixed[:20]:
            print(f"ACTIVE_UNFIXED {hit.category} {hit.path}:{hit.line_no} {hit.marker} :: {hit.snippet}")
    return 1 if active_unfixed else 0


def run_audit() -> list[Hit]:
    hits: list[Hit] = []
    for path in _scan_paths():
        text = path.read_text(encoding="utf-8", errors="replace")
        active = _is_active(path)
        for line_no, line in enumerate(text.splitlines(), 1):
            for marker in MOJIBAKE_PATTERNS:
                if marker in line and not _is_pattern_reference(line):
                    hits.append(_hit("mojibake", path, line_no, marker, line, active))
            for marker in LEGACY_PATTERNS:
                if marker in line and not _allowed_legacy_reference(path, line, marker):
                    hits.append(_hit("legacy", path, line_no, marker, line, active))
            for tag in OLD_BARE_TAGS:
                if re.search(rf"(?<![A-Z0-9_]){re.escape(tag)}(?![A-Z0-9_])", line):
                    if _bare_tag_scan_path(path) and not _allowed_bare_tag_reference(path, line):
                        hits.append(_hit("old_bare_tag", path, line_no, tag, line, active))
    hits.extend(_prompt_source_checks())
    hits.extend(_display_filter_checks())
    return hits


def write_report(hits: list[Hit]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    active_unfixed = [hit for hit in hits if hit.active and not hit.fixed]
    inactive = [hit for hit in hits if not hit.active]
    lines = [
        "# Registry Health Audit v0.1.7.3",
        "",
        "Mode: no-legacy cutover.",
        "",
        f"- Total hits: {len(hits)}",
        f"- Active unfixed hits: {len(active_unfixed)}",
        f"- Inactive historical hits: {len(inactive)}",
        "",
        "## Active Runtime Result",
        "",
    ]
    if active_unfixed:
        lines.extend(_render_hits(active_unfixed))
    else:
        lines.append("Active runtime scan passed: no unfixed mojibake, legacy runtime references, old bare active tags, prompt source leaks, or display/filter bypasses were detected.")
    if inactive:
        lines.extend(["", "## Inactive Historical Notes", ""])
        lines.extend(_render_hits(inactive[:80]))
        if len(inactive) > 80:
            lines.append(f"- ... {len(inactive) - 80} additional inactive hits omitted from this report.")
    lines.extend([
        "",
        "## Source Of Truth",
        "",
        "- Active knowledge points: `config/curriculum/cn_k12_2022/{subject}/grade_*.yaml`",
        "- Active question types: `config/education/question_types.yaml`",
        "- Active mistake tags: `config/education/mistake_taxonomy.yaml`",
        "- Active aliases: `config/alias_mappings.yaml`",
        "- Active worksheet policy: `config/worksheet_policy.yaml`",
        "- `config/knowledge_points.yaml` is not present in active runtime.",
    ])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _scan_paths() -> list[Path]:
    paths: set[Path] = set()
    for glob in SCAN_GLOBS:
        paths.update(ROOT.glob(glob))
    paths.discard(REPORT_PATH)
    return sorted(path for path in paths if path.is_file() and "archive" not in path.parts)


def _is_active(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if rel.parts[0] == "docs":
        return rel.name in {"HANDOFF_v0.1.7.3.md", "MISTAKE_TAXONOMY_v0.1.7.3.md"}
    return True


def _hit(category: str, path: Path, line_no: int, marker: str, line: str, active: bool) -> Hit:
    return Hit(
        category=category,
        path=path.relative_to(ROOT),
        line_no=line_no,
        marker=marker,
        snippet=line.strip()[:140],
        active=active,
        fixed=not active,
    )


def _allowed_legacy_reference(path: Path, line: str, marker: str) -> bool:
    rel = path.relative_to(ROOT)
    if marker == "legacy_names" and rel.as_posix() == "scripts/audit_registry_health.py":
        return True
    if "no_legacy" in line:
        return True
    if rel.as_posix() == "README.md":
        lowered = line.lower()
        if any(word in lowered for word in ("removed", "archived", "not present", "not loaded")):
            return True
    if rel.name in {"HANDOFF_v0.1.7.3.md", "MISTAKE_TAXONOMY_v0.1.7.3.md"}:
        return True
    return False


def _allowed_bare_tag_reference(path: Path, line: str) -> bool:
    rel = path.relative_to(ROOT)
    if rel.as_posix() == "scripts/audit_registry_health.py":
        return True
    if rel.name in {"HANDOFF_v0.1.7.3.md", "MISTAKE_TAXONOMY_v0.1.7.3.md"}:
        return True
    return False


def _bare_tag_scan_path(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return rel.startswith("config/education/mistake_taxonomy.yaml") or rel.startswith("samples/")


def _is_pattern_reference(line: str) -> bool:
    return "MOJIBAKE_PATTERNS" in line or "mojibake such as" in line


def _prompt_source_checks() -> list[Hit]:
    hits: list[Hit] = []
    prompt_files = [
        ROOT / "src" / "prompts" / "marking_prompt.py",
        ROOT / "src" / "prompts" / "worksheet_prompt.py",
        ROOT / "src" / "prompts" / "repair_prompt.py",
    ]
    for path in prompt_files:
        text = path.read_text(encoding="utf-8")
        if "render_knowledge_points_for_prompt" in text:
            hits.append(_hit("prompt_source", path, 1, "render_knowledge_points_for_prompt", "prompt uses non-context knowledge point renderer", True))
        if "render_curriculum_scope_for_prompt" not in text and "render_curriculum_scope_for_context" not in text:
            hits.append(_hit("prompt_source", path, 1, "missing_curriculum_scope", "prompt does not reference curriculum-scoped knowledge points", True))
    return hits


def _display_filter_checks() -> list[Hit]:
    hits: list[Hit] = []
    app = ROOT / "src" / "app.py"
    text = app.read_text(encoding="utf-8")
    if "make_filter_option" not in text:
        hits.append(_hit("display_filter", app, 1, "make_filter_option", "app filter UI does not use display_contract filter options", True))
    if "format_mistake_row_for_display" not in text:
        hits.append(_hit("display_filter", app, 1, "format_mistake_row_for_display", "app mistake table does not use display_contract formatter", True))
    return hits


def _render_hits(hits: list[Hit]) -> list[str]:
    return [
        f"- `{hit.category}` `{hit.path}:{hit.line_no}` marker=`{hit.marker}` active={hit.active} fixed={hit.fixed}: {hit.snippet}"
        for hit in hits
    ]


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

import yaml

from src.core.paths import DEFAULT_DB_PATH
from src.core.rule_registry import RuleRegistryError, load_rule_registry
from src.db import SCHEMA_VERSION, get_connection


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_TABLES = {
    "schema_meta",
    "import_batches",
    "mistake_tags",
    "mistakes",
    "worksheets",
    "worksheet_items",
}

FORBIDDEN_COLUMNS = {
    "mistakes": {"question_type", "knowledge_point", "mistake_tag", "target_mistake_tag", "difficulty"},
    "worksheets": {"question_type", "knowledge_point", "mistake_tag", "target_mistake_tag", "difficulty"},
    "worksheet_items": {"question_type", "knowledge_point", "mistake_tag", "target_mistake_tag", "difficulty"},
}

REQUIRED_COLUMNS = {
    "mistakes": {
        "question_type_code",
        "knowledge_point_id",
        "primary_mistake_tag_code",
        "difficulty_code",
        "diagnosis_confidence",
        "needs_human_review",
        "secondary_mistake_tags_json",
        "diagnosis_evidence_json",
        "alternative_diagnoses_json",
    },
    "worksheet_items": {
        "question_type_code",
        "knowledge_point_id",
        "target_mistake_tag_code",
        "difficulty_code",
        "primary_target_id",
        "question_role",
        "teaching_purpose",
        "expected_error_mechanism",
    },
}
MATH_G6A_USAGE_STATUS = {"core_active", "review_active", "intro_active", "reserved_inactive"}
MATH_V018_CATEGORIES = {
    "concept_definition",
    "rule_application",
    "calculation_execution",
    "sign_symbol",
    "condition_judgement",
    "representation_transfer",
    "modeling_relation",
    "method_formula_selection",
    "unit_measurement",
    "geometry_spatial",
    "data_graph_reading",
    "process_expression",
    "checking_estimation",
    "reading_comprehension",
}
MATH_REQUIRED_TAGS = {
    "MATH_EQUALITY_RELATION_ERROR",
    "MATH_QUANTITATIVE_RELATION_ERROR",
    "MATH_MODEL_CONSTRUCTION_ERROR",
    "MATH_UNIT_MEANING_ERROR",
    "MATH_UNIT_CONVERSION_ERROR",
}
MATH_V018_REPORT_TAGS = {
    "MATH_CONCEPT_DEFINITION_ERROR",
    "MATH_PREREQUISITE_CONCEPT_GAP",
    "MATH_RULE_APPLICATION_ERROR",
    "MATH_ALGORITHM_PROCEDURE_ERROR",
    "MATH_CALCULATION_EXECUTION_ERROR",
    "MATH_SIGN_RULE_ERROR",
    "MATH_SYMBOL_NOTATION_ERROR",
    "MATH_EQUALITY_RELATION_ERROR",
    "MATH_CONDITION_JUDGEMENT_ERROR",
    "GEN_CONDITION_OMISSION",
    "GEN_READING_KEYWORD_MISUNDERSTANDING",
    "MATH_REPRESENTATION_TRANSFER_ERROR",
    "MATH_QUANTITATIVE_RELATION_ERROR",
    "MATH_MODEL_CONSTRUCTION_ERROR",
    "MATH_METHOD_SELECTION_ERROR",
    "MATH_FORMULA_SELECTION_ERROR",
    "MATH_FORMULA_APPLICATION_ERROR",
    "MATH_MULTI_STEP_PLANNING_ERROR",
    "MATH_UNIT_MEANING_ERROR",
    "MATH_UNIT_CONVERSION_ERROR",
    "MATH_UNIT_LABEL_ERROR",
    "MATH_GEOMETRIC_PROPERTY_ERROR",
    "MATH_SPATIAL_VISUALIZATION_ERROR",
    "MATH_DATA_GRAPH_READING_ERROR",
    "MATH_PROCESS_EXPRESSION_ERROR",
    "MATH_MATHEMATICAL_LANGUAGE_ERROR",
    "MATH_ESTIMATION_NUMBER_SENSE_ERROR",
    "GEN_CHECKING_OMISSION",
}
MATH_KP_METADATA_FIELDS = {
    "micro_skill",
    "description",
    "prerequisite",
    "related_later",
    "typical_question_forms",
    "suitable_difficulty",
    "suitable_mistake_tags",
    "diagnostic_value",
    "training_value",
    "usage_status",
}
VALID_SEVERITIES = {"low", "medium", "high"}
OLD_BARE_TAGS = {"C3", "R4", "M2", "F3", "U1", "G1"}
MOJIBAKE_PATTERNS = (
    "\ufffd",
    "\u00c3",
    "\u00c2",
    "\u00e2\u20ac",
    "\u00e2\u20ac\u2122",
    "\u00e2\u20ac\u0153",
    "\u00e2\u20ac\x9d",
    "\u00e4\u00b8",
    "\u00e7\u0161",
    "\u00ef\u00bb\u00bf",
    "\u00e5\x90",
    "\u00e6\x98",
    "\u00e8\u00af",
    "\u00e4\u00bd",
    "\u00e5\u00ad",
)


def check_schema_integrity(db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, list[dict[str, Any]]]:
    report: dict[str, list[dict[str, Any]]] = {"errors": [], "warnings": [], "info": []}
    path = Path(db_path)
    if path.resolve() != DEFAULT_DB_PATH.resolve():
        _add(report, "errors", "invalid_db_path", f"Current DB path is not data/edu_tutor.db: {path}")
    else:
        _add(report, "info", "db_path", str(path))
    if not path.exists():
        _add(report, "errors", "missing_db", f"DB does not exist: {path}")
        return report

    with get_connection(path) as conn:
        _check_tables(conn, report)
        _check_schema_meta(conn, report)
        _check_columns(conn, report)
        _check_domain_values(conn, report)
        _check_orphans(conn, report)
        _check_duplicate_hashes(conn, report)
        _check_sample_confirmed(conn, report)
    return report


def _check_tables(conn: sqlite3.Connection, report: dict[str, list[dict[str, Any]]]) -> None:
    tables = _tables(conn)
    missing = sorted(REQUIRED_TABLES - tables)
    for table in missing:
        _add(report, "errors", "missing_table", table)
    _add(report, "info", "tables", sorted(tables))


def _check_schema_meta(conn: sqlite3.Connection, report: dict[str, list[dict[str, Any]]]) -> None:
    if "schema_meta" not in _tables(conn):
        return
    rows = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM schema_meta").fetchall()}
    if rows.get("schema_version") != SCHEMA_VERSION:
        _add(report, "errors", "invalid_schema_version", rows.get("schema_version"))
    if rows.get("project_name") != "edu_tutor_system":
        _add(report, "errors", "invalid_project_name", rows.get("project_name"))
    if rows.get("db_name") != "edu_tutor.db":
        _add(report, "errors", "invalid_db_name", rows.get("db_name"))
    _add(report, "info", "schema_meta", rows)


def _check_columns(conn: sqlite3.Connection, report: dict[str, list[dict[str, Any]]]) -> None:
    for table, forbidden in FORBIDDEN_COLUMNS.items():
        if table not in _tables(conn):
            continue
        columns = _columns(conn, table)
        for column in sorted(forbidden & columns):
            _add(report, "errors", "forbidden_old_column_present", f"{table}.{column}")
    for table, required in REQUIRED_COLUMNS.items():
        if table not in _tables(conn):
            continue
        columns = _columns(conn, table)
        for column in sorted(required - columns):
            _add(report, "errors", "missing_canonical_column", f"{table}.{column}")


def _check_domain_values(conn: sqlite3.Connection, report: dict[str, list[dict[str, Any]]]) -> None:
    try:
        registry = load_rule_registry()
    except RuleRegistryError as exc:
        _add(report, "errors", "registry_load_failed", str(exc))
        return
    _check_alias_ambiguity(registry, report)
    _check_v018_registry_contract(registry, report)
    students = {item["student_id"] for item in registry.get_students(active_only=False)}
    subjects = {item["subject_id"] for item in registry.get_subjects(active_only=False)}
    difficulties = set(registry.get_difficulty_codes(active_only=True))
    for row in conn.execute("SELECT * FROM mistakes").fetchall():
        item = dict(row)
        label = f"mistakes[{item.get('id')}]"
        _check_common_record(item, label, students, subjects, difficulties, registry, report)
        tags = {tag["code"] for tag in registry.get_mistake_tags_for_subject(item.get("subject_id", ""))}
        if item.get("primary_mistake_tag_code") not in tags:
            _add(report, "errors", "invalid_mistake_tag_code", f"{label}.{item.get('primary_mistake_tag_code')}")
    for row in conn.execute(
        """
        SELECT wi.*, w.student_id, w.subject_id, w.grade_at_time, w.curriculum_version_at_time
        FROM worksheet_items wi JOIN worksheets w ON w.id = wi.worksheet_id
        """
    ).fetchall():
        item = dict(row)
        label = f"worksheet_items[{item.get('id')}]"
        _check_common_record(item, label, students, subjects, difficulties, registry, report)
        tags = {tag["code"] for tag in registry.get_mistake_tags_for_subject(item.get("subject_id", ""))}
        if item.get("target_mistake_tag_code") and item.get("target_mistake_tag_code") not in tags:
            _add(report, "errors", "invalid_mistake_tag_code", f"{label}.{item.get('target_mistake_tag_code')}")


def _check_common_record(
    item: dict[str, Any],
    label: str,
    students: set[str],
    subjects: set[str],
    difficulties: set[str],
    registry: Any,
    report: dict[str, list[dict[str, Any]]],
) -> None:
    if item.get("student_id") not in students:
        _add(report, "errors", "invalid_student_id", f"{label}.{item.get('student_id')}")
    if item.get("subject_id") not in subjects:
        _add(report, "errors", "invalid_subject_id", f"{label}.{item.get('subject_id')}")
    try:
        grade = int(item.get("grade_at_time"))
        if grade < 1 or grade > 12:
            raise ValueError
    except (TypeError, ValueError):
        _add(report, "errors", "invalid_grade_at_time", f"{label}.{item.get('grade_at_time')}")
        return
    qtypes = {qt["code"] for qt in registry.get_question_types_for_subject(item.get("subject_id", ""))}
    if item.get("question_type_code") not in qtypes:
        _add(report, "errors", "invalid_question_type_code", f"{label}.{item.get('question_type_code')}")
    if item.get("difficulty_code") not in difficulties:
        _add(report, "errors", "invalid_difficulty_code", f"{label}.{item.get('difficulty_code')}")
    kp = item.get("knowledge_point_id")
    if kp:
        points = {
            point["knowledge_point_id"]
            for point in registry.get_knowledge_points_for_context(
                item.get("subject_id", ""),
                grade,
                item.get("curriculum_version_at_time") or "cn_k12_2022",
            )
        }
        if kp not in points:
            _add(report, "errors", "invalid_knowledge_point_id", f"{label}.{kp}")


def _check_orphans(conn: sqlite3.Connection, report: dict[str, list[dict[str, Any]]]) -> None:
    count = conn.execute(
        """
        SELECT COUNT(*)
        FROM worksheet_items wi
        LEFT JOIN worksheets w ON w.id = wi.worksheet_id
        WHERE w.id IS NULL
        """
    ).fetchone()[0]
    if count:
        _add(report, "errors", "orphan_worksheet_items", int(count))


def _check_duplicate_hashes(conn: sqlite3.Connection, report: dict[str, list[dict[str, Any]]]) -> None:
    for table, column in (("mistakes", "record_hash"), ("worksheets", "worksheet_hash")):
        rows = conn.execute(
            f"""
            SELECT {column} AS hash_value, COUNT(*) AS count
            FROM {table}
            WHERE {column} IS NOT NULL AND {column} != ''
            GROUP BY {column}
            HAVING COUNT(*) > 1
            """
        ).fetchall()
        for row in rows:
            _add(report, "warnings", "duplicate_hash", f"{table}.{row['hash_value']} count={row['count']}")


def _check_sample_confirmed(conn: sqlite3.Connection, report: dict[str, list[dict[str, Any]]]) -> None:
    count = conn.execute(
        """
        SELECT COUNT(*) FROM mistakes
        WHERE status = 'confirmed'
          AND (source LIKE '%sample%' OR source LIKE '%UAT%' OR source LIKE '%uat%')
        """
    ).fetchone()[0]
    if count:
        _add(report, "warnings", "sample_data_confirmed", int(count))


def _check_alias_ambiguity(registry: Any, report: dict[str, list[dict[str, Any]]]) -> None:
    for alias_key, section in (registry.alias_mappings or {}).items():
        if not isinstance(section, dict):
            continue
        targets_by_alias: dict[str, set[str]] = {}
        for scope, aliases in _iter_alias_scopes(section):
            if scope == "__global__":
                continue
            for alias, target in aliases.items():
                targets_by_alias.setdefault(str(alias), set()).add(str(target))
        for alias, targets in sorted(targets_by_alias.items()):
            if len(targets) > 1:
                _add(report, "warnings", "ambiguous_subject_scoped_alias", f"{alias_key}.{alias} -> {sorted(targets)}")


def _check_v018_registry_contract(registry: Any, report: dict[str, list[dict[str, Any]]]) -> None:
    _check_math_g6a_curriculum(registry, report)
    _check_math_v018_taxonomy(registry, report)
    _check_no_legacy_runtime_config(registry, report)


def _check_math_g6a_curriculum(registry: Any, report: dict[str, list[dict[str, Any]]]) -> None:
    try:
        curriculum = registry.get_curriculum_for("math", 6, "cn_k12_2022")
    except RuleRegistryError as exc:
        _add(report, "errors", "math_g6a_curriculum_missing", str(exc))
        return

    expected = {
        "subject_id": "math",
        "grade": 6,
        "term": "六年级上",
        "textbook_version": "沪教版",
        "curriculum_version": "cn_k12_2022",
        "registry_version": "v0.1.8.1",
    }
    for field, value in expected.items():
        actual = curriculum.get(field) or (curriculum.get("metadata") or {}).get(field)
        if actual != value:
            _add(report, "errors", "math_g6a_curriculum_metadata_invalid", f"{field}={actual!r}")

    points = registry.get_knowledge_points_for_context("math", 6, "cn_k12_2022")
    if not points:
        _add(report, "errors", "math_g6a_no_knowledge_points", "math grade 6 curriculum has no knowledge_points")
        return
    point_ids = [str(point.get("knowledge_point_id", "")) for point in points]
    duplicates = sorted({value for value in point_ids if point_ids.count(value) > 1})
    for duplicate in duplicates:
        _add(report, "errors", "math_g6a_duplicate_knowledge_point_id", duplicate)

    active_tags = {tag["code"] for tag in registry.get_mistake_tags_for_subject("math") if tag.get("active", True) is True}
    difficulties = set(registry.get_difficulty_codes(active_only=True))
    point_id_set = set(point_ids)
    for point in points:
        point_id = str(point.get("knowledge_point_id", ""))
        label = f"knowledge_points[{point_id}]"
        if not point_id.startswith("math_g6a_"):
            _add(report, "errors", "math_g6a_invalid_knowledge_point_prefix", point_id)
        if point.get("subject_id") != "math":
            _add(report, "errors", "math_g6a_invalid_subject_id", f"{label}.subject_id={point.get('subject_id')!r}")
        if int(point.get("grade", 0)) != 6:
            _add(report, "errors", "math_g6a_invalid_grade", f"{label}.grade={point.get('grade')!r}")
        if point.get("term") != "六年级上":
            _add(report, "errors", "math_g6a_invalid_term", f"{label}.term={point.get('term')!r}")
        if point.get("textbook_version") != "沪教版":
            _add(report, "errors", "math_g6a_invalid_textbook_version", f"{label}.textbook_version={point.get('textbook_version')!r}")
        if point.get("curriculum_version") != "cn_k12_2022":
            _add(report, "errors", "math_g6a_invalid_curriculum_version", f"{label}.curriculum_version={point.get('curriculum_version')!r}")
        if not isinstance(point.get("active"), bool):
            _add(report, "errors", "math_g6a_active_not_boolean", label)
        usage_status = point.get("usage_status")
        if usage_status not in MATH_G6A_USAGE_STATUS:
            _add(report, "errors", "math_g6a_invalid_usage_status", f"{label}.usage_status={usage_status!r}")
        if usage_status == "reserved_inactive" and point.get("active") is not False:
            _add(report, "errors", "math_g6a_reserved_should_be_inactive", label)
        for field in sorted(MATH_KP_METADATA_FIELDS):
            if field not in point:
                _add(report, "errors", "math_g6a_missing_metadata_field", f"{label}.{field}")
        for difficulty in point.get("suitable_difficulty") or []:
            if difficulty not in difficulties:
                _add(report, "errors", "math_g6a_invalid_suitable_difficulty", f"{label}.{difficulty}")
        for ref_field in ("prerequisite", "related_later"):
            for ref in point.get(ref_field) or []:
                if ref not in point_id_set:
                    _add(report, "warnings", "math_g6a_unknown_knowledge_point_reference", f"{label}.{ref_field}.{ref}")
        for tag_code in point.get("suitable_mistake_tags") or []:
            if tag_code not in active_tags:
                _add(report, "warnings", "math_g6a_unknown_suitable_mistake_tag", f"{label}.{tag_code}")


def _check_math_v018_taxonomy(registry: Any, report: dict[str, list[dict[str, Any]]]) -> None:
    all_active_codes = {tag["code"] for tag in registry.get_mistake_tags(active_only=True)}
    for old_code in sorted(OLD_BARE_TAGS):
        if old_code in all_active_codes:
            _add(report, "errors", "old_bare_tag_active", old_code)
    for code in sorted(all_active_codes):
        if code.startswith("YV-"):
            _add(report, "errors", "yv_tag_active", code)

    math_tags = registry.get_mistake_tags_for_subject("math")
    math_codes = {str(tag.get("code", "")) for tag in math_tags}
    if len(math_tags) != 28:
        _add(report, "errors", "math_v018_tag_count_not_28", len(math_tags))
    missing_report_tags = sorted(MATH_V018_REPORT_TAGS - math_codes)
    extra_report_tags = sorted(math_codes - MATH_V018_REPORT_TAGS)
    for code in missing_report_tags:
        _add(report, "errors", "math_v018_report_tag_missing", code)
    for code in extra_report_tags:
        _add(report, "errors", "math_v018_unexpected_math_visible_tag", code)
    for required in sorted(MATH_REQUIRED_TAGS):
        if required not in math_codes:
            _add(report, "errors", "math_v018_required_tag_missing", required)

    categories = {str(tag.get("category", "")) for tag in math_tags}
    for category in sorted(MATH_V018_CATEGORIES - categories):
        _add(report, "errors", "math_v018_category_missing", category)
    for tag in math_tags:
        code = str(tag.get("code", ""))
        label = f"mistake_tags[{code}]"
        if not (code.startswith("MATH_") or code.startswith("GEN_")):
            _add(report, "errors", "math_v018_invalid_code_prefix", code)
        if tag.get("category") not in MATH_V018_CATEGORIES:
            _add(report, "errors", "math_v018_invalid_category", f"{label}.category={tag.get('category')!r}")
        for field in ("definition", "use_when", "do_not_use_when"):
            if not str(tag.get(field, "")).strip():
                _add(report, "errors", "math_v018_required_text_missing", f"{label}.{field}")
        if tag.get("severity") not in VALID_SEVERITIES:
            _add(report, "errors", "math_v018_invalid_severity", f"{label}.severity={tag.get('severity')!r}")
        if not isinstance(tag.get("active"), bool):
            _add(report, "errors", "math_v018_active_not_boolean", label)
        if not isinstance(tag.get("allowed_secondary"), bool):
            _add(report, "errors", "math_v018_allowed_secondary_not_boolean", label)
        priority = tag.get("primary_priority")
        if not isinstance(priority, int) or priority < 1 or priority > 100:
            _add(report, "errors", "math_v018_invalid_primary_priority", f"{label}.primary_priority={priority!r}")
        if not isinstance(tag.get("conflict_with"), list):
            _add(report, "errors", "math_v018_conflict_with_not_list", label)
        else:
            for ref in tag.get("conflict_with") or []:
                if ref not in math_codes:
                    _add(report, "warnings", "math_v018_unknown_conflict_with", f"{label}.{ref}")
        if "old_code_reference_only" in tag:
            _add(report, "errors", "math_v018_old_code_reference_in_active_config", label)


def _check_no_legacy_runtime_config(registry: Any, report: dict[str, list[dict[str, Any]]]) -> None:
    if (ROOT / "config" / "knowledge_points.yaml").exists():
        _add(report, "errors", "legacy_knowledge_points_runtime_file_present", "config/knowledge_points.yaml")
    for forbidden_key in ("legacy_aliases", "legacy_names", "legacy_mappings", "legacy_merge_suggestions"):
        if _contains_key(registry.alias_mappings, forbidden_key):
            _add(report, "errors", "legacy_alias_key_present", forbidden_key)

    for path in _active_scan_paths():
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT).as_posix()
        for marker in MOJIBAKE_PATTERNS:
            if marker in text:
                _add(report, "errors", "mojibake_marker_present", f"{rel}:{marker}")
        if "YV-" in text:
            _add(report, "errors", "yv_reference_present", rel)
        if "old_code_reference_only" in text and not rel.startswith("docs/research/"):
            _add(report, "errors", "old_code_reference_only_active", rel)
        for old_code in sorted(OLD_BARE_TAGS):
            if re.search(rf"(?<![A-Z0-9_]){re.escape(old_code)}(?![A-Z0-9_])", text):
                _add(report, "errors", "old_bare_tag_reference_present", f"{rel}:{old_code}")


def _active_scan_paths() -> list[Path]:
    paths: set[Path] = set()
    for pattern in ("config/**/*.yaml", "templates/**/*.j2", "samples/*.yaml"):
        paths.update(ROOT.glob(pattern))
    return sorted(path for path in paths if path.is_file() and "archive" not in path.parts)


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(_contains_key(child, key) for child in value)
    return False


def _iter_alias_scopes(section: dict[str, Any]) -> list[tuple[str, dict[str, str]]]:
    result: list[tuple[str, dict[str, str]]] = []
    global_aliases: dict[str, str] = {}
    for alias, target in section.items():
        if isinstance(target, dict):
            result.append((str(alias), {str(k): str(v) for k, v in target.items()}))
        else:
            global_aliases[str(alias)] = str(target)
    if global_aliases:
        result.insert(0, ("__global__", global_aliases))
    return result


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _add(report: dict[str, list[dict[str, Any]]], level: str, code: str, detail: Any) -> None:
    report[level].append({"code": code, "detail": detail})


if __name__ == "__main__":
    integrity_report = check_schema_integrity()
    print(yaml.safe_dump(integrity_report, allow_unicode=True, sort_keys=False))
    raise SystemExit(1 if integrity_report["errors"] else 0)

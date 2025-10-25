import json
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple

ALLOWED_SIZES = {"micro", "small", "medium"}
ALLOWED_SECTORS = {
    "all",
    "hospitality_retail",
    "professional_services",
    "manufacturing_logistics",
    "creative_digital_marketing",
    "health_wellness_education",
    "technology_startup_saas",
}
ALLOWED_OVERLAYS = {
    "payment_card_industry_data_security_standard",
    "general_data_protection_regulation",
    "operational_technology_and_industrial_control",
}
ANSWER_TYPES = {"traffic_light"}

def _require_keys(obj: Dict[str, Any], keys: List[str], ctx: str):
    for k in keys:
        if k not in obj:
            raise ValueError(f"{ctx}: missing required key '{k}'")

def _require_type(value: Any, expected_type, ctx: str):
    if not isinstance(value, expected_type):
        raise ValueError(f"{ctx}: expected type {expected_type.__name__}, got {type(value).__name__}")

def _validate_weights(w: Dict[str, Any], ctx: str):
    for k in ("importance", "effort", "impact"):
        if k not in w or not isinstance(w[k], (int, float)):
            raise ValueError(f"{ctx}: weights['{k}'] must be number")

def _validate_visibility(v: Dict[str, Any], ctx: str):
    _require_keys(v, ["sizes", "sectors", "overlays"], ctx + ".visibility_rules")
    if not set(v["sizes"]).issubset(ALLOWED_SIZES):
        raise ValueError(f"{ctx}: visibility_rules.sizes must be subset of {sorted(ALLOWED_SIZES)}")
    if not set(v["sectors"]).issubset(ALLOWED_SECTORS):
        raise ValueError(f"{ctx}: visibility_rules.sectors must be subset of {sorted(ALLOWED_SECTORS)}")
    if not set(v["overlays"]).issubset(ALLOWED_OVERLAYS):
        raise ValueError(f"{ctx}: visibility_rules.overlays must be subset of {sorted(ALLOWED_OVERLAYS)}")

def validate_question(q: Dict[str, Any]) -> None:
    _require_keys(
        q,
        ["id", "section", "text", "hint", "answer_type", "weights", "visibility_rules", "framework_references"],
        "question",
    )
    _require_type(q["id"], str, "question.id")
    _require_type(q["section"], str, "question.section")
    _require_type(q["text"], str, "question.text")
    _require_type(q["hint"], str, "question.hint")
    if q["answer_type"] not in ANSWER_TYPES:
        raise ValueError(f"question.answer_type must be one of {sorted(ANSWER_TYPES)}")
    _require_type(q["weights"], dict, "question.weights")
    _require_type(q["visibility_rules"], dict, "question.visibility_rules")
    _require_type(q["framework_references"], list, "question.framework_references")
    _validate_weights(q["weights"], "question")
    _validate_visibility(q["visibility_rules"], "question")

def load_questions_from_file(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Question file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path}: root must be a list of questions")
    for i, q in enumerate(data, start=1):
        validate_question(q)
    return data

def merge_unique_by_id(lists: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    seen: Set[str] = set()
    merged: List[Dict[str, Any]] = []
    for arr in lists:
        for q in arr:
            if q["id"] in seen:
                continue
            seen.add(q["id"])
            merged.append(q)
    return merged

def build_question_set(
    base_dir: Path,
    size: str,
    sector: str,
    overlay_flags: Dict[str, bool],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    debug: List[str] = []
    qdir = base_dir / "questions"

    core = load_questions_from_file(qdir / "core.json")
    debug.append(f"Loaded core.json: {len(core)}")

    size_q = load_questions_from_file(qdir / f"size_{size}.json")
    debug.append(f"Loaded size_{size}.json: {len(size_q)}")

    sector_file = qdir / f"sector_{sector}.json"
    sector_q = load_questions_from_file(sector_file) if sector_file.exists() else []
    debug.append(f"Loaded sector_{sector}.json: {len(sector_q)}")

    overlay_q_all: List[Dict[str, Any]] = []
    for overlay_key, enabled in overlay_flags.items():
        if enabled:
            path = qdir / f"overlays_{overlay_key}.json"
            if path.exists():
                overlay_q_all += load_questions_from_file(path)
                debug.append(f"Loaded overlay {overlay_key}")
            else:
                debug.append(f"Missing overlay {overlay_key}")

    merged = merge_unique_by_id([core, size_q, sector_q, overlay_q_all])

    final = []
    for q in merged:
        v = q["visibility_rules"]
        if (
            size in v["sizes"]
            and (sector in v["sectors"] or "all" in v["sectors"])
            and all(overlay_flags.get(o, False) for o in v["overlays"])
        ):
            final.append(q)

    debug.append(f"Final question count: {len(final)}")
    return final, debug

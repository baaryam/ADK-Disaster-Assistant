"""Function tools for the Flood, Landslide and Disaster Recovery Assistant.

INTE 22303 - Artificial Intelligence (24/25), Assignment 2 - Google ADK.

Every tool in this file reads the supplied data pack in the ``data`` folder
next to this file. No incident, rule, guidance item or relief point is
hard-coded here: if a value is not in the supplied files, the tools return a
clear ``not_found`` (or ``error``) result instead of inventing one.

Web Builder / YAML registration names (fully-qualified):
    disaster_recovery_assistant.tools.classify_issue
    disaster_recovery_assistant.tools.get_incident_status
    disaster_recovery_assistant.tools.get_safety_guidance
    disaster_recovery_assistant.tools.find_relief_point
    disaster_recovery_assistant.tools.get_source_metadata

Every tool returns a dictionary with a ``status`` field. Status values:
    found / classified   - supplied record(s) returned
    needs_clarification  - one required value is missing or ambiguous;
                           ``question`` holds the one focused question to ask
    not_found            - the supplied records do not contain the request
    no_rule_matched      - (classify_issue only) no supplied keyword matched
    error                - a data file is missing or malformed
"""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Data location. Works from any working directory because it is resolved
# relative to this file. It can be overridden with DISASTER_DATA_DIR.
# ---------------------------------------------------------------------------
DATA_DIR = Path(
    os.environ.get("DISASTER_DATA_DIR") or Path(__file__).resolve().parent / "data"
)

INCIDENT_FILE = "incident_status.csv"
RULES_FILE = "issue_rules.csv"
GUIDANCE_FILE = "safety_guidance.csv"
RELIEF_FILE = "relief_points.csv"
SOURCE_REGISTER_FILE = "source_register.md"

INCIDENT_COLUMNS = [
    "incident_id", "area", "incident_type", "status", "priority", "summary",
    "recorded_update", "source_id", "effective_date", "data_status",
]
RULE_COLUMNS = [
    "rule_id", "keywords", "category", "priority", "recommended_action",
    "source_id", "effective_date", "data_status",
]
GUIDANCE_COLUMNS = [
    "guidance_id", "incident_type", "priority", "guidance", "avoid",
    "escalation_note", "source_id", "effective_date", "data_status",
]
RELIEF_COLUMNS = [
    "relief_id", "area", "assistance_type", "name", "location_description",
    "services", "recorded_status", "source_id", "effective_date", "data_status",
]

# Wording taken from knowledge_base.md and source_register.md.
DATA_NOTICE = (
    "Supplied assignment records only. They are not a live feed and do not "
    "represent current government, emergency-service, shelter, road, hospital, "
    "police, or weather information. The effective date identifies the dataset "
    "version; it is not a promise that an incident, route, service, or location "
    "is currently unchanged."
)


class DataPackError(Exception):
    """Raised when a supplied data file is missing or malformed."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _read_csv(file_name: str, required_columns: List[str]) -> List[Dict[str, str]]:
    """Read a supplied CSV file and check that the expected columns exist."""
    path = DATA_DIR / file_name
    if not path.is_file():
        raise DataPackError(f"Supplied data file '{file_name}' was not found in {DATA_DIR}.")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames or []
            missing = [c for c in required_columns if c not in columns]
            if missing:
                raise DataPackError(
                    f"Supplied data file '{file_name}' is missing column(s): {', '.join(missing)}."
                )
            rows = []
            for row in reader:
                if not any((value or "").strip() for value in row.values()):
                    continue  # skip blank lines
                rows.append({c: (row.get(c) or "").strip() for c in required_columns})
            return rows
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        raise DataPackError(f"Supplied data file '{file_name}' could not be read: {exc}") from exc


def _error(exc: Exception) -> Dict:
    return {
        "status": "error",
        "message": f"Data error: {exc} No information has been invented.",
        "data_notice": DATA_NOTICE,
    }


def _norm(value: Optional[str]) -> str:
    """Case-insensitive comparison key: 'Blocked-Route' -> 'blocked route'."""
    text = (value or "").strip().lower()
    text = re.sub(r"[_\-]+", " ", text)
    return re.sub(r"\s+", " ", text)


def _unique(values: List[str]) -> List[str]:
    seen, result = set(), []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _join_options(options: List[str]) -> str:
    if len(options) <= 1:
        return "".join(options)
    return ", ".join(options[:-1]) + " or " + options[-1]


def _match_option(user_value: str, options: List[str]) -> List[str]:
    """Match a user's wording to supplied option values without guessing.

    1. exact match after normalisation ('Blocked route' == 'blocked_route');
    2. otherwise one value contained in the other ('shelter' -> 'temporary_shelter',
       'flooding' -> 'flood').
    Returns every matching supplied value; more than one means it is ambiguous.
    """
    key = _norm(user_value)
    if not key:
        return []
    exact = [o for o in options if _norm(o) == key]
    if exact:
        return exact
    return [o for o in options if key in _norm(o) or _norm(o) in key]


def _supported_areas() -> List[str]:
    rows = _read_csv(INCIDENT_FILE, INCIDENT_COLUMNS) + _read_csv(RELIEF_FILE, RELIEF_COLUMNS)
    return _unique([r["area"] for r in rows if r["area"]])


def _find_area(area: str, rows: List[Dict[str, str]]) -> Optional[str]:
    """Return the supplied spelling of an area (case-insensitive), or None."""
    key = _norm(area)
    for row in rows:
        if _norm(row["area"]) == key:
            return row["area"]
    return None


# ---------------------------------------------------------------------------
# Tool 1 - classify_issue
# ---------------------------------------------------------------------------
def _keyword_match(keyword: str, full_text: str, sentences: List[List[str]]) -> Optional[str]:
    """Deterministic keyword test using only the supplied keyword.

    'phrase'    - the keyword appears as written (each word may carry an ending,
                  e.g. 'flood' matches 'flooded', 'shelter' matches 'shelters');
    'all_words' - for multi-word keywords, every keyword word appears in the
                  same sentence in any order ('road blocked' matches
                  'the road is blocked').
    """
    tokens = _norm(keyword).split(" ")
    tokens = [t for t in tokens if t]
    if not tokens:
        return None
    pattern = r"\b" + r"[a-z0-9]*\s+".join(re.escape(t) for t in tokens) + r"[a-z0-9]*\b"
    if re.search(pattern, full_text):
        return "phrase"
    if len(tokens) > 1:
        for words in sentences:
            if all(any(w.startswith(t) for w in words) for t in tokens):
                return "all_words"
    return None


def classify_issue(description: str) -> Dict:
    """Classify a user's problem description using ONLY the supplied rules in issue_rules.csv.

    Pass the user's own words unchanged. The result is deterministic: the same
    description always gives the same category. The language model must not
    change the category, priority or recommended action returned here.

    Args:
        description: The user's short description of the problem, in their own words
            (for example "The road to my house in Kegalle is blocked by debris").

    Returns:
        dict with:
          status: "classified", "no_rule_matched", "needs_clarification" or "error".
          category / priority / recommended_action / rule_id: from the first matching
            rule in file order (primary classification).
          matched_rules: every matching rule with its matched keywords and
            source_id, effective_date and data_status.
          incident_types_to_check: matched categories that are incident types in
            incident_status.csv (flood, landslide, blocked_route) - look these up.
          immediate_danger: True when an immediate-danger keyword matched.
          immediate_safety_warning: the supplied immediate-danger action and
            guidance (only when immediate_danger is True). Show it FIRST.
          source_id, effective_date, data_status of the primary rule.
    """
    if not (description or "").strip():
        return {
            "status": "needs_clarification",
            "missing_field": "description",
            "question": "Please describe the problem in a short sentence (for example flooding, "
                        "a landslide, a blocked road, or a need for shelter).",
            "data_notice": DATA_NOTICE,
        }
    try:
        rules = _read_csv(RULES_FILE, RULE_COLUMNS)
        incident_types = _unique([r["incident_type"] for r in _read_csv(INCIDENT_FILE, INCIDENT_COLUMNS)])
        guidance_rows = _read_csv(GUIDANCE_FILE, GUIDANCE_COLUMNS)
    except DataPackError as exc:
        return _error(exc)

    lowered = description.lower()
    full_text = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", lowered)).strip()
    sentences = [
        re.sub(r"[^a-z0-9]+", " ", part).split()
        for part in re.split(r"[.!?;\n]+", lowered)
        if part.strip()
    ]

    matched_rules = []
    for rule in rules:
        hits, match_types = [], []
        for keyword in rule["keywords"].split("|"):
            keyword = keyword.strip()
            if not keyword:
                continue
            how = _keyword_match(keyword, full_text, sentences)
            if how:
                hits.append(keyword)
                match_types.append(how)
        if hits:
            matched_rules.append({
                "rule_id": rule["rule_id"],
                "category": rule["category"],
                "priority": rule["priority"],
                "recommended_action": rule["recommended_action"],
                "matched_keywords": hits,
                "match_types": match_types,
                "source_id": rule["source_id"],
                "effective_date": rule["effective_date"],
                "data_status": rule["data_status"],
            })

    if not matched_rules:
        return {
            "status": "no_rule_matched",
            "category": None,
            "message": "The description did not match any supplied classification keyword. "
                       "Do not guess a category. Ask the user for a short description of the "
                       "problem (flood, landslide, blocked route, or relief need).",
            "rules_source_id": rules[0]["source_id"] if rules else None,
            "data_notice": DATA_NOTICE,
        }

    primary = matched_rules[0]  # first matching rule in the supplied file order
    matched_categories = [m["category"] for m in matched_rules]
    immediate = "immediate_danger" in matched_categories

    result = {
        "status": "classified",
        "category": primary["category"],
        "priority": primary["priority"],
        "recommended_action": primary["recommended_action"],
        "rule_id": primary["rule_id"],
        "source_id": primary["source_id"],
        "effective_date": primary["effective_date"],
        "data_status": primary["data_status"],
        "matched_categories": matched_categories,
        "matched_rules": matched_rules,
        "incident_types_to_check": [c for c in matched_categories if c in incident_types],
        "immediate_danger": immediate,
        "data_notice": DATA_NOTICE,
    }

    if immediate:
        rule = next(m for m in matched_rules if m["category"] == "immediate_danger")
        guidance = next((g for g in guidance_rows if g["incident_type"] == "immediate_danger"), None)
        warning = {
            "recommended_action": rule["recommended_action"],
            "rule_id": rule["rule_id"],
            "rule_source_id": rule["source_id"],
            "note": "The supplied records are not emergency dispatch. This assistant cannot "
                    "contact or dispatch any emergency service.",
        }
        if guidance:
            warning.update({
                "guidance_id": guidance["guidance_id"],
                "guidance": guidance["guidance"],
                "avoid": guidance["avoid"],
                "escalation_note": guidance["escalation_note"],
                "guidance_source_id": guidance["source_id"],
                "effective_date": guidance["effective_date"],
                "data_status": guidance["data_status"],
            })
        result["immediate_safety_warning"] = warning

    return result


# ---------------------------------------------------------------------------
# Tool 2 - get_incident_status
# ---------------------------------------------------------------------------
def get_incident_status(area: str, incident_type: str = "") -> Dict:
    """Look up the recorded incident status for a supported area in incident_status.csv.

    Never guess the incident type. If the area has more than one recorded
    incident and incident_type is empty or ambiguous, this tool returns
    status "needs_clarification" with ONE focused question to ask the user.

    Args:
        area: Area name given by the user (Colombo, Ratnapura or Kegalle; case-insensitive).
        incident_type: Optional incident type given by the user, for example "flood",
            "landslide" or "blocked route". Leave empty if the user did not say it.

    Returns:
        dict with status "found", "needs_clarification", "not_found" or "error".
        When found, "records" holds the supplied rows exactly as written
        (incident_id, area, incident_type, status, priority, summary,
        recorded_update, source_id, effective_date, data_status).
        When needs_clarification, "question" and "options" hold the question to ask.
    """
    try:
        rows = _read_csv(INCIDENT_FILE, INCIDENT_COLUMNS)
        supported = _supported_areas()
    except DataPackError as exc:
        return _error(exc)

    if not (area or "").strip():
        return {
            "status": "needs_clarification",
            "missing_field": "area",
            "options": supported,
            "question": f"Which area are you asking about: {_join_options(supported)}?",
            "data_notice": DATA_NOTICE,
        }

    area_name = _find_area(area, rows)
    if area_name is None:
        return {
            "status": "not_found",
            "requested_area": area,
            "supported_areas": supported,
            "message": f"No supplied incident record exists for '{area}'. The supplied records "
                       f"only cover {_join_options(supported)}.",
            "data_notice": DATA_NOTICE,
        }

    area_rows = [r for r in rows if r["area"] == area_name]
    types_in_area = _unique([r["incident_type"] for r in area_rows])

    if not (incident_type or "").strip():
        if len(types_in_area) == 1:
            return {"status": "found", "area": area_name, "records": area_rows,
                    "record_count": len(area_rows), "data_notice": DATA_NOTICE}
        return {
            "status": "needs_clarification",
            "area": area_name,
            "missing_field": "incident_type",
            "options": types_in_area,
            "question": f"{area_name} has more than one recorded incident. Which incident type are "
                        f"you asking about: {_join_options(types_in_area)}?",
            "data_notice": DATA_NOTICE,
        }

    matches = _match_option(incident_type, types_in_area)
    if len(matches) == 1:
        records = [r for r in area_rows if r["incident_type"] == matches[0]]
        return {"status": "found", "area": area_name, "incident_type": matches[0],
                "records": records, "record_count": len(records), "data_notice": DATA_NOTICE}
    if len(matches) > 1:
        return {
            "status": "needs_clarification",
            "area": area_name,
            "missing_field": "incident_type",
            "options": matches,
            "question": f"Which incident type in {area_name} do you mean: {_join_options(matches)}?",
            "data_notice": DATA_NOTICE,
        }
    return {
        "status": "not_found",
        "area": area_name,
        "requested_incident_type": incident_type,
        "recorded_incident_types_for_area": types_in_area,
        "message": f"No supplied incident record exists for '{incident_type}' in {area_name}. "
                   f"Recorded incident types for {area_name}: {_join_options(types_in_area)}.",
        "data_notice": DATA_NOTICE,
    }


# ---------------------------------------------------------------------------
# Tool 3 - get_safety_guidance
# ---------------------------------------------------------------------------
def get_safety_guidance(incident_type: str, priority: str = "") -> Dict:
    """Return the recorded safety guidance from safety_guidance.csv for an incident type.

    Use the priority from the incident record when one was found; otherwise use
    the priority returned by classify_issue. Never write your own safety advice.

    Args:
        incident_type: One of the supplied types: flood, landslide, blocked_route,
            immediate_danger or relief_request.
        priority: Optional priority (critical, urgent, high or normal). When empty,
            every guidance row for the incident type is returned.

    Returns:
        dict with status "found", "needs_clarification", "not_found" or "error".
        When found, "records" holds the supplied rows exactly as written
        (guidance_id, incident_type, priority, guidance, avoid, escalation_note,
        source_id, effective_date, data_status).
    """
    try:
        rows = _read_csv(GUIDANCE_FILE, GUIDANCE_COLUMNS)
    except DataPackError as exc:
        return _error(exc)

    types = _unique([r["incident_type"] for r in rows])
    if not (incident_type or "").strip():
        return {
            "status": "needs_clarification",
            "missing_field": "incident_type",
            "options": types,
            "question": f"Which situation do you need guidance for: {_join_options(types)}?",
            "data_notice": DATA_NOTICE,
        }

    matches = _match_option(incident_type, types)
    if not matches:
        return {
            "status": "not_found",
            "requested_incident_type": incident_type,
            "supported_incident_types": types,
            "message": f"No supplied safety guidance exists for '{incident_type}'.",
            "data_notice": DATA_NOTICE,
        }
    if len(matches) > 1:
        return {
            "status": "needs_clarification",
            "missing_field": "incident_type",
            "options": matches,
            "question": f"Which situation do you mean: {_join_options(matches)}?",
            "data_notice": DATA_NOTICE,
        }

    type_rows = [r for r in rows if r["incident_type"] == matches[0]]
    if (priority or "").strip():
        selected = [r for r in type_rows if _norm(r["priority"]) == _norm(priority)]
        if not selected:
            return {
                "status": "not_found",
                "incident_type": matches[0],
                "requested_priority": priority,
                "available_priorities": _unique([r["priority"] for r in type_rows]),
                "message": f"No supplied guidance for {matches[0]} at priority '{priority}'.",
                "data_notice": DATA_NOTICE,
            }
        return {"status": "found", "incident_type": matches[0], "records": selected,
                "data_notice": DATA_NOTICE}

    result = {"status": "found", "incident_type": matches[0], "records": type_rows,
              "data_notice": DATA_NOTICE}
    if len(type_rows) > 1:
        result["note"] = ("More than one priority level is recorded for this incident type. "
                          "Use the row whose priority matches the incident record.")
    return result


# ---------------------------------------------------------------------------
# Tool 4 - find_relief_point
# ---------------------------------------------------------------------------
def find_relief_point(area: str, assistance_type: str = "") -> Dict:
    """Find a listed shelter, relief centre or assistance point in relief_points.csv.

    Never guess the assistance type. If the area has more than one listed
    relief point and assistance_type is empty or ambiguous, this tool returns
    status "needs_clarification" with ONE focused question. A listing is not a
    live availability, capacity, transport or medical-capacity record.

    Args:
        area: Area name given by the user (Colombo, Ratnapura or Kegalle; case-insensitive).
        assistance_type: Optional assistance type given by the user, for example
            "temporary shelter", "relief supplies", "information point" or
            "first aid information". Leave empty if the user did not say it.

    Returns:
        dict with status "found", "needs_clarification", "not_found" or "error".
        When found, "records" holds the supplied rows exactly as written
        (relief_id, area, assistance_type, name, location_description, services,
        recorded_status, source_id, effective_date, data_status).
    """
    try:
        rows = _read_csv(RELIEF_FILE, RELIEF_COLUMNS)
        supported = _supported_areas()
    except DataPackError as exc:
        return _error(exc)

    if not (area or "").strip():
        return {
            "status": "needs_clarification",
            "missing_field": "area",
            "options": supported,
            "question": f"Which area do you need a relief point in: {_join_options(supported)}?",
            "data_notice": DATA_NOTICE,
        }

    area_name = _find_area(area, rows)
    if area_name is None:
        return {
            "status": "not_found",
            "requested_area": area,
            "supported_areas": supported,
            "message": f"No supplied relief point is listed for '{area}'. The supplied records "
                       f"only cover {_join_options(supported)}.",
            "data_notice": DATA_NOTICE,
        }

    area_rows = [dict(r, services_list=r["services"].split("|")) for r in rows if r["area"] == area_name]
    types_in_area = _unique([r["assistance_type"] for r in area_rows])

    if not (assistance_type or "").strip():
        if len(area_rows) == 1:
            return {"status": "found", "area": area_name, "records": area_rows,
                    "listing_notice": "Listed only; availability, space and supplies are not confirmed.",
                    "data_notice": DATA_NOTICE}
        return {
            "status": "needs_clarification",
            "area": area_name,
            "missing_field": "assistance_type",
            "options": types_in_area,
            "question": f"{area_name} has more than one listed relief point. Which assistance type "
                        f"do you need: {_join_options(types_in_area)}?",
            "data_notice": DATA_NOTICE,
        }

    matches = _match_option(assistance_type, types_in_area)
    if len(matches) == 1:
        records = [r for r in area_rows if r["assistance_type"] == matches[0]]
        return {"status": "found", "area": area_name, "assistance_type": matches[0],
                "records": records,
                "listing_notice": "Listed only; availability, space and supplies are not confirmed.",
                "data_notice": DATA_NOTICE}
    if len(matches) > 1:
        return {
            "status": "needs_clarification",
            "area": area_name,
            "missing_field": "assistance_type",
            "options": matches,
            "question": f"Which assistance type in {area_name} do you mean: {_join_options(matches)}?",
            "data_notice": DATA_NOTICE,
        }
    return {
        "status": "not_found",
        "area": area_name,
        "requested_assistance_type": assistance_type,
        "listed_assistance_types_for_area": types_in_area,
        "message": f"No supplied relief point of type '{assistance_type}' is listed for {area_name}. "
                   f"Listed assistance types for {area_name}: {_join_options(types_in_area)}.",
        "data_notice": DATA_NOTICE,
    }


# ---------------------------------------------------------------------------
# Tool 5 - get_source_metadata
# ---------------------------------------------------------------------------
def get_source_metadata(source_id: str) -> Dict:
    """Explain a source_id using the supplied source_register.md.

    Args:
        source_id: A source identifier returned by another tool, for example "DR-001".

    Returns:
        dict with status "found", "not_found" or "error". When found it contains
        source_id, record_group, description, effective_date, data_status and the
        register's note that the records are not live.
    """
    path = DATA_DIR / SOURCE_REGISTER_FILE
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return _error(DataPackError(f"Supplied data file '{SOURCE_REGISTER_FILE}' could not be read: {exc}"))

    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip().strip("`").strip() for c in line.strip("|").split("|")]
        if len(cells) < 5 or cells[0].lower() == "source id" or set(cells[0]) <= set("-: "):
            continue
        entries.append({
            "source_id": cells[0],
            "record_group": cells[1],
            "description": cells[2],
            "effective_date": cells[3],
            "data_status": cells[4],
        })
    if not entries:
        return _error(DataPackError(f"No source entries could be read from '{SOURCE_REGISTER_FILE}'."))

    register_note = " ".join(
        l.strip() for l in text.splitlines()
        if l.strip() and not l.strip().startswith(("|", "#"))
    )
    key = _norm(source_id)
    for entry in entries:
        if _norm(entry["source_id"]) == key:
            return dict(entry, status="found", register_note=register_note)
    return {
        "status": "not_found",
        "requested_source_id": source_id,
        "known_source_ids": [e["source_id"] for e in entries],
        "message": f"'{source_id}' is not listed in the supplied source register.",
    }

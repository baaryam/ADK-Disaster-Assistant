"""Offline checks for the Function tools (no API key or ADK needed).

Run from the project folder ADK_Disaster_Assistant:
    python -m pytest -q tests
or, without pytest:
    python tests/test_tools.py
"""
# test tools

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agents"))

from disaster_recovery_assistant import tools as t  # noqa: E402


def test_colombo_needs_incident_type():
    r = t.get_incident_status("colombo")
    assert r["status"] == "needs_clarification"
    assert r["missing_field"] == "incident_type"
    assert r["options"] == ["flood", "blocked_route"]
    assert r["question"].count("?") == 1


def test_colombo_flood_found_with_source_fields():
    r = t.get_incident_status("Colombo", "flood")
    assert r["status"] == "found"
    rec = r["records"][0]
    assert rec["incident_id"] == "INC-001"
    assert (rec["source_id"], rec["effective_date"], rec["data_status"]) == (
        "DR-001", "2026-08-19", "SUPPLIED-RECORD")


def test_incident_type_wording():
    assert t.get_incident_status("KEGALLE", "blocked route")["records"][0]["incident_id"] == "INC-006"
    assert t.get_incident_status("Ratnapura", "flooding")["records"][0]["incident_id"] == "INC-003"


def test_unsupported_area_not_found():
    r = t.get_incident_status("Galle", "flood")
    assert r["status"] == "not_found"
    assert r["supported_areas"] == ["Colombo", "Ratnapura", "Kegalle"]


def test_type_not_recorded_in_area():
    r = t.get_incident_status("Colombo", "landslide")
    assert r["status"] == "not_found"
    assert r["recorded_incident_types_for_area"] == ["flood", "blocked_route"]


def test_missing_area():
    assert t.get_incident_status("")["missing_field"] == "area"
    assert t.find_relief_point("")["missing_field"] == "area"


def test_relief_needs_assistance_type():
    r = t.find_relief_point("Kegalle")
    assert r["status"] == "needs_clarification"
    assert r["options"] == ["temporary_shelter", "first_aid_information"]


def test_relief_found():
    r = t.find_relief_point("Kegalle", "temporary shelter")
    assert r["status"] == "found" and r["records"][0]["relief_id"] == "RP-005"
    r = t.find_relief_point("kegalle", "first aid")
    assert r["records"][0]["relief_id"] == "RP-006"
    r = t.find_relief_point("Ratnapura", "relief supplies")
    assert r["records"][0]["services"] == "drinking water|dry food|hygiene supplies"


def test_relief_not_listed():
    r = t.find_relief_point("Colombo", "medical")
    assert r["status"] == "not_found"


def test_guidance_by_priority():
    assert t.get_safety_guidance("flood", "high")["records"][0]["guidance_id"] == "SG-001"
    assert t.get_safety_guidance("flood", "critical")["records"][0]["guidance_id"] == "SG-002"
    assert t.get_safety_guidance("blocked route", "urgent")["records"][0]["guidance_id"] == "SG-004"
    assert len(t.get_safety_guidance("flood")["records"]) == 2
    assert t.get_safety_guidance("tsunami")["status"] == "not_found"
    assert t.get_safety_guidance("landslide", "normal")["status"] == "not_found"


def test_classify_flood():
    r = t.classify_issue("My street in Colombo is flooded and floodwater is near my house.")
    assert r["status"] == "classified"
    assert (r["category"], r["priority"], r["rule_id"]) == ("flood", "high", "DR-R003")
    assert r["incident_types_to_check"] == ["flood"]
    assert r["immediate_danger"] is False


def test_classify_blocked_route_any_order():
    r = t.classify_issue("The road to my house in Kegalle is blocked by debris")
    assert r["category"] == "blocked_route" and r["priority"] == "urgent"


def test_classify_immediate_danger_first():
    r = t.classify_issue("Water is rising inside our house in Ratnapura and my grandmother is trapped upstairs.")
    assert r["category"] == "immediate_danger" and r["priority"] == "critical"
    assert r["immediate_danger"] is True
    assert r["incident_types_to_check"] == ["flood"]
    w = r["immediate_safety_warning"]
    assert w["guidance_id"] == "SG-005"
    assert "Contact the relevant local emergency service immediately" == w["escalation_note"]


def test_classify_active_landslide():
    r = t.classify_issue("There is an active landslide above our houses in Kegalle")
    assert r["category"] == "immediate_danger"
    assert "landslide" in r["incident_types_to_check"]


def test_classify_relief():
    r = t.classify_issue("I need a shelter and drinking water in Ratnapura")
    assert r["category"] == "relief_request" and r["priority"] == "normal"
    assert r["incident_types_to_check"] == []


def test_classify_no_match_and_empty():
    assert t.classify_issue("What time is it?")["status"] == "no_rule_matched"
    assert t.classify_issue("")["status"] == "needs_clarification"


def test_no_false_food_match():
    # 'food' must not match inside 'flood'
    r = t.classify_issue("flood")
    assert r["matched_categories"] == ["flood"]


def test_source_metadata():
    r = t.get_source_metadata("dr-003")
    assert r["status"] == "found" and r["record_group"] == "Relief points"
    assert r["data_status"] == "SUPPLIED-RECORD"
    assert t.get_source_metadata("DR-004")["status"] == "not_found"


def test_missing_data_file_is_error(tmp_path=None):
    original = t.DATA_DIR
    t.DATA_DIR = Path("/nonexistent-folder")
    try:
        assert t.get_incident_status("Colombo", "flood")["status"] == "error"
        assert t.classify_issue("flood")["status"] == "error"
        assert t.get_source_metadata("DR-001")["status"] == "error"
    finally:
        t.DATA_DIR = original


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for test in tests:
        test()
        print("PASS", test.__name__)
    print(f"All {len(tests)} tool checks passed.")

# Requirement checklist, data-pack summary and final audit

## A. Data-pack summary (exact supplied values)

**Supported areas:** Colombo, Ratnapura, Kegalle. Every record has `effective_date` 2026-08-19 and `data_status` SUPPLIED-RECORD.

| incident_id | area | incident_type | status | priority | source_id |
|---|---|---|---|---|---|
| INC-001 | Colombo | flood | monitoring | high | DR-001 |
| INC-002 | Colombo | blocked_route | restricted | urgent | DR-001 |
| INC-003 | Ratnapura | flood | warning_recorded | critical | DR-001 |
| INC-004 | Ratnapura | landslide | watch_recorded | critical | DR-001 |
| INC-005 | Kegalle | landslide | restricted_area | critical | DR-001 |
| INC-006 | Kegalle | blocked_route | closed_recorded | urgent | DR-001 |

Every area has **two** incident types, so an area-only status request always needs one question.

| rule_id | category | priority | keywords | source_id |
|---|---|---|---|---|
| DR-R001 | immediate_danger | critical | trapped, collapsed structure, serious injury, rising water inside, active landslide | DR-005 |
| DR-R002 | landslide | critical | landslide, slope movement, ground crack, falling rocks, mud movement | DR-005 |
| DR-R003 | flood | high | flood, floodwater, water rising, house flooded, river rising | DR-005 |
| DR-R004 | blocked_route | urgent | road blocked, route blocked, bridge closed, debris, access blocked | DR-005 |
| DR-R005 | relief_request | normal | shelter, relief centre, relief center, food, drinking water, assistance point | DR-005 |

| guidance_id | incident_type | priority | source_id |
|---|---|---|---|
| SG-001 | flood | high | DR-002 |
| SG-002 | flood | critical | DR-002 |
| SG-003 | landslide | critical | DR-002 |
| SG-004 | blocked_route | urgent | DR-002 |
| SG-005 | immediate_danger | critical | DR-002 |
| SG-006 | relief_request | normal | DR-002 |

| relief_id | area | assistance_type | name | source_id |
|---|---|---|---|---|
| RP-001 | Colombo | temporary_shelter | Colombo Community Relief Point A | DR-003 |
| RP-002 | Colombo | information_point | Colombo Assistance Information Point | DR-003 |
| RP-003 | Ratnapura | temporary_shelter | Ratnapura Community Relief Point A | DR-003 |
| RP-004 | Ratnapura | relief_supplies | Ratnapura Relief Supplies Point | DR-003 |
| RP-005 | Kegalle | temporary_shelter | Kegalle Community Relief Point A | DR-003 |
| RP-006 | Kegalle | first_aid_information | Kegalle First-Aid Support Point | DR-003 |

Every area lists **two** relief points, so an area-only relief request always needs one question. Source IDs: DR-001 (incidents), DR-002 (guidance), DR-003 (relief points), DR-005 (rules). **DR-004 is not in the register** and returns not_found.

## B. Final audit against Assignment 2

| Requirement | Implementation | Evidence needed | Status |
|---|---|---|---|
| LLM Agent (root + specialists) | disaster_recovery_coordinator + 9 specialist LLM agents | F1 graph | Implemented |
| Sequential Agent | report_triage_pipeline (4 ordered stages) | F1, F2 | Implemented |
| Parallel Agent | parallel_lookup (incident ‖ relief) | F1, F3 | Implemented |
| Loop Agent, bounded | clarification_loop, max_iterations 3, exit_loop | F1, F4 | Implemented |
| ≥ 4 Function tools, documented | 5 tools in tools.py; Section C tables | F1 tool panel | Implemented |
| Same contract: Python / Builder / agent | Signatures, fully-qualified names and owners appear in the code, the YAML files and Sections C–D | Sections C–D | Implemented |
| Tools read supplied data, not hard-coded | CSV/MD read at run time from `data/` | tests, code | Implemented (19 offline checks pass) |
| Deterministic classification | classify_issue rules only; the LLM is told not to change them | F2 trace | Implemented |
| Immediate-danger warning, no dispatch, no numbers | DR-R001 + SG-005 shown first; instructions forbid numbers and dispatch | optional immediate-danger run | Implemented |
| Multiple incidents per area → one question | get_incident_status needs_clarification | F4 | Implemented |
| Multiple relief points per area → one question | find_relief_point needs_clarification | optional run ("shelters in Kegalle") | Implemented |
| Missing info asked, never guessed | tools + agent instructions | F4 | Implemented |
| Not-found / data-error results | not_found / error statuses | F5 | Implemented |
| Unsupported/unsafe request refusal | root instruction | F5 optional prompt | Implemented |
| source_id, effective_date, data_status preserved | records returned unchanged; Source line in every answer | F2–F4 answers | Implemented |
| Records never presented as live | data_notice + closing sentence in every answer | F2–F4 answers | Implemented |
| No sensitive identifiers requested | instructions in root, intake and follow-up agents | – | Implemented |
| Section B flowchart | Figure B1 (PlantUML) + Mermaid source | report | Done |
| Sections C, D, E tables | filled in the report | report | Done |
| Section F actual results | placeholders only | **student runs the tests** | Pending (student) |
| Screenshots | 9 placeholders + checklist | **student captures** | Pending (student) |
| PDF export | report .docx → PDF | student | Pending (student) |
| ZIP without venv / .env / secrets | README §6 command; .gitignore; .env.example only | student | Pending (student) |

**Known limitation:** keyword matching only uses the supplied keywords, so danger described in completely different words (for example "injured" or "the roof fell") is not classified as immediate_danger. The assistant then asks for a short description instead of guessing a category.

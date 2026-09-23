# Flood, Landslide and Disaster Recovery Assistant — Google ADK Web project

INTE 22303 – Artificial Intelligence (24/25), Assignment 2 – Google ADK

This project is a Sri Lanka flood, landslide and disaster-recovery assistant. It uses all four ADK Web Builder agent types (LLM, Sequential, Parallel and Loop) and five Python Function tools. The tools read the supplied data pack at run time, so no record is hard-coded.

---

## 1. Project structure

```
ADK_Disaster_Assistant/                 <- open PowerShell here; this is the folder you ZIP
├── agents/                             <- the "agents directory" given to `adk web`
│   └── disaster_recovery_assistant/    <- the ADK app (name shown in ADK Web)
│       ├── root_agent.yaml             <- root LLM Agent (coordinator)
│       ├── report_triage_pipeline.yaml <- Sequential Agent (E1)
│       ├── intake_agent.yaml               stage 1
│       ├── classification_agent.yaml       stage 2  (classify_issue)
│       ├── incident_lookup_agent.yaml      stage 3  (get_incident_status)
│       ├── safety_response_agent.yaml      stage 4  (get_safety_guidance, get_source_metadata)
│       ├── area_overview_workflow.yaml <- Sequential wrapper: parallel lookups -> combiner
│       ├── parallel_lookup.yaml        <- Parallel Agent (E2)
│       ├── incident_branch_agent.yaml      branch 1 (get_incident_status)
│       ├── relief_branch_agent.yaml        branch 2 (find_relief_point)
│       ├── overview_combiner_agent.yaml    combines both (get_source_metadata)
│       ├── clarification_loop.yaml     <- Loop Agent (E3), max_iterations: 3
│       ├── follow_up_agent.yaml            loop step 1 (get_incident_status, find_relief_point, get_source_metadata)
│       ├── loop_controller_agent.yaml      loop step 2 (built-in exit_loop)
│       ├── tools.py                    <- the 5 Python Function tools
│       ├── .env.example                <- copy to .env and add YOUR key (never submit .env)
│       └── data/                       <- the supplied data pack, unchanged
│           ├── incident_status.csv  issue_rules.csv  safety_guidance.csv
│           ├── relief_points.csv    knowledge_base.md  source_register.md
├── tests/test_tools.py                 <- 19 offline checks of the tools (no API key needed)
├── docs/                               <- diagrams for the report (Mermaid + PlantUML sources and PNGs)
├── requirements.txt
└── README.md
```

Agent tree:

```
disaster_recovery_coordinator (LLM Agent, root)
├── report_triage_pipeline (Sequential)   intake -> classification -> incident lookup -> safety response
├── area_overview_workflow (Sequential)
│   ├── parallel_lookup (Parallel)        incident_branch_agent || relief_branch_agent
│   └── overview_combiner_agent (LLM)
└── clarification_loop (Loop, max 3)      follow_up_agent -> loop_controller_agent (exit_loop)
```

---

## 2. One-time setup on Windows

### 2.1 Install prerequisites
1. Install **Python 3.12** from https://www.python.org/downloads/. On the first installer screen, tick **"Add python.exe to PATH"**.
2. Open **PowerShell** and check it worked:
   ```powershell
   py --version
   ```
3. Get a free Gemini API key from **Google AI Studio** (https://aistudio.google.com → *Get API key*). Keep it private. Never paste it into the report and never let it appear in a screenshot.

### 2.2 Create the virtual environment and install ADK
```powershell
cd "C:\Users\Hp\OneDrive\Desktop\Year 2 Sem 2 24_25 IM_2022_133\INTE 22303 Artificial intelligence\Assignment\ADK_Disaster_Assistant"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
adk --version
```
If `Activate.ps1` is blocked, run this once and then activate again:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
Each time you open a new PowerShell window, `cd` to the project folder and run `.\.venv\Scripts\Activate.ps1` again.

### 2.3 Check the tools (no API key needed)
```powershell
python -m pytest -q tests
```
You should see **19 passed**. This shows that the tools read the data pack correctly.

### 2.4 Add your API key
```powershell
Copy-Item agents\disaster_recovery_assistant\.env.example agents\disaster_recovery_assistant\.env
notepad agents\disaster_recovery_assistant\.env
```
Replace `PASTE_YOUR_OWN_KEY_HERE` with your key, then save and close Notepad. The `.env` file must contain:
```
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=<your key>
```

---

## 3. Start ADK Web and load the project

```powershell
adk web agents
```
Open **http://127.0.0.1:8000** in your browser, then choose **disaster_recovery_assistant** from the app dropdown in the top-left corner.

- **Chat:** type prompts in the chat box.
- **Events / Trace:** the left panel shows every agent step and every tool call. Click an event to see its details, including the tool arguments and the returned dictionary.
- **Web Builder (graph/config view):** click the **edit (pencil) button** next to the app name. It shows the agent graph and lets you select each agent to see its type, instruction, sub-agents and tools. Button labels can differ slightly between ADK versions, so look for the edit/builder icon beside the app selector.

To stop the server, press `Ctrl + C` in PowerShell. Restart it after you change any file.

### 3.1 Registering and connecting in the Web Builder
The YAML files already register every agent, workflow and tool, so opening the app in the builder shows the finished configuration. If your lecturer wants you to build it by hand in the builder, create the same structure with the **+** buttons:

| Step | In the Web Builder | Value to enter |
|---|---|---|
| 1 | Create a new app (**+** next to *Select an app*) | `disaster_recovery_assistant` (then copy `tools.py` and `data/` into that folder) |
| 2 | Root agent | LLM Agent `disaster_recovery_coordinator`; paste the instruction from `root_agent.yaml` |
| 3 | **+ Sub Agents → Sequential Agent** | `report_triage_pipeline`, then add 4 LLM sub-agents in this order: intake, classification, incident_lookup, safety_response |
| 4 | **+ Sub Agents → Sequential Agent** | `area_overview_workflow`, then add a **Parallel Agent** `parallel_lookup` (with the 2 branch LLM agents) and then the LLM agent `overview_combiner_agent` |
| 5 | **+ Sub Agents → Loop Agent** | `clarification_loop`, max iterations **3**, with LLM agents `follow_up_agent` and `loop_controller_agent` |
| 6 | **+ Tools → Function tool** on each owning agent | `disaster_recovery_assistant.tools.classify_issue`, `...get_incident_status`, `...get_safety_guidance`, `...find_relief_point`, `...get_source_metadata` |
| 7 | **+ Tools → Built-in tool** on `loop_controller_agent` | `exit_loop` |
| 8 | For each LLM agent | copy the instruction, `output_key`, and tick disallow transfer to parent/peers, all from its YAML file |
| 9 | Click **Save** | the builder writes the YAML files into the app folder |

The Function tool name must be **fully qualified** (`app_folder.module.function`). This is the same contract used in the Python code and in Section C of the report.

---

## 4. Section F test cases

Start a **new session** for each test (use the *New session* button) so earlier turns do not affect the routing. Everything under "Expected" is a prediction. **Only write the Actual result after you have run the test.**

### F1 – Agent and tool configuration
- **Action:** open the app in the Web Builder (edit) view.
- **Expected:** the graph shows the root LLM agent, two Sequential agents, one Parallel agent and one Loop agent (`max_iterations: 3`). The tool panels show the 5 Function tools and the built-in `exit_loop`.
- **Screenshots:** (a) the whole graph; (b) the tools panel of `follow_up_agent` (3 tools) and of `safety_response_agent` or `classification_agent`. Use extra screenshots if you need them so that all 5 tools are visible.
- **Actual result wording (adapt it to what you see):** "The Web Builder showed disaster_recovery_coordinator (LLM) with report_triage_pipeline and area_overview_workflow (Sequential), parallel_lookup (Parallel) and clarification_loop (Loop, max 3). The tools classify_issue, get_incident_status, get_safety_guidance, find_relief_point and get_source_metadata were registered on …"

### F2 – Sequential workflow
- **Prompt:** `My street in Colombo is flooded and the floodwater is near my house. What should I do?`
- **Expected agents in order:** disaster_recovery_coordinator → (transfer) report_triage_pipeline → intake_agent → classification_agent → incident_lookup_agent → safety_response_agent.
- **Expected tools:** `classify_issue` → flood / high / DR-R003. `get_incident_status("Colombo","flood")` → INC-001 (monitoring, high). `get_safety_guidance("flood","high")` → SG-001.
- **Expected answer:** classification, incident INC-001, guidance SG-001, source lines `DR-001 | 2026-08-19 | SUPPLIED-RECORD` and `DR-002 …`, and the not-live notice.
- **Events to look for:** the four stage agents appear in order, and each tool call appears under the agent that owns it.
- **Screenshots:** the graph with `report_triage_pipeline` selected, and the Events trace showing the ordered stages. Expand the classify_issue response.

### F3 – Parallel workflow
- **Prompt:** `I am in Kegalle. Show me the landslide incident status and the listed temporary shelter.`
- **Expected agents:** coordinator → area_overview_workflow → parallel_lookup → incident_branch_agent **and** relief_branch_agent → overview_combiner_agent.
- **Expected tools:** `get_incident_status("Kegalle","landslide")` → INC-005 (restricted_area, critical). `find_relief_point("Kegalle","temporary shelter")` → RP-005 Kegalle Community Relief Point A.
- **Events to look for:** both branch agents and both tool calls appear in the same run, before the combiner.
- **Screenshots:** the graph with parallel_lookup, and the Events trace showing both branches and the combined answer.

### F4 – Loop workflow (two turns)
- **Turn 1:** `What is happening in Colombo?`
  **Expected:** coordinator → clarification_loop → follow_up_agent calls `get_incident_status("Colombo","")` → `needs_clarification`. The assistant asks **one** question: *"Colombo has more than one recorded incident. Which incident type are you asking about: flood or blocked_route?"* Then loop_controller_agent calls `exit_loop`.
- **Turn 2:** `flood`
  **Expected:** coordinator → clarification_loop again → `get_incident_status("Colombo","flood")` → INC-001 with its source line → `exit_loop`.
- **Events to look for:** in turn 1, needs_clarification followed by exit_loop, with no guessed incident; in turn 2, the found record.
- **Screenshots:** the chat showing the question and the answer, and the Events trace showing the bounded loop (with exit_loop visible).

### F5 – Unsupported or unavailable request
- **Prompt:** `What is the flood status in Galle?`
- **Expected:** clarification_loop → `get_incident_status("Galle","flood")` → `not_found`. The answer says there is no supplied record and that the records cover only Colombo, Ratnapura and Kegalle. Nothing is invented.
- **Optional second prompt (a refusal):** `Please send a rescue team and reserve a shelter place for my family in Kegalle.` Expected: the coordinator refuses dispatch and reservation, says what it can do, and gives no phone numbers.
- **Screenshot:** the Events trace showing the not_found tool response and the safe answer.

### Optional extra evidence – immediate danger
- **Prompt:** `Water is rising inside our house in Ratnapura and my grandmother is trapped upstairs.`
- **Expected:** classify_issue returns **immediate_danger** (DR-R001, critical), and the answer opens with **IMMEDIATE SAFETY WARNING** (SG-005 text). The answer tells the user to move away and contact the relevant local emergency service or authority, says it cannot dispatch help, and gives no phone number. It then shows flood incident INC-003 (critical) and guidance SG-002.

---

## 5. Screenshot checklist

| # | Screen to open | Must be visible | Must NOT be visible | Trace should show | File name |
|---|---|---|---|---|---|
| 1 | Web Builder graph | app name, all 4 agent types | `.env`, key, browser bookmarks or profile | – | `F1a_builder_graph.png` |
| 2 | Web Builder tool panel(s) | 5 Function tool names (+ exit_loop) | key / terminal with key | – | `F1b_builder_tools.png` |
| 3 | Graph with report_triage_pipeline | the 4 stages in order | key | – | `F2a_sequential_graph.png` |
| 4 | Events trace, F2 | prompt, 4 stages in order, classify_issue result | key | ordered execution | `F2b_sequential_events.png` |
| 5 | Graph with parallel_lookup | both branches | key | – | `F3a_parallel_graph.png` |
| 6 | Events trace, F3 | both branch tool calls, combined answer | key | both branches | `F3b_parallel_events.png` |
| 7 | Chat, F4 | the one question, "flood", the INC-001 answer | key | – | `F4a_loop_chat.png` |
| 8 | Events trace, F4 | needs_clarification → exit_loop, then found | key | bounded follow-up | `F4b_loop_events.png` |
| 9 | Events trace, F5 | not_found response and safe answer | key | safe result | `F5_unsupported_events.png` |

Rules: keep the app name `disaster_recovery_assistant` visible, zoom the browser so the text is readable in the PDF (Ctrl + +), and never capture the terminal while `.env` or the key is open. Do not include your real name, NIC or other personal details in any prompt.

---

## 6. Submission

1. **PDF:** open `Assignment_2_ADK_Report.docx` and add your student number. Paste the screenshots at the yellow placeholders and write each Actual result. Delete all the yellow highlight, then use *File → Save As → PDF*.
2. **ZIP (without the venv or your key):**
   ```powershell
   # from the project folder, with the ADK server stopped
   Move-Item agents\disaster_recovery_assistant\.env ..\my_key.env.backup
   Get-ChildItem -Recurse -Directory -Force -Include __pycache__,.adk,.pytest_cache | Remove-Item -Recurse -Force
   Compress-Archive -Path agents, tests, docs, requirements.txt, README.md -DestinationPath ..\ADK_Disaster_Assistant.zip -Force
   Move-Item ..\my_key.env.backup agents\disaster_recovery_assistant\.env
   ```
   Open the ZIP and check that it contains **no** `.env` and **no** `.venv`.

---

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `adk` is not recognised | Activate the venv: `.\.venv\Scripts\Activate.ps1` |
| App not in dropdown | Run `adk web agents` from the project folder, not from inside `agents` |
| `ModuleNotFoundError: disaster_recovery_assistant` | The app folder must be named exactly `disaster_recovery_assistant` and must sit directly in `agents` |
| 429 / 503 (quota or high demand) | The free tier limits requests per minute, and the sequential workflow makes several model calls. Wait one minute and retry |
| 404 model not found / no longer available | The agents use `gemini-3.6-flash` (older models such as gemini-2.5-flash are closed to new keys). To change the model in all YAML files at once: `Get-ChildItem agents\disaster_recovery_assistant\*.yaml \| ForEach-Object { (Get-Content $_) -replace 'model: gemini-[a-z0-9.\-]+','model: NEW-MODEL' \| Set-Content $_ }` |
| API key error | Check `.env` is in `agents\disaster_recovery_assistant\`, then restart `adk web` |
| Answer skipped a question or guessed | Start a new session and re-send the prompt. The tools never guess; check the tool response in Events |

---

## 8. Design notes

- **Deterministic classification:** `classify_issue` uses only the keywords in `issue_rules.csv`. The first matching rule in file order is the primary classification, so DR-R001 immediate_danger takes precedence. Matching is case-insensitive, allows word endings (flood → flooded), and accepts multi-word keywords in any order within one sentence (road blocked → "the road is blocked"). No synonyms are added. Wording that uses none of the supplied keywords (for example "injured" instead of "serious injury") is reported as `no_rule_matched`, and the assistant asks for a short description instead of guessing.
- **No guessing:** when an area has several incidents or relief points and the type is not given, the tool returns `needs_clarification` with one question built from the supplied values.
- **Source fields:** every record is returned with its supplied `source_id`, `effective_date` and `data_status`, and every final answer shows them and says the records are not live.
- **Safety boundary:** the assistant never dispatches help, never guarantees safety, never gives phone numbers and never requests NIC numbers, passwords, OTPs or payment details.
#   A D K - D i s a s t e r - A s s i s t a n t  
 
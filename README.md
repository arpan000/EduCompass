# EduCompass — Agentic AI MBA College Recommender

EduCompass helps students shortlist MBA programmes in India using their academics, entrance-exam results, budget, location, career goal and priorities. The intended output is a personalised, source-linked Excel comparison of the best-fit colleges.

> **Status:** Academic prototype. Configure credentials and backend URLs after importing the n8n workflow. Test the complete evidence-audit, ranking and Excel path before treating results as production-verified.

## Problem Statement

MBA information is spread across college websites, regulators and third-party portals. Students may struggle to compare eligibility, entrance cutoffs, fees and placements, while published figures can refer to different years or programmes. EduCompass aims to reduce this research gap by turning a student's profile into a structured comparison backed by source links.

## Workflow

```text
Student chat → Agent 1 profile extraction → Validate profile
     ↓ incomplete                         ↓ complete
 Ask clarification                  Tavily college discovery
                                         ↓
                            Python candidate selection
                                         ↓
                                 Tavily research
                                         ↓
                          Python evidence extraction
                                         ↓
                            Agent 2 evidence audit
                                         ↓
                         Fit/ranking → Excel output
```

- **Agent 1 — Profile & Research Planner:** OpenAI `gpt-5-mini` in the exported workflow. Extracts the student's information and asks follow-up questions. n8n Simple Memory supports multi-turn clarification.
- **Agent 2 — Evidence Auditor:** Ollama `llama3.2:3b`. Reviews compact evidence for college/programme identity, exam and year, placement scope and conflicting sources.
- **Python/FastAPI:** Handles candidate filtering, evidence extraction and deterministic calculations; n8n orchestrates the workflow.

## Technology Stack

- **n8n** — workflow orchestration and file generation
- **OpenAI `gpt-5-mini`** — student-profile agent
- **Ollama `llama3.2:3b`** — evidence-auditing agent
- **Tavily Search API** — web research
- **Python + FastAPI** — backend services and API endpoints
- **SQLite** — local persistence for college and source evidence
- **JavaScript** — n8n data transformation
- **Excel/XLSX** — intended student-facing result

## Student Profile

The workflow is designed to collect:

- Undergraduate degree, discipline, score type/score and completion year
- MBA specialisation and preferred city/region (or “Anywhere in India”)
- Maximum budget and study mode
- Full-time work experience
- Entrance exam(s), status, year and score/percentile when available
- Exam flexibility: exclusive, preferred or open
- Career goal and priorities, such as placement, ROI and career fit

A planned exam does not need a score. A taken exam with a missing result should trigger clarification. Invalid or contradictory values should be corrected rather than guessed; test these cases against the current workflow.

## Research Quality

Source priority: **official college/programme sources → regulators/accreditors → reputable third-party sources → community feedback**. Keep the exam and year attached to every cutoff. Distinguish programme-specific placement data from institution-wide results, and average/median/highest packages from each other. Label secondary estimates clearly. If evidence is insufficient, use “Not verified in researched sources” instead of inventing data.

The intended Excel includes college/programme, location, exams and 2024/2025 cutoffs, fees, average/median package, placement percentage, recruiters, specialisations, curriculum, eligibility, reservation information where relevant, nearby business/technology hub, ROI, profile fit, caveats and sources.

## Repository Structure

```text
backend/
├── app/main.py
├── app/database.py
├── app/services/
│   ├── candidate_discovery.py
│   ├── evidence_service.py
│   ├── fact_extractor.py
│   ├── fit_engine.py
│   ├── pdf_reader.py
│   ├── report_generator.py
│   └── verification_service.py
├── data/
├── reports/
└── requirements.txt
workflows/educompass-master-orchestrator.json
```

## Run Locally

Requires Python 3.11 or compatible, n8n, an OpenAI credential, a Tavily API key, and Ollama with `llama3.2:3b`.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check `http://127.0.0.1:8000/health`. Import `workflows/educompass-master-orchestrator.json` into n8n, configure your own credentials and confirm the backend URL is reachable from n8n. If n8n runs in Docker, `127.0.0.1` may refer to the container rather than the host. The exported workflow is inactive by default.

## Example Input

```text
I completed B.Tech in Information Technology with 8.4 CGPA in 2026.
I want an MBA in Business Analytics and prefer Pune or Bangalore.
My maximum budget is ₹14 lakh. I took CAT in 2025 and scored 92 percentile.
I want to become a Business Analyst, prefer full-time campus study, have no full-time work experience, and am open to other entrance exams.
My top priorities are placement, ROI and career fit.
```

## Main API Endpoints

- `GET /health` — API health check
- `POST /candidates/discover` — selects candidate colleges
- `POST /evidence/extract` — extracts facts from research evidence

See `backend/app/main.py` for current endpoint definitions.

## Limitations & Security

This is a shortlisting aid, not an admissions authority; historical cutoffs do not guarantee admission, and fees/placements can change. Before claiming a validated Top 10, test that Agent 2 output is parsed, merged with extracted evidence, ranked, and passed to the Excel node in the expected schema.

Never commit `.env` files, API keys, credentials, private keys, virtual environments, local databases or unsanitised student data. Store secrets in n8n Credentials or environment variables and review workflow exports before publishing.

<img width="1229" height="302" alt="image" src="https://github.com/user-attachments/assets/fe5aff04-8a6e-4353-9df8-874b7fa0a111" />



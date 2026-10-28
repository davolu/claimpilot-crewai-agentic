# 🩺 ClaimPilot

AI that gets insurance claims approved the first time. Built with
[CrewAI](https://www.crewai.com) (agents) and [Streamlit](https://streamlit.io) (interface).

A clinic uploads a patient visit's documents (bill, clinical notes, …). Four AI
agents check them against the insurer's rules, fix what they can, and produce a
submission-ready claim. A human reviews and approves before anything is sent.

## Pipeline

```
Upload docs ──▶ 📄 Extractor ──▶ 🔍 Rule Checker ──▶ 🔧 Fixer ──▶ ✍️ Claim Writer ──▶ 👤 Human review
                 structured        issues w/ rule       auto-fixes +     clean claim +      approve /
                 visit data        citations            staff actions    guardrail check    send back
```

## Quick start

```bash
git clone https://github.com/davolu/claimpilot-crewai-agentic.git
cd claimpilot-crewai-agentic
python3 -m venv .venv
# --only-binary=cryptography matters on Intel Macs: the newest cryptography
# has no prebuilt wheel there and would try to compile with Rust.
.venv/bin/pip install --only-binary=cryptography -r requirements.txt

# Optional — for live AI agents (otherwise use Demo mode in the UI):
export ANTHROPIC_API_KEY=sk-ant-...   # or OPENAI_API_KEY

.venv/bin/streamlit run app.py
```

Then in the browser: click **"Use sample visit"** → **"Run claim check"** and
walk through the flow. The sample visit deliberately contains four classic
rejection causes (wrong member-ID format, missing x-ray, non-covered cosmetic
item, missing prior authorization) so you can see every stage do its job.

## Project layout

| Path | What it is |
|---|---|
| `app.py` | Streamlit interface (upload → review → approve → download) |
| `claimpilot/crew.py` | The four CrewAI agents, tasks, and the submission guardrail |
| `claimpilot/models.py` | Pydantic models — all agent output is structured |
| `claimpilot/knowledge/denticare_rules.md` | Insurer rule book (add one file per insurer) |
| `claimpilot/demo.py` | Canned pipeline output for demo mode (no API key) |
| `sample_docs/` | A sample patient visit to test with |

## Adding an insurer

1. Write `claimpilot/knowledge/<insurer>_rules.md` in the same style (rule IDs!).
2. Add the insurer to the selectbox in `app.py`.
3. Pass the insurer key to `run_pipeline(documents_text, insurer="<insurer>")`.

## Not yet in the MVP (by design)

- OCR of scanned images / photos (the pipeline accepts .txt and text-based .pdf;
  plug in vision later for photographed bills)
- Memory of past rejections per insurer (CrewAI memory)
- Learning from staff corrections (CrewAI training)
- Dashboard of money recovered / rejection rate

⚠️ **Privacy**: this prototype processes everything locally except the LLM calls.
Before using real patient data, you need a compliant LLM arrangement
(HIPAA BAA / GDPR DPA), encryption at rest, and access controls.

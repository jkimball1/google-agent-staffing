# Dynamic Agent Staffing Optimization

**DADS 5250: Generative AI in Practice · Module 7 Hackathon**

## Project overview

This project develops a staffing-planning application for Google Ads advertiser support operations across 22 countries.

Using historical advertiser sign-ups from 2024–2025, the application forecasts eligible advertiser demand for 2026 and recommends monthly support-agent staffing levels. The model accounts for agent capacity, 60-day advertiser support assignments, waiting periods, hiring and training delays, and termination costs.

The project combines four components:

1. **Data preparation and forecasting:** clean historical data and estimate eligible advertiser arrivals in 2026.
2. **Staffing simulation:** model how advertiser demand interacts with staffing capacity, support assignments, waiting times, and agent availability.
3. **Optimization and financial evaluation:** compare staffing strategies on operational performance, estimated incremental advertising revenue, staffing costs, and demand uncertainty.
4. **GenAI planning assistant:** a natural-language interface for exploring staffing recommendations, evaluating alternative scenarios, and generating structured explanations.

The final application will produce a month-by-month staffing plan for 2026, financial and operational comparisons, sensitivity analyses, and AI-generated explanations grounded in the planning model.

### Development approach

The project is split into four modules that can be developed and tested independently using shared sample inputs and agreed interfaces ([INTERFACES.md](INTERFACES.md)). The modules are then integrated into a single executable Jupyter notebook.

The application uses course GenAI techniques, including LangChain, structured outputs, and prompt engineering.

### Deliverables

- [ ] Executed Jupyter notebook: [`notebooks/final_submission.ipynb`](notebooks/final_submission.ipynb)
- [ ] 2026 monthly staffing plan for all 22 countries (264 rows): `outputs/plan_2026.csv`
- [ ] Analysis of staffing decisions, financial outcomes, assumptions, and demand sensitivity
- [ ] This repository: code, setup instructions, architecture, team contributions
- [ ] Three-minute demo video: *link TBD*

## Setup

```bash
git clone <repo-url>
cd google-agent-staffing
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then add your API key
```

The course workbook is already in `data/raw/` (see [`data/raw/README.md`](data/raw/README.md)). The repo must stay private because of it.

Check that everything is wired up:

```bash
pytest
```

## Repository layout

```
├── INTERFACES.md            shared function signatures and data formats (read this first)
├── data/
│   ├── raw/                 course workbook (committed; keep repo private)
│   └── sample/              stand-in files for independent development (not results)
├── src/
│   ├── schemas.py           column contracts + validate()
│   ├── forecasting/         Member 1: forecast.py
│   ├── simulation/          Member 2: simulator.py
│   ├── optimization/        Member 3: optimizer.py, financials.py, scenarios.py
│   └── genai/               Member 4: assistant.py, prompts.py
├── outputs/                 generated plan_2026.csv, sensitivity results
├── notebooks/               final_submission.ipynb (the graded deliverable)
├── tests/                   interface and module tests
└── docs/                    assumptions, architecture, AI-use disclosure
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for the diagram and [docs/assumptions.md](docs/assumptions.md) for the modeling decisions.

## Team and contributions

| Role | Member | Folder | Branch | Notebook sections |
|---|---|---|---|---|
| 1. Data & forecasting | TBD | `src/forecasting/` | `feature/forecasting` | 2 |
| 2. Staffing simulation | Mer McFadden (@mcfadd22) | `src/simulation/` | `feature/simulation` | 3 |
| 3. Optimization & financials | Mer McFadden (@mcfadd22) | `src/optimization/` | `feature/optimization` | 4, 5 |
| 4. GenAI app & notebook integration | Enrique Mendez | `src/genai/`, `notebooks/` | `feature/genai` | 6 |

Shared by everyone: sections 1, 7, and 8, documentation for your own module, a segment of the video, and review of other members' PRs.

Video assembly: TBD · Canvas submission: TBD

## How we work

1. **Work on your own branch**, mostly inside your own folder.
2. **Build against `data/sample/`** until the upstream module is ready. They're stand-ins, not results. See `INTERFACES.md`.
3. **Don't change a contract alone.** Changes to `INTERFACES.md` and `src/schemas.py` need the affected owners to agree.
4. **Open a PR** when your piece works. At least one other member reviews before merging. Keep `main` runnable.
5. **Only the Member 4 owner edits the final notebook.** Everyone else puts code in `src/` and sends notebook text and plots to them through their PR or Issue.
6. **Never commit** `.env` or API keys. **Keep the repo private**, because it contains the course data.
7. **Log AI use** in [docs/AI_USE.md](docs/AI_USE.md) as you go.

## Timeline

| Day | Goal |
|---|---|
| Sat 10/24 | Claim roles, confirm interfaces and assumptions, start building |
| Sun 10/25 | Keep building; **push working versions by evening** |
| Mon 10/26 | Connect components, troubleshoot |
| Tue 10/27 | Full run-through, finalize README, record and assemble video |
| Wed 10/28 | Buffer for fixes, then submit |

## AI-use disclosure

See [docs/AI_USE.md](docs/AI_USE.md).

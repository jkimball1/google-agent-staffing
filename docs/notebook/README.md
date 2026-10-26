# Notebook drafts

Each role writes its part of the submission here as one ready-to-paste Markdown file and includes it in its PR. The notebook owner pastes the notebook cells into `notebooks/final_submission.ipynb`. The README and video owner copies the rest. `section3_simulation.md` is a complete example to copy.

| File | Role | Notebook section |
|---|---|---|
| `section2_forecast.md` | Role 1 | 2. Historical data and demand forecast |
| `section3_simulation.md` | Role 2 | 3. Staffing simulation |
| `section4_optimization.md` | Role 3 | 4. Staffing optimization and 5. Sensitivity analysis |
| `section6_genai.md` | Role 4 | 6. GenAI planning assistant |

## What each file contains

1. **Notebook cells**, each labeled **[markdown cell]** or **[code cell]**. Code cells should run in order after the notebook's setup cell, which puts the repo root on `sys.path` and defines `ROOT`. If a cell needs a variable from an earlier section (for example `demand_df`), say so at the top of the file.
2. **For the README:** a short component description of your part.
3. **For notebook section 7:** limitations of your part.
4. **For notebook section 8:** your contribution line, and an AI-use note saying which parts of your work were AI-generated or AI-assisted and how you checked them. Also add the details as rows in `docs/AI_USE.md`.
5. **For the video:** a script of about 30 seconds, with a **[Show: …]** cue before each line so whoever records the walkthrough knows what to have on screen.

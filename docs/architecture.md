# Architecture

```mermaid
flowchart LR
    WB[(Course workbook<br/>data/raw/)] --> F

    subgraph M1[Member 1: Forecasting]
        F[clean_signups<br/>forecast_demand<br/>load_country_parameters]
    end

    subgraph M2[Member 2: Simulation]
        S[simulate_plan<br/>daily engine, monthly summary]
    end

    subgraph M3[Member 3: Optimization & Financials]
        O[optimize_staffing]
        SC[run_scenario<br/>sensitivity_table]
        FIN[financials]
    end

    subgraph M4[Member 4: GenAI]
        Q[User question] --> P[LangChain<br/>structured output<br/>→ ScenarioRequest]
        P --> SC
        SC --> E[LLM explanation<br/>→ StaffingMemo]
    end

    F -- demand_df --> O
    F -- country_parameters_df --> O
    O -- staffing_plan_df --> S
    S -- results_df --> O
    FIN --> O
    O --> OUT[(outputs/plan_2026.csv)]
    O --> SC
    OUT --> NB[notebooks/final_submission.ipynb]
    E --> NB
```

## Course techniques used (need at least two)

| Technique | Where |
|---|---|
| LangChain | `src/genai/assistant.py`: chains from parsing to tool call to explanation |
| Structured output | `ScenarioRequest` and `StaffingMemo` Pydantic models |
| Prompt engineering | `src/genai/prompts.py`: parsing and grounded-explanation prompts |
| *(optional)* Agents / tool calling | LLM chooses when to call `run_scenario` |

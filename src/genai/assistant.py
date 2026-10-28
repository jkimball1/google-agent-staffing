
"""Role 4 — GenAI Planning Assistant.

Owner: Enrique Mendez

Uses LangChain, Pydantic structured output, and prompt
engineering to explain staffing scenarios using the
team's quantitative optimization model.
"""

import json
import math
import os

import pandas as pd
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .prompts import PARSE_SYSTEM_PROMPT, EXPLAIN_SYSTEM_PROMPT


# 1. Structured request
class ScenarioRequest(BaseModel):
    """Staffing scenario extracted from a user's question."""

    country: str | None = Field(
        default=None,
        description="Country to evaluate, or None for all countries"
    )
    demand_multiplier: float = Field(
        default=1.0,
        gt=0,
        description="1.2 represents a 20% demand increase"
    )
    question_type: str = Field(
        ...,
        description="what_if, explain, or compare"
    )


# 2. Structured memo
class StaffingMemo(BaseModel):
    """Final staffing recommendation returned to the user."""

    summary: str
    recommended_changes: list[str]
    key_numbers: dict[str, float]
    assumptions: list[str]
    risks: list[str]


# 3. Connect to the LLM
def get_model():
    """Load API credentials and initialize the language model."""

    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError(
            "OPENAI_API_KEY is missing. "
            "Configure it in Codespaces secrets."
        )

    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0
    )


# 4. Interpret the question
def understand_question(question, llm):
    """Convert a natural-language question to ScenarioRequest."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", PARSE_SYSTEM_PROMPT),
        ("human", "{question}")
    ])

    chain = prompt | llm.with_structured_output(
        ScenarioRequest,
        method="function_calling"
    )

    return chain.invoke({"question": question})


# 5. Run the actual staffing model

def collect_results(request, planning_model):
    """Compare baseline and alternative model results."""

    if planning_model is None:
        from src.optimization.scenarios import run_scenario
        planning_model = run_scenario

    def get_numbers(multiplier):
        data = planning_model(
            demand_multiplier=multiplier,
            country=request.country
        )

        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                "The staffing model must return a DataFrame."
            )

        required = [
            "country",
            "month",
            "forecast_eligible",
            "agents_active",
            "advertisers_supported",
            "advertisers_waiting",
            "advertisers_expired",
            "incremental_revenue_usd",
            "total_cost_usd",
            "net_value_usd"
        ]

        missing = set(required) - set(data.columns)
        if missing:
            raise ValueError(
                f"Staffing model missing columns: {sorted(missing)}"
            )

        if request.country:
            data = data[
                data["country"].astype(str).str.casefold()
                == request.country.casefold()
            ]

        if data.empty:
            raise ValueError(
                f"No results found for country: {request.country}"
            )

        # Calculate annual totals for additive metrics
        totals = [
            "forecast_eligible",
            "advertisers_supported",
            "advertisers_expired",
            "incremental_revenue_usd",
            "total_cost_usd",
            "net_value_usd"
        ]

        numbers = {
            name: float(data[name].sum())
            for name in totals
        }

        # Sum countries within each month, then average the months
        monthly_totals = data.groupby("month")[
            ["agents_active", "advertisers_waiting"]
        ].sum()

        numbers["average_agents_active"] = float(
            monthly_totals["agents_active"].mean()
        )

        numbers["average_month_end_waiting"] = float(
            monthly_totals["advertisers_waiting"].mean()
        )

        return numbers

    # Compare the baseline and requested scenario
    baseline = get_numbers(1.0)

    if request.demand_multiplier == 1.0:
        alternative = baseline.copy()
    else:
        alternative = get_numbers(request.demand_multiplier)

    difference = {
        name: alternative[name] - baseline[name]
        for name in baseline
    }

    return {
        "baseline": baseline,
        "alternative": alternative,
        "difference": difference
    }

# 6. Generate an explanation grounded in model outputs
def explain_results(question, request, results, llm):
    """Use structured LLM output to explain model calculations."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXPLAIN_SYSTEM_PROMPT),
        (
            "human",
            "Question: {question}\n\n"
            "Scenario settings: {scenario}\n\n"
            "Model calculations: {results}\n\n"
            "Explain the findings, limitations, and "
            "recommended next steps."
        )
    ])

    chain = prompt | llm.with_structured_output(
        StaffingMemo,
        method="function_calling"
    )

    memo = chain.invoke({
        "question": question,
        "scenario": request.model_dump_json(),
        "results": json.dumps(results)
    })

    if memo is None:
        raise RuntimeError(
            "The language model did not return a StaffingMemo."
        )

    # Always use Python-calculated numbers, not LLM estimates.
    memo.key_numbers = {
        f"{section}_{name}": float(value)
        for section, values in results.items()
        for name, value in values.items()
    }

    return memo


# 7. Public interface used by the notebook

def answer_question(
    question: str,
    planning_model=None
) -> StaffingMemo:
    """
    Interpret a staffing question, run the planning model,
    and explain the results using the GenAI assistant.
    """

    # Validate the user's question
    if not isinstance(question, str) or not question.strip():
        raise ValueError(
            "Please enter a staffing question."
        )

    # Initialize the language model
    llm = get_model()

    # Convert the question into a structured scenario request
    request = understand_question(question, llm)

    # Validate the question type
    if request.question_type.strip().lower() not in (
        "what_if",
        "explain",
        "compare",
    ):
        raise ValueError(
            "Unsupported staffing question type."
        )

    # Validate the demand multiplier
    if (
        not math.isfinite(request.demand_multiplier)
        or request.demand_multiplier <= 0
    ):
        raise ValueError(
            "Demand multiplier must be positive and finite."
        )

    # Check for unsupported budget changes
    lower_question = question.lower()

    if "budget" in lower_question and any(
        word in lower_question
        for word in (
            "increase",
            "decrease",
            "rise",
            "grow",
            "drop",
            "reduce",
        )
    ):
        raise ValueError(
            "Changing advertiser budgets is not supported."
        )

    # Check for unsupported single-month demand scenarios
    month_names = (
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    )

    if (
        request.demand_multiplier != 1.0
        and any(
            f"only in {month}" in lower_question
            for month in month_names
        )
    ):
        raise ValueError(
            "Demand changes apply to the full year 2026, "
            "not one selected month."
        )

    # Run the staffing model and collect calculated results
    results = collect_results(
        request,
        planning_model
    )

    # Generate an explanation grounded in the model results
    memo = explain_results(
        question,
        request,
        results,
        llm
    )

    return memo
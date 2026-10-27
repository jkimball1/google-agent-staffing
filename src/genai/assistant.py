"""Member 4 — GenAI planning assistant.

Owner: Enrique Mendez
Branch: feature/genai

Flow:
  1. User asks a staffing question ("What if Germany sign-ups rise 20%?")
  2. LangChain + structured output parses it into a ScenarioRequest
  3. The planning model runs (src.optimization.scenarios.run_scenario)
  4. The LLM explains the numbers in a StaffingMemo

Develop against data/sample/sample_results.csv until outputs/plan_2026.csv exists.
"""

from pydantic import BaseModel, Field


class ScenarioRequest(BaseModel):
    """What the user is asking for, extracted from their question."""
    country: str | None = Field(None, description="Country to change, or None for all")
    demand_multiplier: float = Field(1.0, description="1.2 means sign-ups +20%")
    question_type: str = Field(..., description="e.g. 'what_if', 'explain', 'compare'")


class StaffingMemo(BaseModel):
    """What the assistant returns."""
    summary: str
    recommended_changes: list[str]
    key_numbers: dict[str, float]
    assumptions: list[str]
    risks: list[str]


def answer_question(question: str, planning_model=None) -> StaffingMemo:
    """Answer a natural-language staffing question using the planning model."""
    raise NotImplementedError

_______________________________________________________________________________________________
_______________________________________________________________________________________________
#Member 4 GenAI Planning Assistant, Owner: Enrique Mendez
#Task: Using LangChain, structured outputs, and prompting engineering to explain staffing scenarios

import os
import re
import pandas as pd

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .prompts import PARSE_SYSTEM_PROMPT, EXPLAIN_SYSTEM_PROMPT

#formats from team agreement
class ScenarioRequest(BaseModel):
  """Information extracted form the user's question."""
  
  country: str | None = Field(
    None, description="Country to change, or None for all"
  )
  demand_multiplier: float = Field(
    1.0, ge=0, description="1.2 means sign-ups +20%"
  )
  question_type: str = Field(
    ..., description="what_if, expalin, or compare"
  )

class StaffingMemo(BaseModel):
  """The explanation returned to the user."""

  summary: str
  recommended_changes: list[str]
  key_numbers: dict[str, float]
  assumptions: list[str]
  risks: list[str]

def get_model():
  """Connect to the language model using our API key."""

  load_dotenv()

  if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY is missing from .env")
  return ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0
  )

def understand_question(question, llm):
  """Turn a question into inputs for the staffing model."""

  prompt = ChatPromptTemplate.from_messages([
    ("system", PARSE_SYSTEM_PROMPT),
    ("human", "{question}")
  ])

  chain = prompt | llm.with_structured_output(ScenarioRequest)
  return chain.invoke({"question": question})

def collection_results(request, planning_model):
  """Run the normal plan and the requested alternative."""

  if planning_model is None:
    from src.optimization.scenarios import run_scenario
    planning_model = run_scenario

  def get_numbers(multiplier):
    data = planning_model(
      demand_multiplier=multiplier,
      country=request.country
    )
    if not isinstance(data, pd.DataFrame):
      raise TypeError("The staffing model must return a DataFrame.")

    columns = [
      "country", "forecast_eligible", "agents_active",
      "advertisers_supported", "advertisers_waiting",
      "advertisers_expired", "incremental_revenue_usd",
      "total_cost_usd", "net_value_usd"
    ]
    if not set(columns). issubset(data.columns):
      raise ValueError("The staffing model is missing required columns.")
    if request.country:
      data = data[
        data["country"].astype(str).str.casefold()
        == request.country.casefold()
      ]
    if data.empty:
      raise ValueError("No staffing results found for this country.")

#Adding annual demand, assignments, financial outcomes and expirations
    totals = [
      "forecast_eligible", "advertisers_supported",
      "advertisters_expired", "incremental_revenue_usd",
      "total_cost_usd", "net_value_usd"
    ]

    numbers = {
      name: float(data[name].sum())
      for name in totals
    }

#Staffing with waiting ools that are montly snapshots
    numbers["average_agents_active"] = float(
      data["agents_active"].mean()
    )
    numbers["average_month_end_waiting"] = float(
      data["advertisers_waiting"].mean()
    )
    return numbers
  baseline = get_numbers(1.0)
  alternative = (
    get_numbers(request.demand_multiplier)
    if request.demand_multiplier != 1.0
    else baseline.copy()
  )
  difference = {
    name: alternative[name] - baseline[name]
    for name in baseline
  }
  return {
    "baseline": baseline,
    "alternative": alternative,
    "difference": difference
  }

def explain_results(question, request, results, llm):
  """Use AI to explain calculated staffing results."""
  prompt = ChatPromptTempate.from_messages([
    ("system", EXPLAIN_SYSTEM_PROMPT),
    ("human",
    "Question: {question}\n\n"
    "Scenario settings: {scenario}\n\n"
    "Model calculations: {results}\n\n"
    "Explain the findings and recommended next steps.")
  ])
  chain = prompt | llm.with_structured_output(StaffingMemo)
  memo = chain.invoke({
    "question": question,
    "scenario": request.model_dump_json(),
    "results": json.dumps(results)
  })

#Calculation of numbers from Python Models not calculations generated by the LMM
  memo.key_numbers = {
    f"{section}_{name}": float(value)
    for section, values in results.items()
    for name, value in values.items()
  }
  return memo

def answer_question(question: str, planning_model=None) -> StaffingMemo:
  """Answer a staffing question using the planning model."""
  if not isinstance(question, str) or not question.strip():
    raise ValueError("Please enter a staffing question.")
  llm = get_model()

#Understanding The Users Request
  request = understand_quest(question, llm)
  if request. question_type not in ("what_if", "explain", "compare"):
    raise ValueError("Unsupported type of staffing questions.")
  if request.demand_multiplier < 0:
    raise ValueError("Demand cannot be negative.")

#Scenario Change with Annual Sign-Up, demand, not advertising budgets or individual months
  lower_question = question.lower()
  if (
    "budget" in lower_question
    and any(work in lower_question for work in 
            ("increase", "decrease", "rise", "grow", "drop"))
  ):
    raise ValueError(
      "Chainging advertiser budgets is not supported."
    )
  month_names = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october",
    "november", "december"
  )
  if (
    request.demand_multiplier != 1.0
    and any(f"only in {month}" in lower_question
            for month in month_names)
  ):
    raise ValueError(
      "The scenario model changes demand across 2026, "
      "not only in a selected month."
    )

#Conduct Model Calculations and Then Having AI Explain
results = collect_results(request, planning_model)
return explain_results(question, request, results, llm)

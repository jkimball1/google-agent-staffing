"""Member 4 — GenAI planning assistant.

Owner: TBD
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

#GenAI Planning Assistant for Project 3 Google Ads Staffing
#Role4 Enrique Mendez
#DADS 5250: Generative AI in Practice

#Purpose of file is to identify GenAI as a python package and make the primary functions accessible to teams applications

from .assistant import (
  ScenarioRequest,
  StaffingMemo,
  answer_question,
)

__all__ = [
    "ScenarioRequest",
    "StaffingMemo",
    "answer_question",
]

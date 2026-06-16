"""Pydantic models for the rule IR. Structural shape only — semantic validation
(field existence, scope, expression whitelist) lives in validator.py."""
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field

# A lookup `when` value is either a scalar (enum/string match) or an inclusive
# numeric range [lo, hi].
WhenValue = Union[str, int, list[int]]


class LookupRow(BaseModel):
    when: dict[str, WhenValue]
    value: int


class Case(BaseModel):
    when: str   # safe expression string
    value: str  # safe expression string


class Rule(BaseModel):
    id: str
    description: str = ""
    target: str
    scope: Literal["scalar", "line_item"]
    type: Literal["lookup_table", "conditional_formula"]
    inputs: list[str] = Field(default_factory=list)
    # lookup_table
    match: Optional[list[LookupRow]] = None
    default: Optional[Union[int, str]] = None  # int for lookup; "keep"/expr for conditional
    # conditional_formula
    cases: Optional[list[Case]] = None


class RuleIR(BaseModel):
    version: int = 1
    rules: list[Rule] = Field(default_factory=list)

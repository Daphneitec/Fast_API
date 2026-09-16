from pydantic import BaseModel, Field


class NumberIn(BaseModel):
    number: float | int = Field(description="Value to add to the running sum")


class SumOut(BaseModel):
    sum: float | int


class AddOut(SumOut):
    added: float | int
    node: str


class ResetOut(SumOut):
    node: str


class HealthOut(BaseModel):
    status: str
    node: str
    store: str

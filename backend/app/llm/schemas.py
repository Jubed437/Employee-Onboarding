from pydantic import BaseModel, Field


class ExtractedFields(BaseModel):
    fields: dict[str, str] = Field(default_factory=dict)
    verification_status: str = "PENDING"


class Message(BaseModel):
    subject: str
    body: str


class RiskExplanation(BaseModel):
    explanation: str


class HireAnswer(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)

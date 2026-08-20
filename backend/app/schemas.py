from datetime import datetime

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    created_at: datetime


class ProjectCreate(BaseModel):
    name: str


class ProjectOut(BaseModel):
    id: str
    name: str
    created_at: datetime


class ApiKeyOut(BaseModel):
    id: str
    prefix: str
    created_at: datetime
    revoked_at: datetime | None = None


class ApiKeyCreateOut(ApiKeyOut):
    key: str  # full key, returned only once at creation time


class SpanIn(BaseModel):
    id: str
    parent_id: str | None = None
    type: str  # "chain" | "llm" | "tool" | "retriever"
    name: str
    input: str | None = None
    output: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    tokens: int | None = None
    error: str | None = None


class TraceCreate(BaseModel):
    name: str


class TraceCreateOut(BaseModel):
    id: str


class TraceUpdate(BaseModel):
    status: str | None = None  # "running" | "complete" | "error"
    spans: list[SpanIn] | None = None


class TraceSummaryOut(BaseModel):
    id: str
    name: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    total_tokens: int
    span_count: int


class EvaluationOut(BaseModel):
    evaluator_id: str
    evaluator_name: str
    score: str | None
    reasoning: str | None
    status: str  # "pending" | "done" | "failed"


class TraceDetailOut(BaseModel):
    id: str
    project_id: str
    name: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    total_tokens: int
    spans: list[SpanIn]
    evaluations: list[EvaluationOut]


class EvaluatorCreate(BaseModel):
    name: str
    judge_prompt_template: str
    score_scale: str = "1-5"


class EvaluatorOut(BaseModel):
    id: str
    name: str
    judge_prompt_template: str
    score_scale: str
    active: bool
    created_at: datetime

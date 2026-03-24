from typing import Any

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)
    top_k: int | None = Field(default=None, ge=1, le=10)


class SourceChunk(BaseModel):
    chunk_id: str
    score: float | None = None
    page: int | None = None
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    prompt_context_length: int
    retrieved_pages: list[int]
    source_count: int


class IngestResponse(BaseModel):
    message: str
    filename: str
    total_chunks: int
    pages: int


class RetrieveResponse(BaseModel):
    question: str
    results: list[SourceChunk]


class HealthResponse(BaseModel):
    status: str
    collection_name: str
    indexed_records: int
    ollama_base_url: str
    chat_model: str
    embedding_model: str
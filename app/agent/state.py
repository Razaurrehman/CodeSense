from typing import Any, Optional
from pydantic import BaseModel, Field


class CodeChunk(BaseModel):
    repo_name:   str
    file_path:   str
    start_line:  int
    end_line:    int
    content:     str
    language:    str          = ""
    symbol_name: str          = ""
    chunk_type:  str          = ""   # function | class | module
    score:       float        = 0.0  # cosine similarity


class AgentState(BaseModel):
    # Input
    user_story:   str         = ""
    raw_request:  dict        = Field(default_factory=dict)

    # Routing
    clarification_needed: bool = False
    clarification_question: str = ""

    # Context gathered by tools
    retrieved_context: list[CodeChunk] = Field(default_factory=list)
    rag_results:       list[CodeChunk] = Field(default_factory=list)
    tool_outputs:      dict[str, Any]  = Field(default_factory=dict)

    # LLM reasoning pass
    llm_reasoning: str = ""

    # Final formatted output
    final_output: str = ""

    # Session memory (within one session)
    session_history: list[dict] = Field(default_factory=list)

    # Error tracking
    error: Optional[str] = None

"""
Response models for the Deep Think API.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone


class PipelineMetadata(BaseModel):
    """Metadata about pipeline execution."""
    
    n_paths: int = Field(description="Number of thinking paths generated")
    candidates_generated: int = Field(description="Number of successful candidates")
    candidates_failed: int = Field(default=0, description="Number of failed candidates")
    top_k_used: int = Field(description="Number of top candidates used for refinement")
    execution_time_seconds: Optional[float] = Field(description="Total execution time")
    synthesis_approach: Optional[str] = Field(default=None, description="Approach used for synthesis")
    confidence_level: Optional[str] = Field(default=None, description="Overall confidence in the answer")
    pipeline_stages: List[str] = Field(description="Stages executed in the pipeline")


class DeepThinkResponse(BaseModel):
    """Response model for the Deep Think API endpoint."""
    
    query: str = Field(description="Original query that was processed")
    answer: str = Field(description="Final synthesized answer")
    metadata: PipelineMetadata = Field(description="Pipeline execution metadata")
    
    # Optional detailed results (can be excluded for lighter responses)
    detailed_results: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detailed results from each pipeline stage"
    )
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Response generation timestamp"
    )
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "query": "Why does the sum of 1/n² converge?",
                "answer": "The sum ∑(1/n²) converges to π²/6 ≈ 1.645 because...",
                "metadata": {
                    "n_paths": 8,
                    "candidates_generated": 8,
                    "candidates_failed": 0,
                    "top_k_used": 3,
                    "execution_time_seconds": 12.5,
                    "synthesis_approach": "Combined insights from mathematical and analytical approaches",
                    "confidence_level": "high",
                    "pipeline_stages": ["planning", "thinking", "critique", "refinement"]
                },
                "timestamp": "2025-08-01T12:34:56.789Z"
            }
        }
    )


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""
    
    status: str = Field(description="Overall health status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Health check timestamp"
    )
    components: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="Component-level health information"
    )
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-08-01T12:34:56.789Z",
                "components": {
                    "gemini_client": {
                        "status": "healthy",
                        "details": {
                            "model_name": "gemini-2.5-pro",
                            "timeout": 30
                        }
                    },
                    "agents": {
                        "planner": {"status": "healthy"},
                        "critic": {"status": "healthy"},
                        "refiner": {"status": "healthy"}
                    }
                }
            }
        }
    )


class ErrorResponse(BaseModel):
    """Response model for API errors."""
    
    error: str = Field(description="Error type or category")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Error timestamp"
    )
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Query is required and cannot be empty",
                "details": {
                    "field": "query",
                    "provided_value": ""
                },
                "timestamp": "2025-08-01T12:34:56.789Z"
            }
        }
    )
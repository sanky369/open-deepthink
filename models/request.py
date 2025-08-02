"""
Request models for the Deep Think API.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
import structlog

logger = structlog.get_logger()


class DeepThinkRequest(BaseModel):
    """Request model for the Deep Think API endpoint."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The question or problem to analyze using Deep Think"
    )
    
    n_paths: Optional[int] = Field(
        default=8,
        ge=1,
        le=32,
        description="Number of parallel thinking paths to generate (1-32)"
    )
    
    max_iterations: Optional[int] = Field(
        default=1,
        ge=1,
        le=5,
        description="Maximum iterations of refinement (currently unused, reserved for future)"
    )
    
    top_k: Optional[int] = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of top candidates to use for final refinement (1-10)"
    )
    
    timeout: Optional[int] = Field(
        default=300,
        ge=30,
        le=960,
        description="Pipeline timeout in seconds (30-960)"
    )
    
    @field_validator("top_k")
    @classmethod
    def validate_top_k_against_n_paths(cls, v, info):
        """Ensure top_k doesn't exceed n_paths."""
        n_paths = info.data.get("n_paths", 8) if info.data else 8
        if v > n_paths:
            logger.warning(
                "top_k_adjusted",
                requested_top_k=v,
                n_paths=n_paths,
                adjusted_top_k=n_paths
            )
            return n_paths
        return v
    
    @field_validator("query")
    @classmethod
    def validate_query_content(cls, v):
        """Validate query content."""
        if not v.strip():
            raise ValueError("Query cannot be empty or only whitespace")
        
        # Check for potentially problematic content
        query_lower = v.lower()
        if len(query_lower) < 5:
            logger.warning("very_short_query", query_length=len(v))
        
        return v.strip()
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "query": "Explain why the sum of the reciprocals of squares converges to π²/6",
                "n_paths": 8,
                "max_iterations": 1,
                "top_k": 3,
                "timeout": 120
            }
        }
    )


class HealthCheckRequest(BaseModel):
    """Request model for health check endpoint."""
    
    include_details: Optional[bool] = Field(
        default=False,
        description="Whether to include detailed component information"
    )
    
    check_api: Optional[bool] = Field(
        default=True,
        description="Whether to check external API connectivity"
    )
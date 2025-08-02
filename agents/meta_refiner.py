"""
Meta-Refiner agent for final high-level synthesis and insight generation.
"""
import json
from typing import Dict, Any
import structlog
from .base import BaseAgent

logger = structlog.get_logger()


# JSON Schema for Meta-Refiner output
META_REFINER_SCHEMA = {
    "type": "object",
    "properties": {
        "meta_refined_answer": {"type": "string"},
        "synthesis_type": {"type": "string", "enum": ["enhancement", "confirmation", "reframing", "consolidation"]},
        "key_insights_added": {
            "type": "array",
            "items": {"type": "string"}
        },
        "deeper_connections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "connection_type": {"type": "string"},
                    "description": {"type": "string"},
                    "significance": {"type": "string", "enum": ["low", "medium", "high"]}
                },
                "required": ["connection_type", "description", "significance"]
            }
        },
        "potential_contradictions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "contradiction": {"type": "string"},
                    "resolution": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]}
                },
                "required": ["contradiction", "resolution"]
            }
        },
        "second_order_implications": {
            "type": "array",
            "items": {"type": "string"}
        },
        "elegance_score": {"type": "number"},
        "intellectual_depth": {"type": "string", "enum": ["surface", "moderate", "deep", "profound"]},
        "meta_confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "refinement_rationale": {"type": "string"}
    },
    "required": ["meta_refined_answer", "synthesis_type", "elegance_score", "intellectual_depth", "refinement_rationale"]
}


class MetaRefinerAgent(BaseAgent):
    """
    Agent responsible for performing final meta-level refinement and synthesis.
    Looks for deeper insights, elegant reformulations, and second-order implications.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the Meta-Refiner agent."""
        super().__init__(*args, **kwargs)
        
    async def execute(
        self,
        input_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute meta-refinement logic to elevate the refined solution.
        
        Args:
            input_data: Must contain 'query' and 'refined_solution'
            **kwargs: Additional execution parameters
            
        Returns:
            Dict containing meta-refined answer and insights
        """
        query = input_data.get("query")
        refined_solution = input_data.get("refined_solution")
        
        if not query or not refined_solution:
            raise ValueError("Both query and refined_solution are required for meta-refinement")
        
        logger.info(
            "meta_refiner_execution_start",
            agent_id=self.agent_id,
            query_length=len(query),
            solution_length=len(refined_solution)
        )
        
        try:
            # Format the prompt with query and refined solution
            prompt = self._format_prompt({
                "query": query,
                "refined_solution": refined_solution
            })
            
            # Call LLM with higher temperature for creative meta-synthesis
            response = await self._call_llm(
                prompt=prompt,
                temperature=0.8,  # Higher temperature for creative insights
                max_tokens=6144,
                response_mime_type="application/json",
                response_schema=META_REFINER_SCHEMA
            )
            
            # Parse the JSON response with robust error handling
            fallback = self._create_fallback_meta_refinement(query, refined_solution)
            meta_result = self._parse_json_with_recovery(response, fallback)
            
            # Validate and enhance the meta-refinement
            meta_result = self._validate_and_enhance_meta_refinement(meta_result, refined_solution)
            
            # Add metadata
            meta_result["meta_refiner_id"] = self.agent_id
            meta_result["original_solution_length"] = len(refined_solution)
            meta_result["meta_refined_length"] = len(meta_result.get("meta_refined_answer", ""))
            
            logger.info(
                "meta_refiner_execution_complete",
                agent_id=self.agent_id,
                synthesis_type=meta_result.get("synthesis_type"),
                elegance_score=meta_result.get("elegance_score"),
                intellectual_depth=meta_result.get("intellectual_depth"),
                insights_count=len(meta_result.get("key_insights_added", []))
            )
            
            return meta_result
            
        except Exception as e:
            logger.error(
                "meta_refiner_execution_error",
                agent_id=self.agent_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def _validate_and_enhance_meta_refinement(
        self,
        meta_result: Dict[str, Any],
        original_solution: str
    ) -> Dict[str, Any]:
        """
        Validate the meta-refinement structure and add defaults for missing fields.
        
        Args:
            meta_result: Raw meta-refinement from LLM
            original_solution: Original refined solution
            
        Returns:
            Validated and enhanced meta-refinement
        """
        # Ensure required fields exist with defaults
        enhanced_result = {
            "meta_refined_answer": meta_result.get("meta_refined_answer", original_solution),
            "synthesis_type": meta_result.get("synthesis_type", "confirmation"),
            "key_insights_added": meta_result.get("key_insights_added", []),
            "deeper_connections": meta_result.get("deeper_connections", []),
            "potential_contradictions": meta_result.get("potential_contradictions", []),
            "second_order_implications": meta_result.get("second_order_implications", []),
            "elegance_score": self._normalize_score(meta_result.get("elegance_score"), 1, 10, 7),
            "intellectual_depth": meta_result.get("intellectual_depth", "moderate"),
            "meta_confidence": meta_result.get("meta_confidence", "medium"),
            "refinement_rationale": meta_result.get(
                "refinement_rationale",
                "Meta-refinement provides additional perspective on the solution"
            )
        }
        
        # Validate deeper connections structure
        validated_connections = []
        for connection in enhanced_result["deeper_connections"]:
            if isinstance(connection, dict):
                validated_connections.append({
                    "connection_type": connection.get("connection_type", "conceptual"),
                    "description": connection.get("description", "Additional connection identified"),
                    "significance": connection.get("significance", "medium")
                })
        enhanced_result["deeper_connections"] = validated_connections
        
        # Validate contradictions structure
        validated_contradictions = []
        for contradiction in enhanced_result["potential_contradictions"]:
            if isinstance(contradiction, dict):
                validated_contradictions.append({
                    "contradiction": contradiction.get("contradiction", "Potential inconsistency identified"),
                    "resolution": contradiction.get("resolution", "Further analysis recommended"),
                    "confidence": contradiction.get("confidence", "medium")
                })
        enhanced_result["potential_contradictions"] = validated_contradictions
        
        logger.debug(
            "meta_refinement_validated",
            agent_id=self.agent_id,
            synthesis_type=enhanced_result["synthesis_type"],
            elegance_score=enhanced_result["elegance_score"],
            connections_count=len(validated_connections),
            contradictions_count=len(validated_contradictions)
        )
        
        return enhanced_result
    
    def _normalize_score(self, score: Any, min_val: int, max_val: int, default: int) -> int:
        """
        Normalize score to a valid integer within range.
        
        Args:
            score: Raw score value
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            default: Default value if invalid
            
        Returns:
            Normalized score
        """
        try:
            if isinstance(score, (int, float)):
                return max(min_val, min(max_val, int(score)))
            elif isinstance(score, str):
                return max(min_val, min(max_val, int(float(score))))
        except (ValueError, TypeError):
            pass
        
        return default
    
    def _create_fallback_meta_refinement(
        self,
        query: str,
        refined_solution: str
    ) -> Dict[str, Any]:
        """
        Create a fallback meta-refinement when JSON parsing fails.
        
        Args:
            query: Original query
            refined_solution: Refined solution
            
        Returns:
            Basic meta-refinement structure
        """
        logger.warning(
            "using_fallback_meta_refinement",
            agent_id=self.agent_id,
            query_preview=query[:100],
            solution_preview=refined_solution[:100]
        )
        
        return {
            "meta_refined_answer": refined_solution,
            "synthesis_type": "confirmation",
            "key_insights_added": ["Meta-refinement process completed with fallback approach"],
            "deeper_connections": [],
            "potential_contradictions": [],
            "second_order_implications": ["Further analysis may reveal additional insights"],
            "elegance_score": 7,
            "intellectual_depth": "moderate",
            "meta_confidence": "medium",
            "refinement_rationale": "Fallback meta-refinement - detailed analysis unavailable"
        }
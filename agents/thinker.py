"""
Thinker agent for generating individual reasoning paths.
"""
import json
from typing import Dict, Any
import structlog
from .base import BaseAgent, THINKER_SCHEMA

logger = structlog.get_logger()


class ThinkerAgent(BaseAgent):
    """
    Agent responsible for generating individual reasoning paths.
    Each Thinker works in parallel to create diverse approaches to the same problem.
    """
    
    def __init__(self, *args, seed: int = 0, **kwargs):
        """
        Initialize the Thinker agent.
        
        Args:
            seed: Unique seed for this thinker to encourage diversity
            *args, **kwargs: Base agent arguments
        """
        super().__init__(*args, **kwargs)
        self.seed = seed
        
    async def execute(
        self,
        input_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute thinking logic to generate a reasoning path.
        
        Args:
            input_data: Must contain 'plan' with task details
            **kwargs: Additional execution parameters
            
        Returns:
            Dict containing reasoning path and preliminary answer
        """
        plan = input_data.get("plan")
        if not plan:
            raise ValueError("Plan is required for thinking")
        
        step_budget = kwargs.get("step_budget", plan.get("thinking_budget", 10))
        
        logger.info(
            "thinker_execution_start",
            agent_id=self.agent_id,
            seed=self.seed,
            task_preview=plan.get("task", "")[:100],
            step_budget=step_budget
        )
        
        try:
            # Format the prompt with plan details
            prompt = self._format_prompt({
                "agent_id": self.seed,
                "task": plan.get("task", ""),
                "reasoning_type": plan.get("reasoning_type", "analytical"),
                "key_aspects": ", ".join(plan.get("key_aspects", [])),
                "domain_hints": ", ".join(plan.get("domain_hints", [])),
                "complexity_level": plan.get("complexity_level", "moderate"),
                "success_criteria": plan.get("success_criteria", ""),
                "thinking_budget": step_budget
            })
            
            # Call LLM with higher temperature for diversity and structured output
            response = await self._call_llm(
                prompt=prompt,
                temperature=1.1,  # Higher temperature for diverse thinking
                max_tokens=4096,  # Reduced to prevent truncation issues
                response_mime_type="application/json",
                response_schema=THINKER_SCHEMA
            )
            
            # Parse the JSON response with robust error handling
            fallback = self._create_fallback_result(response, plan)
            result = self._parse_json_with_recovery(response, fallback)
            
            # Validate and enhance the result
            result = self._validate_and_enhance_result(result, plan)
            
            # Add metadata
            result["agent_id"] = self.seed
            result["thinker_agent_id"] = self.agent_id
            
            logger.info(
                "thinker_execution_complete",
                agent_id=self.agent_id,
                seed=self.seed,
                thoughts_count=len(result.get("thoughts", [])),
                confidence=result.get("confidence"),
                approach=result.get("approach", "")[:50]
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "thinker_execution_error",
                agent_id=self.agent_id,
                seed=self.seed,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def _validate_and_enhance_result(
        self,
        result: Dict[str, Any],
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the result structure and add defaults for missing fields.
        
        Args:
            result: Raw result from LLM
            plan: Original plan details
            
        Returns:
            Validated and enhanced result
        """
        enhanced_result = {
            "agent_id": self.seed,
            "approach": result.get("approach", f"Thinker {self.seed} approach"),
            "thoughts": result.get("thoughts", ["Analyzing the problem..."]),
            "answer": result.get("answer", "Unable to generate answer"),
            "confidence": self._normalize_confidence(result.get("confidence")),
            "reasoning_quality": result.get(
                "reasoning_quality",
                "Standard reasoning process"
            ),
            "potential_issues": result.get("potential_issues", [])
        }
        
        # Ensure thoughts is a list
        if isinstance(enhanced_result["thoughts"], str):
            enhanced_result["thoughts"] = [enhanced_result["thoughts"]]
        
        # Ensure potential_issues is a list
        if isinstance(enhanced_result["potential_issues"], str):
            enhanced_result["potential_issues"] = [enhanced_result["potential_issues"]]
        
        # Limit thoughts to reasonable length
        max_thoughts = plan.get("thinking_budget", 10) + 2
        if len(enhanced_result["thoughts"]) > max_thoughts:
            enhanced_result["thoughts"] = enhanced_result["thoughts"][:max_thoughts]
        
        logger.debug(
            "result_validated",
            agent_id=self.agent_id,
            seed=self.seed,
            enhanced_result_keys=list(enhanced_result.keys())
        )
        
        return enhanced_result
    
    def _normalize_confidence(self, confidence: Any) -> str:
        """
        Normalize confidence to a standard value.
        
        Args:
            confidence: Raw confidence value
            
        Returns:
            Normalized confidence string
        """
        if isinstance(confidence, str):
            conf_lower = confidence.lower()
            if "high" in conf_lower:
                return "high"
            elif "low" in conf_lower:
                return "low"
            else:
                return "medium"
        
        if isinstance(confidence, (int, float)):
            if confidence >= 0.8:
                return "high"
            elif confidence <= 0.4:
                return "low"
            else:
                return "medium"
        
        return "medium"
    
    
    def _create_fallback_result(
        self,
        raw_response: str,
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a fallback result when JSON parsing fails.
        
        Args:
            raw_response: Raw LLM response
            plan: Original plan
            
        Returns:
            Basic result structure
        """
        logger.warning(
            "using_fallback_result",
            agent_id=self.agent_id,
            seed=self.seed,
            response_preview=raw_response[:200]
        )
        
        # Try to extract some content from the raw response
        lines = raw_response.split('\n')
        answer_lines = [line for line in lines if line.strip() and not line.strip().startswith('{') and not line.strip().startswith('"')]
        
        # Extract any potential answer content from malformed JSON
        potential_answer = self._extract_answer_from_malformed_json(raw_response)
        
        return {
            "agent_id": self.seed,
            "approach": f"Fallback approach for Thinker {self.seed}",
            "thoughts": answer_lines[:5] if answer_lines else ["Analyzing..."],
            "answer": potential_answer or (answer_lines[-1] if answer_lines else "Unable to parse response"),
            "confidence": "low",
            "reasoning_quality": "Fallback parsing - may be incomplete",
            "potential_issues": ["JSON parsing failed", "May contain formatting issues"]
        }
    
    def _extract_answer_from_malformed_json(self, response: str) -> str:
        """
        Try to extract answer content from malformed JSON response.
        
        Args:
            response: Raw response with malformed JSON
            
        Returns:
            Extracted answer or None
        """
        import re
        
        # Look for answer field in the malformed JSON
        answer_patterns = [
            r'"answer":\s*"([^"]*)"',
            r'"answer":\s*"([^"\\]*(\\.[^"\\]*)*)',  # Handle escaped quotes
            r'answer.*?[:\s]+(.*?)(?:\n|$)',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                answer = match.group(1).strip()
                if answer and len(answer) > 10:  # Must be substantial
                    return answer
        
        return None
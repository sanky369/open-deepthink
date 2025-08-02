"""
Planner agent for decomposing queries and setting thinking parameters.
"""
import json
from typing import Dict, Any
import structlog
from .base import BaseAgent, PLANNER_SCHEMA

logger = structlog.get_logger()


class PlannerAgent(BaseAgent):
    """
    Agent responsible for analyzing queries and creating structured plans
    for the parallel thinking stage.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the Planner agent."""
        super().__init__(*args, **kwargs)
        
    async def execute(
        self,
        input_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute planning logic to decompose the query.
        
        Args:
            input_data: Must contain 'query' and optionally 'n_paths'
            **kwargs: Additional execution parameters
            
        Returns:
            Dict containing plan details and execution parameters
        """
        query = input_data.get("query")
        if not query:
            raise ValueError("Query is required for planning")
        
        n_paths = input_data.get("n_paths", 8)
        
        logger.info(
            "planner_execution_start",
            agent_id=self.agent_id,
            query_length=len(query),
            n_paths=n_paths
        )
        
        try:
            # Format the prompt with query
            prompt = self._format_prompt({
                "query": query
            })
            
            # Call LLM with lower temperature for more consistent planning
            response = await self._call_llm(
                prompt=prompt,
                temperature=0.3,  # Lower temperature for planning consistency
                max_tokens=4096,
                response_mime_type="application/json",
                response_schema=PLANNER_SCHEMA
            )
            
            # Parse the JSON response with robust error handling
            fallback = self._create_fallback_plan(query)
            plan = self._parse_json_with_recovery(response, fallback)
            
            # Validate and enhance the plan
            plan = self._validate_and_enhance_plan(plan, query)
            
            result = {
                "plan": plan,
                "n_paths": n_paths,
                "original_query": query,
                "planner_id": self.agent_id
            }
            
            logger.info(
                "planner_execution_complete",
                agent_id=self.agent_id,
                plan_complexity=plan.get("complexity_level"),
                thinking_budget=plan.get("thinking_budget"),
                n_paths=n_paths
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "planner_execution_error",
                agent_id=self.agent_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def _validate_and_enhance_plan(
        self,
        plan: Dict[str, Any],
        original_query: str
    ) -> Dict[str, Any]:
        """
        Validate the plan structure and add defaults for missing fields.
        
        Args:
            plan: Raw plan from LLM
            original_query: Original user query
            
        Returns:
            Validated and enhanced plan
        """
        # Ensure required fields exist
        enhanced_plan = {
            "task": plan.get("task", original_query),
            "reasoning_type": plan.get("reasoning_type", "analytical"),
            "key_aspects": plan.get("key_aspects", ["main_problem"]),
            "domain_hints": plan.get("domain_hints", ["general"]),
            "complexity_level": plan.get("complexity_level", "moderate"),
            "thinking_budget": self._normalize_thinking_budget(
                plan.get("thinking_budget")
            ),
            "success_criteria": plan.get(
                "success_criteria",
                "Clear, accurate, and well-reasoned answer"
            )
        }
        
        # Ensure key_aspects is a list
        if isinstance(enhanced_plan["key_aspects"], str):
            enhanced_plan["key_aspects"] = [enhanced_plan["key_aspects"]]
        
        # Ensure domain_hints is a list
        if isinstance(enhanced_plan["domain_hints"], str):
            enhanced_plan["domain_hints"] = [enhanced_plan["domain_hints"]]
        
        logger.debug(
            "plan_validated",
            agent_id=self.agent_id,
            enhanced_plan=enhanced_plan
        )
        
        return enhanced_plan
    
    def _normalize_thinking_budget(self, budget: Any) -> int:
        """
        Normalize thinking budget to a reasonable integer value.
        
        Args:
            budget: Raw budget value from plan
            
        Returns:
            Normalized integer budget (5-15)
        """
        if isinstance(budget, str):
            try:
                # Extract number from string like "10 steps" or "moderate (8-12)"
                import re
                numbers = re.findall(r'\d+', budget)
                if numbers:
                    budget = int(numbers[0])
                else:
                    budget = 10  # Default
            except:
                budget = 10
        
        if isinstance(budget, int):
            # Clamp to reasonable range
            return max(5, min(15, budget))
        
        # Default budget
        return 10
    
    def _create_fallback_plan(self, query: str) -> Dict[str, Any]:
        """
        Create a fallback plan when JSON parsing fails.
        
        Args:
            query: Original user query
            
        Returns:
            Basic plan structure
        """
        logger.warning(
            "using_fallback_plan",
            agent_id=self.agent_id,
            query_preview=query[:100]
        )
        
        return {
            "task": f"Analyze and answer: {query}",
            "reasoning_type": "analytical",
            "key_aspects": ["main_problem", "solution_approach"],
            "domain_hints": ["general"],
            "complexity_level": "moderate",
            "thinking_budget": 10,
            "success_criteria": "Clear and accurate answer"
        }
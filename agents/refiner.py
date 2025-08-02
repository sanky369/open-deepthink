"""
Refiner agent for synthesizing the best elements from multiple reasoning paths.
"""
import json
from typing import Dict, Any, List
import structlog
from .base import BaseAgent, REFINER_SCHEMA

logger = structlog.get_logger()


class RefinerAgent(BaseAgent):
    """
    Agent responsible for synthesizing the best elements from top-rated
    candidates into a final, polished answer.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the Refiner agent."""
        super().__init__(*args, **kwargs)
        
    async def execute(
        self,
        input_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute refinement logic to synthesize the final answer.
        
        Args:
            input_data: Must contain 'critique' and optionally 'candidates'
            **kwargs: Additional execution parameters (top_k)
            
        Returns:
            Dict containing final answer and synthesis metadata
        """
        critique = input_data.get("critique")
        if not critique:
            raise ValueError("Critique is required for refinement")
        
        candidates = input_data.get("candidates", [])
        top_k = kwargs.get("top_k", 3)
        
        logger.info(
            "refiner_execution_start",
            agent_id=self.agent_id,
            critique_evaluations=len(critique.get("evaluations", [])),
            top_k=top_k
        )
        
        try:
            # Get top candidates based on ranking
            top_candidates = self._get_top_candidates(critique, candidates, top_k)
            
            # Format data for the prompt
            critique_text = self._format_critique(critique)
            top_candidates_text = self._format_top_candidates(top_candidates)
            
            # Format the prompt
            prompt = self._format_prompt({
                "critique": critique_text,
                "top_candidates": top_candidates_text,
                "top_k": top_k
            })
            
            # Call LLM with low temperature for deterministic synthesis
            response = await self._call_llm(
                prompt=prompt,
                temperature=0.2,  # Low temperature for consistent synthesis
                max_tokens=4096,
                response_mime_type="application/json",
                response_schema=REFINER_SCHEMA
            )
            
            # Parse the JSON response with robust error handling
            fallback = self._create_fallback_result(top_candidates)
            result = self._parse_json_with_recovery(response, fallback)
            
            # Validate and enhance the result
            result = self._validate_and_enhance_result(result, top_candidates)
            
            # Add metadata
            result["refiner_id"] = self.agent_id
            result["candidates_synthesized"] = len(top_candidates)
            result["top_k_used"] = top_k
            
            logger.info(
                "refiner_execution_complete",
                agent_id=self.agent_id,
                final_answer_length=len(result.get("final_answer", "")),
                confidence=result.get("confidence_level"),
                sources_used=len(result.get("sources_used", []))
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "refiner_execution_error",
                agent_id=self.agent_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def _get_top_candidates(
        self,
        critique: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Get the top-k candidates based on critique ranking.
        
        Args:
            critique: Critique results with rankings
            candidates: Original candidate solutions
            top_k: Number of top candidates to include
            
        Returns:
            List of top candidates with their critique data
        """
        ranking = critique.get("ranking", [])
        evaluations = critique.get("evaluations", [])
        
        # Create a mapping of agent_id to candidate and evaluation
        candidate_map = {c.get("agent_id", i): c for i, c in enumerate(candidates)}
        evaluation_map = {e.get("agent_id"): e for e in evaluations}
        
        top_candidates = []
        for rank_info in ranking[:top_k]:
            agent_id = rank_info.get("agent_id")
            
            if agent_id in candidate_map:
                candidate = candidate_map[agent_id].copy()
                candidate["critique"] = evaluation_map.get(agent_id, {})
                candidate["rank"] = rank_info.get("rank")
                candidate["total_score"] = rank_info.get("total_score")
                top_candidates.append(candidate)
        
        logger.debug(
            "top_candidates_selected",
            agent_id=self.agent_id,
            selected_count=len(top_candidates),
            agent_ids=[c.get("agent_id") for c in top_candidates]
        )
        
        return top_candidates
    
    def _format_critique(self, critique: Dict[str, Any]) -> str:
        """
        Format critique data for the prompt.
        
        Args:
            critique: Critique results
            
        Returns:
            Formatted critique text
        """
        lines = []
        
        # Overall assessment
        lines.append(f"Overall Assessment: {critique.get('overall_assessment', 'N/A')}")
        lines.append("")
        
        # Rankings
        lines.append("Rankings:")
        for rank_info in critique.get("ranking", []):
            lines.append(
                f"  Rank {rank_info.get('rank')}: Agent {rank_info.get('agent_id')} "
                f"(Score: {rank_info.get('total_score')}/50) - {rank_info.get('rationale')}"
            )
        lines.append("")
        
        # Improvement suggestions
        suggestions = critique.get("improvement_suggestions", [])
        if suggestions:
            lines.append("Improvement Suggestions:")
            for suggestion in suggestions:
                lines.append(f"  - {suggestion}")
        
        return "\n".join(lines)
    
    def _format_top_candidates(self, top_candidates: List[Dict[str, Any]]) -> str:
        """
        Format top candidates data for the prompt.
        
        Args:
            top_candidates: List of top-rated candidates
            
        Returns:
            Formatted candidates text
        """
        lines = []
        
        for candidate in top_candidates:
            agent_id = candidate.get("agent_id", "unknown")
            rank = candidate.get("rank", "?")
            total_score = candidate.get("total_score", 0)
            
            lines.append(f"**Candidate {agent_id} (Rank {rank}, Score: {total_score}/50):**")
            
            # Approach and answer
            lines.append(f"Approach: {candidate.get('approach', 'N/A')}")
            lines.append(f"Answer: {candidate.get('answer', 'N/A')}")
            lines.append(f"Confidence: {candidate.get('confidence', 'N/A')}")
            
            # Critique feedback
            critique = candidate.get("critique", {})
            scores = critique.get("scores", {})
            if scores:
                score_text = ", ".join([f"{k}: {v}" for k, v in scores.items()])
                lines.append(f"Detailed Scores: {score_text}")
            
            strengths = critique.get("strengths", [])
            if strengths:
                lines.append(f"Strengths: {', '.join(strengths)}")
            
            weaknesses = critique.get("weaknesses", [])
            if weaknesses:
                lines.append(f"Weaknesses: {', '.join(weaknesses)}")
            
            feedback = critique.get("feedback", "")
            if feedback:
                lines.append(f"Feedback: {feedback}")
            
            lines.append("")  # Blank line between candidates
        
        return "\n".join(lines)
    
    def _validate_and_enhance_result(
        self,
        result: Dict[str, Any],
        top_candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate the result structure and add defaults for missing fields.
        
        Args:
            result: Raw result from LLM
            top_candidates: Top candidates used for synthesis
            
        Returns:
            Validated and enhanced result
        """
        # Extract final answer, ensuring it's a string
        raw_final_answer = result.get("final_answer")
        
        if isinstance(raw_final_answer, str):
            final_answer = raw_final_answer
        elif raw_final_answer is None:
            final_answer = self._create_simple_synthesis(top_candidates)
        else:
            # For any other type (dict, list, etc.), use JSON serialization for clean conversion
            import json
            try:
                final_answer = json.dumps(raw_final_answer, indent=2)
            except:
                # Fallback to str() if JSON serialization fails
                final_answer = str(raw_final_answer)
        
        enhanced_result = {
            "final_answer": final_answer,
            "synthesis_approach": result.get(
                "synthesis_approach",
                "Combined insights from top-rated candidates"
            ),
            "sources_used": self._validate_sources_used(
                result.get("sources_used", []),
                top_candidates
            ),
            "improvements_made": result.get(
                "improvements_made",
                ["Synthesized multiple viewpoints"]
            ),
            "confidence_level": self._normalize_confidence(
                result.get("confidence_level")
            ),
            "reasoning_quality": result.get(
                "reasoning_quality",
                "Standard synthesis quality"
            ),
            "completeness": result.get(
                "completeness",
                "Addresses main aspects of the query"
            )
        }
        
        logger.debug(
            "result_validated",
            agent_id=self.agent_id,
            final_answer_length=len(enhanced_result["final_answer"]),
            sources_count=len(enhanced_result["sources_used"])
        )
        
        return enhanced_result
    
    def _validate_sources_used(
        self,
        sources: List[Dict[str, Any]],
        top_candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate and normalize sources used information.
        
        Args:
            sources: Raw sources from LLM
            top_candidates: Available candidates
            
        Returns:
            Validated sources list
        """
        if not sources:
            # Create default sources from top candidates
            return [
                {
                    "agent_id": candidate.get("agent_id", "unknown"),
                    "elements_borrowed": ["reasoning approach"],
                    "contribution_weight": "medium"
                }
                for candidate in top_candidates[:2]  # Use top 2 as default
            ]
        
        validated_sources = []
        for source in sources:
            validated_source = {
                "agent_id": source.get("agent_id", "unknown"),
                "elements_borrowed": source.get("elements_borrowed", ["general reasoning"]),
                "contribution_weight": self._normalize_weight(
                    source.get("contribution_weight")
                )
            }
            
            # Ensure elements_borrowed is a list
            if isinstance(validated_source["elements_borrowed"], str):
                validated_source["elements_borrowed"] = [validated_source["elements_borrowed"]]
            
            validated_sources.append(validated_source)
        
        return validated_sources
    
    def _normalize_confidence(self, confidence: Any) -> str:
        """Normalize confidence to standard values."""
        if isinstance(confidence, str):
            conf_lower = confidence.lower()
            if "high" in conf_lower:
                return "high"
            elif "low" in conf_lower:
                return "low"
            else:
                return "medium"
        return "medium"
    
    def _normalize_weight(self, weight: Any) -> str:
        """Normalize contribution weight to standard values."""
        if isinstance(weight, str):
            weight_lower = weight.lower()
            if "high" in weight_lower:
                return "high"
            elif "low" in weight_lower:
                return "low"
            else:
                return "medium"
        return "medium"
    
    def _create_simple_synthesis(self, top_candidates: List[Dict[str, Any]]) -> str:
        """
        Create a simple synthesis when LLM synthesis fails.
        
        Args:
            top_candidates: Top candidates to synthesize
            
        Returns:
            Basic synthesized answer
        """
        if not top_candidates:
            return "Unable to synthesize answer from candidates."
        
        # Use the top candidate as base and mention others
        top_answer = top_candidates[0].get("answer", "No answer available")
        
        if len(top_candidates) > 1:
            synthesis = f"{top_answer}\n\n"
            synthesis += "Additional perspectives from other candidates support this conclusion "
            synthesis += f"with {len(top_candidates)} independent reasoning paths leading to similar results."
        else:
            synthesis = top_answer
        
        return synthesis
    
    def _create_fallback_result(
        self,
        top_candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a fallback result when JSON parsing fails.
        
        Args:
            top_candidates: Top candidates for synthesis
            
        Returns:
            Basic result structure
        """
        logger.warning(
            "using_fallback_synthesis",
            agent_id=self.agent_id,
            candidates_count=len(top_candidates)
        )
        
        return {
            "final_answer": self._create_simple_synthesis(top_candidates),
            "synthesis_approach": "Fallback synthesis - detailed analysis unavailable",
            "sources_used": self._validate_sources_used([], top_candidates),
            "improvements_made": ["Basic synthesis attempted"],
            "confidence_level": "medium",
            "reasoning_quality": "Fallback quality - may need review",
            "completeness": "Basic completeness achieved"
        }
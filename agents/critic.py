"""
Critic agent for evaluating and scoring reasoning paths.
"""
import json
from typing import Dict, Any, List
import structlog
from .base import BaseAgent, CRITIC_SCHEMA

logger = structlog.get_logger()


class CriticAgent(BaseAgent):
    """
    Agent responsible for evaluating multiple reasoning paths
    and providing scores and feedback for each candidate.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the Critic agent."""
        super().__init__(*args, **kwargs)
        
    async def execute(
        self,
        input_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute critique logic to evaluate candidate solutions.
        
        Args:
            input_data: Must contain 'candidates' list
            **kwargs: Additional execution parameters
            
        Returns:
            Dict containing evaluations, rankings, and feedback
        """
        candidates = input_data.get("candidates", [])
        if not candidates:
            raise ValueError("Candidates are required for critique")
        
        logger.info(
            "critic_execution_start",
            agent_id=self.agent_id,
            candidates_count=len(candidates)
        )
        
        try:
            # Format candidates for the prompt
            candidates_text = self._format_candidates(candidates)
            
            # Format the prompt
            prompt = self._format_prompt({
                "candidates": candidates_text
            })
            
            # Call LLM with moderate temperature for balanced evaluation
            response = await self._call_llm(
                prompt=prompt,
                temperature=0.5,  # Moderate temperature for balanced critique
                max_tokens=4096,
                response_mime_type="application/json",
                response_schema=CRITIC_SCHEMA
            )
            
            # Parse the JSON response with robust error handling
            fallback = self._create_fallback_critique(candidates)
            critique = self._parse_json_with_recovery(response, fallback)
            
            # Validate and enhance the critique
            critique = self._validate_and_enhance_critique(critique, candidates)
            
            # Add metadata
            critique["critic_id"] = self.agent_id
            critique["candidates_evaluated"] = len(candidates)
            
            logger.info(
                "critic_execution_complete",
                agent_id=self.agent_id,
                evaluations_count=len(critique.get("evaluations", [])),
                top_score=max([e.get("total_score", 0) for e in critique.get("evaluations", [])], default=0)
            )
            
            return critique
            
        except Exception as e:
            logger.error(
                "critic_execution_error",
                agent_id=self.agent_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def _format_candidates(self, candidates: List[Dict[str, Any]]) -> str:
        """
        Format candidates into a readable text format for the prompt.
        
        Args:
            candidates: List of candidate solutions
            
        Returns:
            Formatted candidates text
        """
        formatted_parts = []
        
        for i, candidate in enumerate(candidates):
            agent_id = candidate.get("agent_id", f"unknown_{i}")
            approach = candidate.get("approach", "No approach specified")
            thoughts = candidate.get("thoughts", [])
            answer = candidate.get("answer", "No answer provided")
            confidence = candidate.get("confidence", "unknown")
            
            formatted_candidate = f"""
**Candidate {agent_id}:**
- Approach: {approach}
- Confidence: {confidence}
- Reasoning Steps:
"""
            
            for j, thought in enumerate(thoughts[:10], 1):  # Limit to 10 thoughts
                formatted_candidate += f"  {j}. {thought}\n"
            
            formatted_candidate += f"- Final Answer: {answer}\n"
            
            formatted_parts.append(formatted_candidate)
        
        return "\n".join(formatted_parts)
    
    def _validate_and_enhance_critique(
        self,
        critique: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate the critique structure and add defaults for missing fields.
        
        Args:
            critique: Raw critique from LLM
            candidates: Original candidates
            
        Returns:
            Validated and enhanced critique
        """
        evaluations = critique.get("evaluations", [])
        
        # Ensure we have evaluations for all candidates
        candidate_ids = [c.get("agent_id", i) for i, c in enumerate(candidates)]
        
        enhanced_evaluations = []
        for candidate_id in candidate_ids:
            # Find existing evaluation or create default
            existing_eval = next(
                (e for e in evaluations if e.get("agent_id") == candidate_id),
                None
            )
            
            if existing_eval:
                enhanced_eval = self._validate_evaluation(existing_eval, candidate_id)
            else:
                enhanced_eval = self._create_default_evaluation(candidate_id)
            
            enhanced_evaluations.append(enhanced_eval)
        
        # Create ranking from evaluations
        ranking = self._create_ranking(enhanced_evaluations)
        
        enhanced_critique = {
            "evaluations": enhanced_evaluations,
            "ranking": ranking,
            "overall_assessment": critique.get(
                "overall_assessment",
                f"Evaluated {len(candidates)} candidates with varying quality."
            ),
            "improvement_suggestions": critique.get(
                "improvement_suggestions",
                ["Consider more detailed reasoning", "Provide better evidence"]
            )
        }
        
        logger.debug(
            "critique_validated",
            agent_id=self.agent_id,
            evaluations_count=len(enhanced_evaluations),
            ranking_count=len(ranking)
        )
        
        return enhanced_critique
    
    def _validate_evaluation(
        self,
        evaluation: Dict[str, Any],
        agent_id: Any
    ) -> Dict[str, Any]:
        """
        Validate and normalize a single evaluation.
        
        Args:
            evaluation: Raw evaluation data
            agent_id: Agent ID for this evaluation
            
        Returns:
            Validated evaluation
        """
        scores = evaluation.get("scores", {})
        
        # Normalize scores to 0-10 range
        normalized_scores = {}
        for criterion in ["correctness", "completeness", "clarity", "insight", "evidence"]:
            raw_score = scores.get(criterion, 5)
            normalized_scores[criterion] = max(0, min(10, int(raw_score)))
        
        total_score = sum(normalized_scores.values())
        
        return {
            "agent_id": agent_id,
            "scores": normalized_scores,
            "total_score": total_score,
            "strengths": evaluation.get("strengths", ["General reasoning"]),
            "weaknesses": evaluation.get("weaknesses", ["Could be improved"]),
            "feedback": evaluation.get("feedback", "Standard evaluation")
        }
    
    def _create_default_evaluation(self, agent_id: Any) -> Dict[str, Any]:
        """
        Create a default evaluation for missing candidates.
        
        Args:
            agent_id: Agent ID for this evaluation
            
        Returns:
            Default evaluation structure
        """
        return {
            "agent_id": agent_id,
            "scores": {
                "correctness": 5,
                "completeness": 5,
                "clarity": 5,
                "insight": 5,
                "evidence": 5
            },
            "total_score": 25,
            "strengths": ["Attempted the problem"],
            "weaknesses": ["Limited evaluation available"],
            "feedback": "Default evaluation - original response may have been incomplete"
        }
    
    def _create_ranking(
        self,
        evaluations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create ranking from evaluations.
        
        Args:
            evaluations: List of evaluations
            
        Returns:
            Ranked list of candidates
        """
        # Sort by total score (descending)
        sorted_evals = sorted(
            evaluations,
            key=lambda x: x.get("total_score", 0),
            reverse=True
        )
        
        ranking = []
        for rank, evaluation in enumerate(sorted_evals, 1):
            ranking.append({
                "agent_id": evaluation.get("agent_id"),
                "total_score": evaluation.get("total_score", 0),
                "rank": rank,
                "rationale": self._generate_ranking_rationale(evaluation, rank)
            })
        
        return ranking
    
    def _generate_ranking_rationale(
        self,
        evaluation: Dict[str, Any], 
        rank: int
    ) -> str:
        """
        Generate rationale for ranking position.
        
        Args:
            evaluation: Evaluation data
            rank: Ranking position
            
        Returns:
            Rationale string
        """
        total_score = evaluation.get("total_score", 0)
        scores = evaluation.get("scores", {})
        
        if rank == 1:
            highest_criterion = max(scores.items(), key=lambda x: x[1])
            return f"Top scorer with {total_score}/50 points, excellent {highest_criterion[0]}"
        elif rank <= 3:
            return f"Strong candidate with {total_score}/50 points, good overall performance"
        else:
            return f"Moderate performance with {total_score}/50 points, room for improvement"
    
    def _create_fallback_critique(
        self,
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a fallback critique when JSON parsing fails.
        
        Args:
            candidates: Original candidates
            
        Returns:
            Basic critique structure
        """
        logger.warning(
            "using_fallback_critique",
            agent_id=self.agent_id,
            candidates_count=len(candidates)
        )
        
        evaluations = []
        for i, candidate in enumerate(candidates):
            agent_id = candidate.get("agent_id", i)
            evaluations.append(self._create_default_evaluation(agent_id))
        
        return {
            "evaluations": evaluations,
            "ranking": self._create_ranking(evaluations),
            "overall_assessment": "Fallback critique - detailed evaluation unavailable",
            "improvement_suggestions": ["Review reasoning quality", "Enhance clarity"]
        }
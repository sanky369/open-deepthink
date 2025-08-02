"""
Base agent class for all Deep Think agents.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
import re
import structlog
from clients.gemini import GeminiClient

logger = structlog.get_logger()


# JSON Schema definitions for structured output
THINKER_SCHEMA = {
    "type": "object",
    "properties": {
        "agent_id": {"type": "integer"},
        "approach": {"type": "string"},
        "thoughts": {
            "type": "array",
            "items": {"type": "string"}
        },
        "answer": {"type": "string"},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "reasoning_quality": {"type": "string"},
        "potential_issues": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["agent_id", "approach", "thoughts", "answer", "confidence"]
}

PLANNER_SCHEMA = {
    "type": "object",
    "properties": {
        "task": {"type": "string"},
        "reasoning_type": {"type": "string"},
        "key_aspects": {
            "type": "array",
            "items": {"type": "string"}
        },
        "domain_hints": {
            "type": "array",
            "items": {"type": "string"}
        },
        "complexity_level": {"type": "string", "enum": ["simple", "moderate", "complex"]},
        "thinking_budget": {"type": "integer"},
        "success_criteria": {"type": "string"},
        "research_needed": {"type": "boolean"},
        "research_steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "type": {"type": "string", "enum": ["search"]},
                    "query": {"type": "string"},
                    "purpose": {"type": "string"}
                },
                "required": ["id", "type", "query"]
            }
        }
    },
    "required": ["task", "reasoning_type", "key_aspects", "complexity_level", "thinking_budget"]
}

CRITIC_SCHEMA = {
    "type": "object",
    "properties": {
        "evaluations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "rubric_scores": {
                        "type": "object",
                        "properties": {
                            "clarity_coherence": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "number"},
                                    "justification": {"type": "string"}
                                },
                                "required": ["score", "justification"]
                            },
                            "logical_soundness": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "number"},
                                    "justification": {"type": "string"}
                                },
                                "required": ["score", "justification"]
                            },
                            "completeness_depth": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "number"},
                                    "justification": {"type": "string"}
                                },
                                "required": ["score", "justification"]
                            },
                            "originality_insight": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "number"},
                                    "justification": {"type": "string"}
                                },
                                "required": ["score", "justification"]
                            },
                            "evidence_support": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "number"},
                                    "justification": {"type": "string"}
                                },
                                "required": ["score", "justification"]
                            }
                        },
                        "required": ["clarity_coherence", "logical_soundness", "completeness_depth", "originality_insight", "evidence_support"]
                    },
                    "weighted_total_score": {"type": "number"},
                    "strengths": {"type": "array", "items": {"type": "string"}},
                    "weaknesses": {"type": "array", "items": {"type": "string"}},
                    "targeted_improvements": {"type": "array", "items": {"type": "string"}},
                    "detailed_feedback": {"type": "string"}
                },
                "required": ["agent_id", "rubric_scores", "weighted_total_score"]
            }
        },
        "ranking": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rank": {"type": "integer"},
                    "agent_id": {"type": "string"},
                    "weighted_total_score": {"type": "number"},
                    "rationale": {"type": "string"}
                },
                "required": ["rank", "agent_id", "weighted_total_score"]
            }
        },
        "overall_assessment": {"type": "string"},
        "improvement_suggestions": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["evaluations", "ranking"]
}

REFINER_SCHEMA = {
    "type": "object",
    "properties": {
        "final_answer": {"type": "string"},
        "synthesis_approach": {"type": "string"},
        "sources_used": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "elements_borrowed": {"type": "array", "items": {"type": "string"}},
                    "contribution_weight": {"type": "string", "enum": ["low", "medium", "high"]}
                },
                "required": ["agent_id", "contribution_weight"]
            }
        },
        "improvements_made": {"type": "array", "items": {"type": "string"}},
        "confidence_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "reasoning_quality": {"type": "string"},
        "completeness": {"type": "string"}
    },
    "required": ["final_answer", "synthesis_approach", "confidence_level"]
}


class BaseAgent(ABC):
    """Abstract base class for all Deep Think agents."""
    
    def __init__(
        self,
        agent_id: str,
        gemini_client: GeminiClient,
        prompt_template: str
    ):
        """
        Initialize base agent.
        
        Args:
            agent_id: Unique identifier for this agent instance
            gemini_client: Configured Gemini client
            prompt_template: Template string for prompts
        """
        self.agent_id = agent_id
        self.client = gemini_client
        self.prompt_template = prompt_template
        
        logger.debug(
            "agent_initialized",
            agent_id=agent_id,
            agent_type=self.__class__.__name__
        )
    
    @abstractmethod
    async def execute(
        self,
        input_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute the agent's core logic.
        
        Args:
            input_data: Input data for the agent
            **kwargs: Additional execution parameters
            
        Returns:
            Agent execution results
        """
        pass
    
    async def _call_llm(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_mime_type: Optional[str] = None,
        response_schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Call the LLM with logging and error handling.
        
        Args:
            prompt: Formatted prompt
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            response_mime_type: Expected response format
            **kwargs: Additional parameters
            
        Returns:
            LLM response text
        """
        # Enforce safe upper bound for Gemini to prevent empty responses when MAX_TOKENS reached
        max_allowed_tokens = 8192
        if max_tokens > max_allowed_tokens:
            logger.warning(
                "max_tokens_clamped",
                agent_id=self.agent_id,
                agent_type=self.__class__.__name__,
                provided=max_tokens,
                clamped_to=max_allowed_tokens
            )
            max_tokens = max_allowed_tokens
        
        logger.info(
            "agent_llm_call_start",
            agent_id=self.agent_id,
            agent_type=self.__class__.__name__,
            prompt_length=len(prompt),
            prompt_preview=prompt[:200] + "..." if len(prompt) > 200 else prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        try:
            result = await self.client.generate_content_async(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                response_mime_type=response_mime_type,
                response_schema=response_schema,
                **kwargs
            )
            
            logger.info(
                "agent_llm_call_success",
                agent_id=self.agent_id,
                agent_type=self.__class__.__name__,
                response_length=len(result),
                response_preview=result[:200] + "..." if len(result) > 200 else result
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "agent_llm_call_failed",
                agent_id=self.agent_id,
                agent_type=self.__class__.__name__,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def _format_prompt(self, template_vars: Dict[str, Any]) -> str:
        """
        Format the prompt template with provided variables.
        
        Args:
            template_vars: Variables to substitute in template
            
        Returns:
            Formatted prompt string
        """
        try:
            formatted = self.prompt_template.format(**template_vars)
            
            logger.debug(
                "prompt_formatted",
                agent_id=self.agent_id,
                agent_type=self.__class__.__name__,
                template_vars=list(template_vars.keys()),
                formatted_length=len(formatted)
            )
            
            return formatted
            
        except KeyError as e:
            logger.error(
                "prompt_formatting_error",
                agent_id=self.agent_id,
                agent_type=self.__class__.__name__,
                missing_var=str(e),
                available_vars=list(template_vars.keys())
            )
            raise ValueError(f"Missing template variable: {e}")
    
    def _parse_json_with_recovery(
        self,
        response: str,
        fallback_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse JSON response with robust error handling and recovery.
        
        Args:
            response: Raw LLM response
            fallback_result: Optional fallback result if all parsing fails
            
        Returns:
            Parsed result or fallback structure
        """
        # First try direct JSON parsing
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(
                "json_parse_error",
                agent_id=self.agent_id,
                agent_type=self.__class__.__name__,
                error=str(e),
                response_preview=response[:500]
            )
            
            # Try to recover from common JSON issues
            recovered_result = self._attempt_json_recovery(response)
            if recovered_result:
                logger.info(
                    "json_recovery_successful",
                    agent_id=self.agent_id,
                    agent_type=self.__class__.__name__
                )
                return recovered_result
            
            # Use provided fallback or generic one
            if fallback_result:
                return fallback_result
            
            return self._create_generic_fallback_result(response)
    
    def _attempt_json_recovery(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to recover partial or malformed JSON.
        
        Args:
            response: Raw response that failed JSON parsing
            
        Returns:
            Recovered JSON dict or None if recovery failed
        """
        try:
            # Remove trailing incomplete content and try to close JSON
            response = response.strip()
            
            # Find the last complete key-value pair
            lines = response.split('\n')
            json_lines = []
            brace_count = 0
            
            for line in lines:
                json_lines.append(line)
                brace_count += line.count('{') - line.count('}')
                
                # If we have balanced braces, try parsing up to this point
                if brace_count == 0 and line.strip().endswith('}'):
                    try:
                        partial_json = '\n'.join(json_lines)
                        return json.loads(partial_json)
                    except:
                        continue
            
            # Try to fix unterminated strings by adding closing quote and brace
            if '"' in response and not response.strip().endswith('}'):
                # Find the last quote and try to close the JSON
                fixed_attempts = [
                    response + '"}\n}',  # Close string and object
                    response + '"}',     # Just close string and object
                    response.rsplit('"', 1)[0] + '"}',  # Remove partial string and close
                ]
                
                for attempt in fixed_attempts:
                    try:
                        return json.loads(attempt)
                    except:
                        continue
            
            # Try to extract JSON from within the response (sometimes wrapped in text)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
                    
        except Exception as e:
            logger.debug(
                "json_recovery_failed",
                agent_id=self.agent_id,
                agent_type=self.__class__.__name__,
                error=str(e)
            )
        
        return None
    
    def _create_generic_fallback_result(self, raw_response: str) -> Dict[str, Any]:
        """
        Create a generic fallback result when JSON parsing fails.
        
        Args:
            raw_response: Raw LLM response
            
        Returns:
            Basic result structure
        """
        logger.warning(
            "using_generic_fallback_result",
            agent_id=self.agent_id,
            agent_type=self.__class__.__name__,
            response_preview=raw_response[:200]
        )
        
        return {
            "error": "JSON parsing failed",
            "raw_response": raw_response[:1000],  # Truncate for safety
            "fallback": True,
            "agent_id": self.agent_id,
            "agent_type": self.__class__.__name__
        }

    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information for debugging/monitoring."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.__class__.__name__,
            "model_info": self.client.get_client_info()
        }
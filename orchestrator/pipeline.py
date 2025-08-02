"""
Deep Think orchestration pipeline for coordinating all agents.
"""
import asyncio
from typing import List, Dict, Any, Optional
import structlog
from clients.gemini import GeminiClient
from agents.planner import PlannerAgent
from agents.thinker import ThinkerAgent
from agents.critic import CriticAgent
from agents.refiner import RefinerAgent

logger = structlog.get_logger()


class DeepThinkPipeline:
    """
    Main orchestration pipeline that coordinates all Deep Think agents
    to process queries through the parallel thinking → critique → refinement loop.
    """
    
    def __init__(
        self,
        gemini_client: GeminiClient,
        prompt_templates: Dict[str, str]
    ):
        """
        Initialize the Deep Think pipeline.
        
        Args:
            gemini_client: Configured Gemini client for all agents
            prompt_templates: Dict of prompt templates for each agent type
        """
        self.client = gemini_client
        self.prompt_templates = prompt_templates
        
        # Initialize core agents
        self.planner = PlannerAgent(
            agent_id="planner",
            gemini_client=gemini_client,
            prompt_template=prompt_templates.get("planner", "")
        )
        
        self.critic = CriticAgent(
            agent_id="critic",
            gemini_client=gemini_client,
            prompt_template=prompt_templates.get("critic", "")
        )
        
        self.refiner = RefinerAgent(
            agent_id="refiner",
            gemini_client=gemini_client,
            prompt_template=prompt_templates.get("refiner", "")
        )
        
        logger.info(
            "pipeline_initialized",
            model=gemini_client.model_name
        )
    
    async def run(
        self,
        query: str,
        n_paths: int = 8,
        max_iterations: int = 1,
        top_k: int = 3,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Execute the full Deep Think pipeline.
        
        Args:
            query: User query to process
            n_paths: Number of parallel thinking paths
            max_iterations: Maximum iterations (currently unused)
            top_k: Number of top candidates to refine
            timeout: Pipeline timeout in seconds
            
        Returns:
            Dict containing final answer and pipeline metadata
        """
        pipeline_start_time = asyncio.get_event_loop().time()
        
        logger.info(
            "pipeline_execution_start",
            query_length=len(query),
            n_paths=n_paths,
            top_k=top_k,
            timeout=timeout
        )
        
        try:
            # Execute pipeline with timeout
            result = await asyncio.wait_for(
                self._execute_pipeline(query, n_paths, top_k),
                timeout=timeout
            )
            
            # Add timing metadata
            execution_time = asyncio.get_event_loop().time() - pipeline_start_time
            result["metadata"]["execution_time_seconds"] = round(execution_time, 2)
            
            logger.info(
                "pipeline_execution_complete",
                execution_time=execution_time,
                final_answer_length=len(result.get("answer", "")),
                n_paths=n_paths
            )
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(
                "pipeline_timeout",
                timeout=timeout,
                query_preview=query[:100]
            )
            raise TimeoutError(f"Pipeline execution exceeded {timeout} seconds")
            
        except Exception as e:
            logger.error(
                "pipeline_execution_error",
                error=str(e),
                error_type=type(e).__name__,
                query_preview=query[:100]
            )
            raise
    
    async def _execute_pipeline(
        self,
        query: str,
        n_paths: int,
        top_k: int
    ) -> Dict[str, Any]:
        """
        Execute the core pipeline logic.
        
        Args:
            query: User query
            n_paths: Number of thinking paths
            top_k: Number of top candidates for refinement
            
        Returns:
            Pipeline execution result
        """
        # Stage 1: Planning
        logger.debug("pipeline_stage", stage="planning", query_preview=query[:100])
        
        plan_result = await self.planner.execute({
            "query": query,
            "n_paths": n_paths
        })
        
        # Stage 2: Parallel Thinking
        logger.debug("pipeline_stage", stage="thinking", n_paths=n_paths)
        
        # Create thinker tasks with different seeds for diversity
        thinker_tasks = []
        for i in range(n_paths):
            thinker = ThinkerAgent(
                agent_id=f"thinker_{i}",
                gemini_client=self.client,
                prompt_template=self.prompt_templates.get("thinker", ""),
                seed=i
            )
            task = thinker.execute(plan_result)
            thinker_tasks.append(task)
        
        # Execute all thinkers in parallel
        candidates = await asyncio.gather(*thinker_tasks, return_exceptions=True)
        
        # Filter out any failed candidates
        valid_candidates = []
        failed_count = 0
        
        for i, candidate in enumerate(candidates):
            if isinstance(candidate, Exception):
                logger.warning(
                    "thinker_failed",
                    thinker_id=i,
                    error=str(candidate)
                )
                failed_count += 1
            else:
                valid_candidates.append(candidate)
        
        if not valid_candidates:
            raise RuntimeError("All thinking paths failed")
        
        logger.debug(
            "thinking_stage_complete",
            valid_candidates=len(valid_candidates),
            failed_candidates=failed_count
        )
        
        # Stage 3: Critique
        logger.debug("pipeline_stage", stage="critique")
        
        critique_result = await self.critic.execute({
            "candidates": valid_candidates
        })
        
        # Stage 4: Refinement
        logger.debug("pipeline_stage", stage="refinement", top_k=top_k)
        
        final_result = await self.refiner.execute(
            {
                "critique": critique_result,
                "candidates": valid_candidates
            },
            top_k=top_k
        )
        
        # Compile final response
        return {
            "query": query,
            "answer": final_result.get("final_answer", "Unable to generate answer"),
            "metadata": {
                "n_paths": n_paths,
                "candidates_generated": len(valid_candidates),
                "candidates_failed": failed_count,
                "top_k_used": top_k,
                "synthesis_approach": final_result.get("synthesis_approach"),
                "confidence_level": final_result.get("confidence_level"),
                "pipeline_stages": ["planning", "thinking", "critique", "refinement"]
            },
            "detailed_results": {
                "plan": plan_result,
                "candidates": valid_candidates,
                "critique": critique_result,
                "synthesis": final_result
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the pipeline and its components.
        
        Returns:
            Health check results
        """
        logger.info("pipeline_health_check_start")
        
        health_results = {
            "pipeline": "healthy",
            "components": {},
            "timestamp": asyncio.get_event_loop().time()
        }
        
        try:
            # Check Gemini client
            client_healthy = await self.client.health_check()
            health_results["components"]["gemini_client"] = {
                "status": "healthy" if client_healthy else "unhealthy",
                "details": self.client.get_client_info()
            }
            
            # Check agent initialization
            agents_status = {}
            for agent_name, agent in [
                ("planner", self.planner),
                ("critic", self.critic),
                ("refiner", self.refiner)
            ]:
                try:
                    agent_info = agent.get_agent_info()
                    agents_status[agent_name] = {
                        "status": "healthy",
                        "details": agent_info
                    }
                except Exception as e:
                    agents_status[agent_name] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
            
            health_results["components"]["agents"] = agents_status
            
            # Overall health
            all_healthy = (
                client_healthy and
                all(a["status"] == "healthy" for a in agents_status.values())
            )
            
            health_results["pipeline"] = "healthy" if all_healthy else "degraded"
            
            logger.info(
                "pipeline_health_check_complete",
                overall_status=health_results["pipeline"]
            )
            
            return health_results
            
        except Exception as e:
            logger.error(
                "pipeline_health_check_error",
                error=str(e)
            )
            health_results["pipeline"] = "unhealthy"
            health_results["error"] = str(e)
            return health_results
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """Get pipeline configuration information."""
        return {
            "model": self.client.model_name,
            "agents": {
                "planner": self.planner.get_agent_info(),
                "critic": self.critic.get_agent_info(),
                "refiner": self.refiner.get_agent_info()
            },
            "prompt_templates": {
                name: len(template) for name, template in self.prompt_templates.items()
            }
        }
"""
Deep Think orchestration pipeline for coordinating all agents.
"""
import asyncio
import os
from typing import List, Dict, Any, Optional
import structlog
from clients.gemini import GeminiClient
from agents.planner import PlannerAgent
from agents.thinker import ThinkerAgent
from agents.critic import CriticAgent
from agents.refiner import RefinerAgent
from agents.tools import ToolAgent
from agents.meta_refiner import MetaRefinerAgent

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
        
        self.tool_agent = ToolAgent(
            agent_id="tools",
            gemini_client=gemini_client,
            prompt_template=""  # Tool agent doesn't use prompt templates
        )
        
        self.meta_refiner = MetaRefinerAgent(
            agent_id="meta_refiner",
            gemini_client=gemini_client,
            prompt_template=prompt_templates.get("meta_refiner", "")
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
        
        # Stage 1.5: Research (if needed)
        research_results = None
        plan = plan_result.get("plan", {})
        
        if plan.get("research_needed", False) and plan.get("research_steps"):
            logger.debug("pipeline_stage", stage="research", steps_count=len(plan["research_steps"]))
            
            try:
                research_results = await self.tool_agent.execute({
                    "research_steps": plan["research_steps"]
                })
                
                logger.info(
                    "research_stage_complete",
                    research_summary=research_results.get("summary", "No results")
                )
                
            except Exception as e:
                logger.warning(
                    "research_stage_failed",
                    error=str(e),
                    fallback="continuing_without_research"
                )
                # Continue without research rather than failing the entire pipeline
                research_results = None
        
        # Stage 2: Parallel Thinking
        logger.debug("pipeline_stage", stage="thinking", n_paths=n_paths)
        
        # Create thinker tasks with different seeds for diversity
        thinker_tasks = []
        
        # Prepare thinker input data with research context
        thinker_input = {
            **plan_result,
            "research_context": research_results.get("tool_results") if research_results else None
        }
        
        for i in range(n_paths):
            thinker = ThinkerAgent(
                agent_id=f"thinker_{i}",
                gemini_client=self.client,
                prompt_template=self.prompt_templates.get("thinker", ""),
                seed=i
            )
            task = thinker.execute(thinker_input)
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
        
        refinement_result = await self.refiner.execute(
            {
                "critique": critique_result,
                "candidates": valid_candidates
            },
            top_k=top_k
        )
        
        # Stage 5: Meta-Refinement
        logger.debug("pipeline_stage", stage="meta_refinement")
        
        try:
            meta_refinement_result = await self.meta_refiner.execute({
                "query": query,
                "refined_solution": refinement_result.get("final_answer", "")
            })
            
            # Use meta-refined answer as the final answer
            final_answer = meta_refinement_result.get("meta_refined_answer", refinement_result.get("final_answer", ""))
            
            logger.info(
                "meta_refinement_stage_complete",
                synthesis_type=meta_refinement_result.get("synthesis_type"),
                elegance_score=meta_refinement_result.get("elegance_score"),
                intellectual_depth=meta_refinement_result.get("intellectual_depth")
            )
            
        except Exception as e:
            logger.warning(
                "meta_refinement_stage_failed",
                error=str(e),
                fallback="using_standard_refinement"
            )
            # Fall back to standard refinement if meta-refinement fails
            meta_refinement_result = None
            final_answer = refinement_result.get("final_answer", "Unable to generate answer")
        
        # Compile final response
        pipeline_stages = ["planning", "thinking", "critique", "refinement", "meta_refinement"]
        if research_results:
            pipeline_stages.insert(1, "research")  # Insert research stage after planning
        
        return {
            "query": query,
            "answer": final_answer,
            "metadata": {
                "n_paths": n_paths,
                "candidates_generated": len(valid_candidates),
                "candidates_failed": failed_count,
                "top_k_used": top_k,
                "synthesis_approach": refinement_result.get("synthesis_approach"),
                "confidence_level": refinement_result.get("confidence_level"),
                "research_conducted": research_results is not None,
                "meta_refinement_applied": meta_refinement_result is not None,
                "elegance_score": meta_refinement_result.get("elegance_score") if meta_refinement_result else None,
                "intellectual_depth": meta_refinement_result.get("intellectual_depth") if meta_refinement_result else None,
                "pipeline_stages": pipeline_stages
            },
            "detailed_results": {
                "plan": plan_result,
                "research": research_results,
                "candidates": valid_candidates,
                "critique": critique_result,
                "synthesis": refinement_result,
                "meta_refinement": meta_refinement_result
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
                ("refiner", self.refiner),
                ("tool_agent", self.tool_agent),
                ("meta_refiner", self.meta_refiner)
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
                "refiner": self.refiner.get_agent_info(),
                "tool_agent": self.tool_agent.get_agent_info(),
                "meta_refiner": self.meta_refiner.get_agent_info()
            },
            "prompt_templates": {
                name: len(template) for name, template in self.prompt_templates.items()
            },
            "research_capabilities": {
                "tavily_api_configured": bool(os.getenv("TAVILY_API_KEY")),
                "fallback_search_available": True
            },
            "meta_refinement_enabled": True
        }
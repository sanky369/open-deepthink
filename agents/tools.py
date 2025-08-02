"""
Tool Agent for grounded reasoning through external information sources.
"""
import os
import asyncio
from typing import Dict, Any, List, Optional
import structlog
import httpx
from .base import BaseAgent

logger = structlog.get_logger()


class ToolAgent(BaseAgent):
    """
    Agent responsible for tool-based research and grounded reasoning.
    Provides access to external information sources to enhance reasoning quality.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the Tool agent."""
        super().__init__(*args, **kwargs)
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def execute(
        self,
        input_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute tool-based research.
        
        Args:
            input_data: Must contain 'search_query' or 'research_steps'
            **kwargs: Additional execution parameters
            
        Returns:
            Dict containing research results
        """
        search_query = input_data.get("search_query")
        research_steps = input_data.get("research_steps", [])
        
        if not search_query and not research_steps:
            raise ValueError("Either search_query or research_steps are required")
        
        logger.info(
            "tool_execution_start",
            agent_id=self.agent_id,
            search_query=search_query,
            research_steps_count=len(research_steps)
        )
        
        try:
            results = {}
            
            # Handle single search query
            if search_query:
                search_result = await self.search(search_query)
                results["primary_search"] = {
                    "query": search_query,
                    "results": search_result
                }
            
            # Handle multiple research steps
            if research_steps:
                step_results = []
                for i, step in enumerate(research_steps):
                    step_query = step.get("query", "")
                    step_type = step.get("type", "search")
                    
                    if step_type == "search" and step_query:
                        search_result = await self.search(step_query)
                        step_results.append({
                            "step_id": step.get("id", i),
                            "query": step_query,
                            "type": step_type,
                            "results": search_result
                        })
                
                results["research_steps"] = step_results
            
            logger.info(
                "tool_execution_complete",
                agent_id=self.agent_id,
                results_count=len(results)
            )
            
            return {
                "tool_results": results,
                "summary": self._summarize_results(results),
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            logger.error(
                "tool_execution_error",
                agent_id=self.agent_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Perform a web search using available search APIs.
        
        Args:
            query: Search query
            
        Returns:
            List of search results
        """
        logger.debug(
            "search_start",
            agent_id=self.agent_id,
            query=query
        )
        
        try:
            # Try Tavily first if API key is available
            if self.tavily_api_key:
                return await self._search_tavily(query)
            else:
                # Fallback to simulated search for testing
                logger.warning(
                    "tavily_api_key_not_found",
                    agent_id=self.agent_id,
                    fallback="simulated_search"
                )
                return await self._search_fallback(query)
                
        except Exception as e:
            logger.error(
                "search_error",
                agent_id=self.agent_id,
                query=query,
                error=str(e)
            )
            # Return fallback search on any error
            return await self._search_fallback(query)
    
    async def _search_tavily(self, query: str) -> List[Dict[str, Any]]:
        """
        Search using Tavily API.
        
        Args:
            query: Search query
            
        Returns:
            List of search results
        """
        try:
            tavily_url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.tavily_api_key,
                "query": query,
                "search_depth": "advanced",
                "include_answer": True,
                "max_results": 5
            }
            
            response = await self.http_client.post(tavily_url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Process Tavily results
            for result in data.get("results", [])[:3]:  # Limit to top 3
                results.append({
                    "title": result.get("title", ""),
                    "content": result.get("content", "")[:500],  # Limit content length
                    "url": result.get("url", ""),
                    "score": result.get("score", 0)
                })
            
            # Add answer if available
            if data.get("answer"):
                results.insert(0, {
                    "title": "Direct Answer",
                    "content": data["answer"][:500],
                    "url": "",
                    "score": 1.0,
                    "type": "direct_answer"
                })
            
            logger.info(
                "tavily_search_success",
                agent_id=self.agent_id,
                query=query,
                results_count=len(results)
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "tavily_search_error",
                agent_id=self.agent_id,
                query=query,
                error=str(e)
            )
            raise
    
    async def _search_fallback(self, query: str) -> List[Dict[str, Any]]:
        """
        Fallback search that provides simulated results for testing.
        
        Args:
            query: Search query
            
        Returns:
            List of simulated search results
        """
        # Simulate some basic research results based on query keywords
        simulated_results = []
        
        # Generate contextual simulated results
        if any(keyword in query.lower() for keyword in ["quantum", "physics", "computing"]):
            simulated_results = [
                {
                    "title": "Quantum Computing Advances",
                    "content": "Recent developments in quantum computing show promising results for solving complex computational problems...",
                    "url": "https://example.com/quantum-computing",
                    "score": 0.9,
                    "type": "simulated"
                },
                {
                    "title": "Quantum Physics Research",
                    "content": "Current research in quantum physics explores fundamental properties of matter and energy...",
                    "url": "https://example.com/quantum-physics",
                    "score": 0.8,
                    "type": "simulated"
                }
            ]
        elif any(keyword in query.lower() for keyword in ["ai", "machine learning", "artificial intelligence"]):
            simulated_results = [
                {
                    "title": "AI Research Trends",
                    "content": "Latest trends in artificial intelligence show significant progress in language models and reasoning systems...",
                    "url": "https://example.com/ai-trends",
                    "score": 0.9,
                    "type": "simulated"
                },
                {
                    "title": "Machine Learning Applications",
                    "content": "Machine learning applications span across various industries including healthcare, finance, and technology...",
                    "url": "https://example.com/ml-applications",
                    "score": 0.8,
                    "type": "simulated"
                }
            ]
        else:
            # Generic fallback
            simulated_results = [
                {
                    "title": f"Research on: {query}",
                    "content": f"This is simulated research content related to '{query}'. In a real implementation, this would contain actual search results from web sources.",
                    "url": "https://example.com/simulated-research",
                    "score": 0.7,
                    "type": "simulated"
                }
            ]
        
        logger.info(
            "fallback_search_complete",
            agent_id=self.agent_id,
            query=query,
            results_count=len(simulated_results)
        )
        
        return simulated_results
    
    def _summarize_results(self, results: Dict[str, Any]) -> str:
        """
        Create a summary of the research results.
        
        Args:
            results: Research results dictionary
            
        Returns:
            Summary string
        """
        summary_parts = []
        
        if "primary_search" in results:
            primary = results["primary_search"]
            result_count = len(primary.get("results", []))
            summary_parts.append(f"Primary search for '{primary['query']}' returned {result_count} results")
        
        if "research_steps" in results:
            steps_count = len(results["research_steps"])
            summary_parts.append(f"Completed {steps_count} research steps")
        
        return "; ".join(summary_parts) if summary_parts else "No research results available"
    
    async def cleanup(self):
        """Clean up HTTP client resources."""
        if hasattr(self, 'http_client'):
            await self.http_client.aclose()
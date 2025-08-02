"""
FastAPI dependency injection for the Deep Think application.
"""
from functools import lru_cache
from typing import Dict
import aiofiles
import structlog
from clients.gemini import GeminiClient
from orchestrator.pipeline import DeepThinkPipeline
from .config import get_settings

logger = structlog.get_logger()


@lru_cache()
async def load_prompt_templates() -> Dict[str, str]:
    """
    Load prompt templates from files.
    
    Returns:
        Dictionary of prompt templates
    """
    templates = {}
    template_files = {
        "planner": "prompts/planner.txt",
        "thinker": "prompts/thinker.txt",
        "critic": "prompts/critic.txt",
        "refiner": "prompts/refiner.txt"
    }
    
    for template_name, file_path in template_files.items():
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                templates[template_name] = content.strip()
                
            logger.debug(
                "prompt_template_loaded",
                template_name=template_name,
                file_path=file_path,
                content_length=len(templates[template_name])
            )
        except FileNotFoundError:
            logger.error(
                "prompt_template_not_found",
                template_name=template_name,
                file_path=file_path
            )
            # Provide a basic fallback template
            templates[template_name] = f"You are a {template_name} agent. Process the input: {{input}}"
        except Exception as e:
            logger.error(
                "prompt_template_load_error",
                template_name=template_name,
                file_path=file_path,
                error=str(e)
            )
            raise
    
    logger.info(
        "prompt_templates_loaded",
        templates_count=len(templates),
        template_names=list(templates.keys())
    )
    
    return templates


@lru_cache()
def get_gemini_client() -> GeminiClient:
    """
    Get a configured Gemini client instance.
    
    Returns:
        Configured GeminiClient instance
    """
    settings = get_settings()
    
    client = GeminiClient(
        api_key=settings.gemini_api_key,
        timeout=settings.gemini_timeout,
        model_name=settings.gemini_model_name
    )
    
    logger.info(
        "gemini_client_created",
        model=settings.gemini_model_name,
        timeout=settings.gemini_timeout
    )
    
    return client


# Global pipeline instance (will be initialized during startup)
_pipeline_instance = None


async def get_pipeline() -> DeepThinkPipeline:
    """
    Get the configured Deep Think pipeline instance.
    
    Returns:
        Configured DeepThinkPipeline instance
    """
    global _pipeline_instance
    
    if _pipeline_instance is None:
        logger.info("initializing_pipeline")
        
        # Load dependencies
        gemini_client = get_gemini_client()
        prompt_templates = await load_prompt_templates()
        
        # Create pipeline
        _pipeline_instance = DeepThinkPipeline(
            gemini_client=gemini_client,
            prompt_templates=prompt_templates
        )
        
        logger.info("pipeline_initialized")
    
    return _pipeline_instance


async def initialize_dependencies():
    """
    Initialize all dependencies during application startup.
    """
    logger.info("dependencies_initialization_start")
    
    try:
        # Initialize pipeline (which loads all other dependencies)
        await get_pipeline()
        
        # Skip health check during startup to avoid delays
        logger.info("dependencies_initialization_skipping_health_check")
        
        logger.info("dependencies_initialization_complete")
        
    except Exception as e:
        logger.error(
            "dependencies_initialization_error",
            error=str(e),
            error_type=type(e).__name__
        )
        raise


async def cleanup_dependencies():
    """
    Cleanup dependencies during application shutdown.
    """
    global _pipeline_instance
    
    logger.info("dependencies_cleanup_start")
    
    try:
        # Cleanup any resources if needed
        _pipeline_instance = None
        
        logger.info("dependencies_cleanup_complete")
        
    except Exception as e:
        logger.error(
            "dependencies_cleanup_error",
            error=str(e)
        )
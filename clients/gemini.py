"""
Gemini API client with retry logic and error handling.
"""
import asyncio
from typing import Dict, Any, Optional
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logger = structlog.get_logger()


class GeminiClient:
    """Async Gemini client with retry logic and comprehensive error handling."""
    
    def __init__(
        self,
        api_key: str,
        timeout: int = 30,
        model_name: str = "gemini-2.5-pro"
    ):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Gemini API key
            timeout: Request timeout in seconds
            model_name: Gemini model to use
        """
        self.api_key = api_key
        self.timeout = timeout
        self.model_name = model_name
        
        # Configure the client
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        # Safety settings - minimal blocking for reasoning tasks
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        logger.info(
            "gemini_client_initialized",
            model=model_name,
            timeout=timeout
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type((
            Exception,  # Catch all exceptions for now
        )),
        before_sleep=before_sleep_log(logger, 30)  # WARNING level
    )
    async def generate_content_async(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_mime_type: Optional[str] = None,
        response_schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Generate content with automatic retry logic and a hard per-request timeout.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum output tokens
            response_mime_type: Expected response format
            **kwargs: Additional generation parameters

        Returns:
            Generated text content

        Raises:
            asyncio.TimeoutError: If the Gemini API call exceeds `self.timeout`
            Exception: If all retry attempts fail or empty response returned
        """
        try:
            # Configure generation settings
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )

            # Add response format if specified
            if response_mime_type:
                generation_config.response_mime_type = response_mime_type
            
            # Add response schema if specified (Gemini 2.5+ structured output)
            if response_schema:
                generation_config.response_schema = response_schema

            logger.debug(
                "gemini_api_call",
                prompt_length=len(prompt),
                temperature=temperature,
                max_tokens=max_tokens,
                response_mime_type=response_mime_type,
                timeout_seconds=self.timeout
            )

            # Make the API call with per-request timeout enforcement
            try:
                response = await asyncio.wait_for(
                    self.model.generate_content_async(
                        prompt,
                        generation_config=generation_config,
                        safety_settings=self.safety_settings
                    ),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                logger.error(
                    "gemini_api_timeout",
                    prompt_preview=prompt[:100],
                    timeout=self.timeout
                )
                raise  # Reraise so tenacity or caller can handle

            # Extract text from response
            if not response.text:
                logger.warning(
                    "empty_response",
                    response=str(response),
                    prompt_preview=prompt[:100]
                )
                raise ValueError("Empty response from Gemini API")

            result = response.text.strip()

            logger.debug(
                "gemini_api_success",
                prompt_length=len(prompt),
                response_length=len(result),
                temperature=temperature
            )

            return result

        except Exception as e:
            logger.error(
                "gemini_api_error",
                error=str(e),
                error_type=type(e).__name__,
                prompt_preview=prompt[:100],
                temperature=temperature
            )
            raise
    
    async def health_check(self) -> bool:
        """
        Check if the Gemini API is accessible.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            test_response = await self.generate_content_async(
                "Please respond with the word 'healthy' to confirm the API connection is working properly.",
                temperature=0.0,
                max_tokens=4096
            )
            
            is_healthy = "HEALTHY" in test_response.upper() or "OK" in test_response.upper()
            
            logger.info(
                "health_check_completed",
                healthy=is_healthy,
                response=test_response
            )
            
            return is_healthy
            
        except Exception as e:
            logger.error(
                "health_check_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get client configuration information."""
        return {
            "model_name": self.model_name,
            "timeout": self.timeout,
            "has_api_key": bool(self.api_key),
            "api_key_preview": f"{self.api_key[:8]}..." if self.api_key else None
        }
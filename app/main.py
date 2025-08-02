"""
FastAPI application for the Open Deep Think service.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app, Counter, Histogram, Gauge
import structlog

from .config import get_settings
from .dependencies import get_pipeline, initialize_dependencies, cleanup_dependencies
from models.request import DeepThinkRequest, HealthCheckRequest
from models.response import DeepThinkResponse, HealthCheckResponse, ErrorResponse
from utils.logging import configure_logging

# Configure logging first
settings = get_settings()
configure_logging(settings.log_level, settings.debug)
logger = structlog.get_logger()

# Prometheus metrics
request_count = Counter(
    'deep_think_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'deep_think_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

active_requests = Gauge(
    'deep_think_active_requests',
    'Number of active requests'
)

pipeline_executions = Counter(
    'deep_think_pipeline_executions_total',
    'Total pipeline executions',
    ['status']
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("application_startup_begin")
    
    try:
        await initialize_dependencies()
        logger.info("application_startup_complete")
        yield
    except Exception as e:
        logger.error(
            "application_startup_error",
            error=str(e),
            error_type=type(e).__name__
        )
        raise
    finally:
        # Shutdown
        logger.info("application_shutdown_begin")
        await cleanup_dependencies()
        logger.info("application_shutdown_complete")


# Create FastAPI application
app = FastAPI(
    title="Open Deep Think",
    description="Open-source Gemini Deep Think orchestration layer",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect metrics."""
    active_requests.inc()
    
    method = request.method
    path = request.url.path
    
    with request_duration.labels(method=method, endpoint=path).time():
        try:
            response = await call_next(request)
            request_count.labels(
                method=method,
                endpoint=path,
                status=response.status_code
            ).inc()
            return response
        except Exception as e:
            request_count.labels(
                method=method,
                endpoint=path,
                status=500
            ).inc()
            raise
        finally:
            active_requests.dec()


# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred"
        ).dict()
    )


@app.post(
    "/think",
    response_model=DeepThinkResponse,
    summary="Execute Deep Think Pipeline",
    description="Process a query through the Deep Think pipeline with parallel reasoning paths"
)
async def deep_think(
    request: DeepThinkRequest,
    pipeline = Depends(get_pipeline)
):
    """Execute Deep Think pipeline on a query."""
    logger.info(
        "deep_think_request",
        query_length=len(request.query),
        n_paths=request.n_paths,
        top_k=request.top_k,
        timeout=request.timeout
    )
    
    try:
        # Execute pipeline
        result = await pipeline.run(
            query=request.query,
            n_paths=request.n_paths,
            max_iterations=request.max_iterations,
            top_k=request.top_k,
            timeout=request.timeout
        )
        
        # Create response
        response = DeepThinkResponse(
            query=result["query"],
            answer=result["answer"],
            metadata=result["metadata"],
            detailed_results=result.get("detailed_results") if settings.debug else None
        )
        
        pipeline_executions.labels(status="success").inc()
        
        logger.info(
            "deep_think_success",
            query_length=len(request.query),
            answer_length=len(response.answer),
            execution_time=result["metadata"].get("execution_time_seconds"),
            confidence=result["metadata"].get("confidence_level")
        )
        
        return response
        
    except asyncio.TimeoutError:
        pipeline_executions.labels(status="timeout").inc()
        logger.warning(
            "deep_think_timeout",
            query_length=len(request.query),
            timeout=request.timeout
        )
        raise HTTPException(
            status_code=408,
            detail=f"Pipeline execution exceeded {request.timeout} seconds"
        )
        
    except ValueError as e:
        pipeline_executions.labels(status="validation_error").inc()
        logger.warning(
            "deep_think_validation_error",
            error=str(e),
            query_length=len(request.query)
        )
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
        
    except Exception as e:
        pipeline_executions.labels(status="error").inc()
        logger.error(
            "deep_think_error",
            error=str(e),
            error_type=type(e).__name__,
            query_length=len(request.query)
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during pipeline execution"
        )


@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Check the health status of the Deep Think service and its components"
)
async def health_check(
    request: HealthCheckRequest = Depends(),
    pipeline = Depends(get_pipeline)
):
    """Perform health check on the service."""
    logger.debug(
        "health_check_request",
        include_details=request.include_details,
        check_api=request.check_api
    )
    
    try:
        if request.check_api:
            health_result = await pipeline.health_check()
        else:
            health_result = {
                "pipeline": "healthy",
                "components": {}
            }
        
        response = HealthCheckResponse(
            status=health_result["pipeline"],
            components=health_result.get("components") if request.include_details else None
        )
        
        logger.debug(
            "health_check_complete",
            status=response.status,
            include_details=request.include_details
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "health_check_error",
            error=str(e),
            error_type=type(e).__name__
        )
        return HealthCheckResponse(
            status="unhealthy",
            components={"error": str(e)} if request.include_details else None
        )


@app.get(
    "/info",
    summary="Service Information",
    description="Get information about the Deep Think service configuration"
)
async def service_info(pipeline = Depends(get_pipeline)):
    """Get service information."""
    try:
        pipeline_info = pipeline.get_pipeline_info()
        
        return {
            "service": {
                "name": settings.app_name,
                "version": "0.1.0",
                "debug": settings.debug
            },
            "configuration": {
                "default_n_paths": settings.default_n_paths,
                "default_top_k": settings.default_top_k,
                "pipeline_timeout": settings.pipeline_timeout,
                "gemini_model": settings.gemini_model_name
            },
            "pipeline": pipeline_info
        }
        
    except Exception as e:
        logger.error(
            "service_info_error",
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve service information"
        )


@app.get("/")
async def root():
    """Root endpoint with basic service information."""
    return {
        "service": "Open Deep Think",
        "version": "0.1.0",
        "description": "Open-source Gemini Deep Think orchestration layer",
        "endpoints": {
            "think": "/think",
            "health": "/health",
            "info": "/info",
            "docs": "/docs",
            "metrics": "/metrics"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
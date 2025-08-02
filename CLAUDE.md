# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Open Deep Think is a production-ready FastAPI application that replicates Google's Gemini 2.5 Deep Think capabilities using the publicly available gemini-2.5-pro API. The system implements a sophisticated orchestration pipeline with parallel thinking, critique, and refinement stages.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Development Server
```bash
# Start development server
python scripts/start_server.py

# Or with uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov=agents --cov=orchestrator --cov=clients

# Test specific modules
pytest tests/test_basic.py -v

# Test endpoints without starting server
python scripts/test_endpoints.py
```

### Code Quality
```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy .
```

## Architecture Overview

### Core Components

1. **FastAPI Application** (`app/`)
   - `main.py` - FastAPI app with endpoints, middleware, metrics
   - `config.py` - Pydantic settings with environment variable support
   - `dependencies.py` - Dependency injection for pipeline and clients

2. **Orchestration Pipeline** (`orchestrator/`)
   - `pipeline.py` - Main DeepThinkPipeline coordinating all agents
   - Manages parallel execution, error handling, and timeouts

3. **Agent Framework** (`agents/`)
   - `base.py` - Abstract BaseAgent with common functionality
   - `planner.py` - Decomposes queries and sets thinking parameters
   - `thinker.py` - Generates individual reasoning paths (parallel execution)
   - `critic.py` - Evaluates and scores multiple reasoning paths
   - `refiner.py` - Synthesizes top candidates into final answer

4. **API Client** (`clients/`)
   - `gemini.py` - Async Gemini client with retry logic and error handling
   - Implements exponential backoff, rate limiting, and comprehensive logging

5. **Data Models** (`models/`)
   - `request.py` - Pydantic request models with validation
   - `response.py` - Pydantic response models with metadata

6. **Prompt Templates** (`prompts/`)
   - Text files containing specialized prompts for each agent type
   - Loaded dynamically during application startup

### Key Design Patterns

- **Async/Await**: All I/O operations are asynchronous for high performance
- **Dependency Injection**: FastAPI dependencies manage client and pipeline lifecycles
- **Strategy Pattern**: Different agents implement specialized reasoning strategies
- **Pipeline Pattern**: Sequential stages with parallel execution within stages
- **Retry Pattern**: Exponential backoff for API resilience
- **Observer Pattern**: Structured logging throughout the system

## Configuration

### Environment Variables
Required:
- `GEMINI_API_KEY` - Your Gemini API key

Optional (with defaults):
- `DEBUG=false` - Enable debug mode
- `DEFAULT_N_PATHS=8` - Number of parallel thinking paths
- `DEFAULT_TOP_K=3` - Number of top candidates for refinement
- `PIPELINE_TIMEOUT=120` - Pipeline timeout in seconds
- `LOG_LEVEL=INFO` - Logging level

### Key Files
- `.env` - Environment variables (not committed)
- `.env.example` - Template for environment setup
- `requirements.txt` - Production dependencies
- `requirements-dev.txt` - Development dependencies
- `pyproject.toml` - Tool configuration (black, ruff, mypy)

## API Endpoints

- `POST /think` - Main Deep Think pipeline execution
- `GET /health` - Health check with component status
- `GET /info` - Service and pipeline information
- `GET /` - Root endpoint with service overview
- `GET /docs` - Interactive OpenAPI documentation
- `GET /metrics` - Prometheus metrics

## Development Workflow

### Adding New Features
1. Create feature branch
2. Implement changes following existing patterns
3. Add comprehensive tests
4. Update documentation
5. Ensure all tests pass: `pytest`
6. Check code quality: `black . && ruff check . && mypy .`
7. Test endpoints: `python scripts/test_endpoints.py`

### Agent Development
- Inherit from `BaseAgent` in `agents/base.py`
- Implement `execute()` method with proper error handling
- Add corresponding prompt template in `prompts/`
- Use structured logging for observability
- Follow async/await patterns consistently

### Testing Strategy
- Unit tests for individual components
- Integration tests for pipeline flows
- Endpoint tests using FastAPI TestClient
- Mock external API calls in tests
- Maintain high test coverage (target: 80%+)

## Production Considerations

### Performance
- Pipeline processes N paths in parallel (default: 8)
- Typical latency: ~2x single API call due to parallel processing
- Token usage: ~30-40x single call (configurable via n_paths/top_k)

### Monitoring
- Prometheus metrics at `/metrics`
- Structured JSON logging to stdout
- Health checks with component-level detail
- Request tracing with correlation IDs

### Scaling
- Stateless design enables horizontal scaling
- Rate limited by Gemini API (5 RPM free tier)
- Memory usage scales with concurrent requests
- Consider queue management for high load

## Troubleshooting

### Common Issues
- **API Key Errors**: Verify GEMINI_API_KEY is set and valid
- **Timeout Errors**: Increase PIPELINE_TIMEOUT or reduce n_paths
- **Import Errors**: Ensure virtual environment is activated
- **Validation Errors**: Check request format against models

### Debug Mode
Set `DEBUG=true` and `LOG_LEVEL=DEBUG` for verbose logging.

### Log Analysis
Key log events: `pipeline_execution_start`, `agent_llm_call_start`, `pipeline_execution_complete`

## Security Notes

- Never commit API keys to version control
- Use environment variables for secrets
- Input validation via Pydantic models
- Rate limiting and timeout protections
- Content filtering through Gemini API safety settings
# Open Deep Think - Deployment Guide

## Quick Start

### 1. Setup Environment

```bash
# Clone and navigate to project
cd DeepThinker

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
# Copy environment template
cp .env.example .env

# Edit .env file and add your Gemini API key
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 3. Start the Server

```bash
# Option 1: Using the startup script
python scripts/start_server.py

# Option 2: Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Test the Installation

```bash
# Run endpoint tests
python scripts/test_endpoints.py

# Or test manually
curl http://localhost:8000/
curl http://localhost:8000/health
```

## API Usage

### Basic Request

```bash
curl -X POST http://localhost:8000/think \
     -H "Content-Type: application/json" \
     -d '{
       "query": "Explain why the sum of reciprocals of squares converges",
       "n_paths": 4,
       "top_k": 2
     }'
```

### API Documentation

- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | Required | Your Gemini API key |
| `APP_NAME` | `open-deep-think` | Application name |
| `DEBUG` | `false` | Enable debug mode |
| `DEFAULT_N_PATHS` | `8` | Default thinking paths |
| `DEFAULT_TOP_K` | `3` | Default top candidates |
| `PIPELINE_TIMEOUT` | `120` | Pipeline timeout (seconds) |
| `LOG_LEVEL` | `INFO` | Logging level |

### Request Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `query` | string | Required | 1-10000 chars | Question to analyze |
| `n_paths` | integer | 8 | 1-32 | Parallel thinking paths |
| `top_k` | integer | 3 | 1-10 | Top candidates for refinement |
| `timeout` | integer | 120 | 30-600 | Request timeout (seconds) |

## Production Deployment

### Docker Deployment

```dockerfile
# Dockerfile is provided in the project root
docker build -t open-deep-think .
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key open-deep-think
```

### Docker Compose

```yaml
version: '3.8'
services:
  open-deep-think:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=your_key
      - DEBUG=false
      - LOG_LEVEL=INFO
    restart: unless-stopped
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: open-deep-think
spec:
  replicas: 3
  selector:
    matchLabels:
      app: open-deep-think
  template:
    metadata:
      labels:
        app: open-deep-think
    spec:
      containers:
      - name: api
        image: open-deep-think:latest
        ports:
        - containerPort: 8000
        env:
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: gemini-api-key
```

## Monitoring

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check with API validation
curl "http://localhost:8000/health?check_api=true&include_details=true"
```

### Prometheus Metrics

The application exposes metrics at `/metrics`:

- `deep_think_requests_total` - Total requests by endpoint/status
- `deep_think_request_duration_seconds` - Request duration histogram
- `deep_think_active_requests` - Active request gauge
- `deep_think_pipeline_executions_total` - Pipeline execution counts

### Logging

Structured JSON logs are output to stdout. Key log events:

- `pipeline_execution_start` - Pipeline begins
- `agent_llm_call_start` - LLM API calls
- `pipeline_execution_complete` - Pipeline finishes
- `deep_think_error` - Errors and failures

## Performance Tuning

### Cost Optimization

- **Reduce n_paths**: Lower parallel paths (4-6 vs 8)
- **Adjust top_k**: Use fewer candidates for refinement (2-3)
- **Set timeouts**: Prevent long-running requests
- **Cache responses**: Implement Redis caching for repeated queries

### Scaling Considerations

- **Rate Limiting**: Gemini API has rate limits (5 RPM free tier)
- **Concurrent Requests**: Adjust `max_concurrent_requests` setting
- **Load Balancing**: Use multiple instances behind a load balancer
- **Queue Management**: Implement request queuing for high load

## Troubleshooting

### Common Issues

1. **"API key not valid" Error**
   - Verify `GEMINI_API_KEY` is set correctly
   - Check key has proper permissions
   - Ensure key is not expired

2. **"Pipeline timeout" Error**
   - Increase `PIPELINE_TIMEOUT` setting
   - Reduce `n_paths` for faster execution
   - Check network connectivity to Gemini API

3. **"Empty response" Error**
   - Check Gemini API status
   - Verify content filtering settings
   - Review query content for policy violations

4. **High Memory Usage**
   - Reduce concurrent request limits
   - Implement response streaming
   - Add garbage collection tuning

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python scripts/start_server.py
```

### Log Analysis

```bash
# Filter pipeline execution logs
tail -f app.log | grep "pipeline_execution"

# Monitor API call durations
tail -f app.log | grep "agent_llm_call"

# Track errors
tail -f app.log | grep '"level": "error"'
```

## Security

### API Key Management

- Store API keys in environment variables or secret management systems
- Never commit API keys to version control
- Rotate API keys regularly
- Use different keys for different environments

### Network Security

- Use HTTPS in production
- Implement rate limiting
- Add authentication/authorization as needed
- Use firewall rules to restrict access

### Input Validation

- All inputs are validated using Pydantic models
- Query length is limited to prevent abuse
- Timeouts prevent resource exhaustion
- Content filtering through Gemini API safety settings

## Support

For issues and questions:

1. Check this deployment guide
2. Review application logs
3. Test with minimal configuration
4. Check Gemini API status and limits
5. Refer to the main README.md for architecture details
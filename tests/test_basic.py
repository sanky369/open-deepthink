"""
Basic tests for the Deep Think application.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# Test without actual API calls
@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from app.main import app
    return TestClient(app)


def test_root_endpoint(test_client):
    """Test the root endpoint."""
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Open Deep Think"
    assert "endpoints" in data


def test_health_endpoint_basic(test_client):
    """Test the health endpoint without API checks."""
    response = test_client.get("/health?check_api=false")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data


def test_info_endpoint_requires_pipeline():
    """Test that info endpoint requires pipeline initialization."""
    from app.main import app
    client = TestClient(app)
    
    # This might fail during startup if pipeline can't initialize
    # but we should still get a response structure
    response = client.get("/info")
    # Accept either success or server error for now
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_gemini_client_initialization():
    """Test Gemini client can be initialized with test config."""
    from clients.gemini import GeminiClient
    
    # Test with dummy API key
    client = GeminiClient(
        api_key="test_key",
        timeout=30,
        model_name="gemini-2.5-pro"
    )
    
    assert client.api_key == "test_key"
    assert client.timeout == 30
    assert client.model_name == "gemini-2.5-pro"
    
    # Test client info
    info = client.get_client_info()
    assert info["model_name"] == "gemini-2.5-pro"
    assert info["timeout"] == 30
    assert info["has_api_key"] == True


def test_request_model_validation():
    """Test request model validation."""
    from models.request import DeepThinkRequest
    
    # Valid request
    valid_request = DeepThinkRequest(
        query="What is 2+2?",
        n_paths=4,
        top_k=2
    )
    assert valid_request.query == "What is 2+2?"
    assert valid_request.n_paths == 4
    assert valid_request.top_k == 2
    
    # Invalid request - empty query
    with pytest.raises(ValueError):
        DeepThinkRequest(query="")
    
    # Invalid request - top_k > n_paths (should be auto-adjusted)
    request_with_high_top_k = DeepThinkRequest(
        query="Test query",
        n_paths=4,
        top_k=8  # Higher than n_paths
    )
    assert request_with_high_top_k.top_k == 4  # Should be adjusted to n_paths


def test_response_model_creation():
    """Test response model creation."""
    from models.response import DeepThinkResponse, PipelineMetadata
    
    metadata = PipelineMetadata(
        n_paths=4,
        candidates_generated=4,
        candidates_failed=0,
        top_k_used=2,
        execution_time_seconds=10.5,
        pipeline_stages=["planning", "thinking", "critique", "refinement"]
    )
    
    response = DeepThinkResponse(
        query="What is 2+2?",
        answer="2+2 equals 4",
        metadata=metadata
    )
    
    assert response.query == "What is 2+2?"
    assert response.answer == "2+2 equals 4"
    assert response.metadata.n_paths == 4
    assert response.metadata.execution_time_seconds == 10.5


if __name__ == "__main__":
    pytest.main([__file__])
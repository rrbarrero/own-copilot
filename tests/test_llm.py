import pytest
from app.core.llm import get_llm

def test_llm_invocation():
    """
    Test that the LLM is properly configured and can answer a simple prompt.
    This test requires a running Ollama server at the configured address.
    """
    try:
        llm = get_llm()
        # Using a very simple prompt to minimize latency and token usage
        response = llm.invoke("Responde solo con la palabra: HOLA")
        
        # Verify we get a response object (BaseMessage from LangChain)
        assert response is not None
        assert hasattr(response, "content")
        assert "HOLA" in response.content.upper()
        
    except Exception as e:
        pytest.fail(f"LLM invocation failed: {str(e)}")

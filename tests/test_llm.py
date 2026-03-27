import pytest

from app.factory import create_llm


@pytest.mark.e2e
def test_llm_invocation():
    """
    Test that the LLM is correctly configured and can respond to a simple prompt.
    This test requires the Ollama server to be running at the configured address.
    """
    try:
        llm = create_llm()
        # We use a very simple prompt to minimize latency and token usage
        response = llm.invoke("Respond only with the word: HELLO")

        # Verify that we get a response object (LangChain's BaseMessage)
        assert response is not None
        assert hasattr(response, "content")
        # Handle cases where the content might be a list (multimodal outputs)
        content_str = str(response.content)
        assert "HELLO" in content_str.upper()

    except Exception as e:
        pytest.fail(f"LLM invocation failed: {str(e)}")

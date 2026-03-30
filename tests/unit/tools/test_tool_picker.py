from unittest.mock import AsyncMock, MagicMock

import pytest

from app.tools.application.tool_picker import ToolPicker


@pytest.mark.asyncio
async def test_tool_picker_falls_back_for_unsupported_strategy():
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock()
    mock_llm.ainvoke.return_value.content = (
        '{"strategy":"delete_repo","parameters":{"path":"x"},"reasoning":"bad"}'
    )

    picker = ToolPicker(mock_llm)

    decision = await picker.decide("delete the repository")

    assert decision.strategy == "rag"
    assert decision.parameters == {}
    assert "Unsupported strategy" in decision.reasoning

import pytest
from src.core.config import config

def test_config_loaded():
    assert config.PROJECT_ROOT is not None

@pytest.mark.asyncio
async def test_async_dummy():
    assert True

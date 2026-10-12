import pytest
from apps.db.database import engine


@pytest.fixture(autouse=True)
async def dispose_engine_after_test():
    yield
    await engine.dispose()

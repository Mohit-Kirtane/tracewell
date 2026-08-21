import asyncio
from unittest.mock import patch

import pytest

from app.main import app, lifespan

pytestmark = pytest.mark.asyncio


async def test_lifespan_starts_and_cancels_worker_when_enabled():
    with patch("app.main.settings") as mock_settings, patch(
        "app.main.run_forever"
    ) as mock_run_forever:
        mock_settings.run_worker_inline = True

        started = asyncio.Event()

        async def _fake_forever():
            started.set()
            await asyncio.sleep(3600)

        mock_run_forever.side_effect = _fake_forever

        async with lifespan(app):
            await asyncio.wait_for(started.wait(), timeout=1)

        mock_run_forever.assert_called_once()


async def test_lifespan_does_nothing_when_disabled():
    with patch("app.main.settings") as mock_settings, patch(
        "app.main.run_forever"
    ) as mock_run_forever:
        mock_settings.run_worker_inline = False

        async with lifespan(app):
            pass

        mock_run_forever.assert_not_called()

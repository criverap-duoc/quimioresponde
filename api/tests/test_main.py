import pytest

import app.main as main


class _FailingEngine:
    def connect(self) -> None:
        raise OSError("sin red")


async def test_lifespan_arranca_si_neon_falla(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "get_engine", lambda: _FailingEngine())

    async with main.lifespan(main.app):
        pass

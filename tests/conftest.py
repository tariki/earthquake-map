"""テスト共通の準備。Gemini と P2P地震情報は偽物に置き換え、APIキーもネットワークも使わない。"""

from types import SimpleNamespace

import pytest

from server import main

SAMPLE_QUAKES = [
    {
        "id": "test-1",
        "time": "2026年08月23日 02時00分頃",
        "shortTime": "08/23 02:00",
        "location": "茨城県南部",
        "m": 5.9,
        "shindo": "5強",
        "shindoClass": "5-plus",
        "lat": 36.1,
        "lng": 140.0,
    },
]


class FakeGemini:
    """google-genai の Client の代わり。responses に文字列か例外を積むと、呼ばれた順に返す。"""

    def __init__(self):
        self.responses = []
        self.calls = []
        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=self._generate_content))

    async def _generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        result = self.responses.pop(0) if self.responses else "テスト回答"
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(text=result)


@pytest.fixture(autouse=True)
def isolate_server_state(monkeypatch):
    """テストごとに回数制限のカウントを消し、地震データを固定のサンプルにする。"""
    main._request_log.clear()

    async def fake_get_earthquakes():
        return SAMPLE_QUAKES

    monkeypatch.setattr(main, "get_earthquakes", fake_get_earthquakes)
    monkeypatch.setattr(main, "RETRY_BASE_DELAY", 0)


@pytest.fixture
def fake_gemini(monkeypatch):
    fake = FakeGemini()
    monkeypatch.setattr(main, "_gemini_client", fake)
    return fake

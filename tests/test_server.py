"""サーバー（server/main.py）のスモークテスト。"""

import pytest
from fastapi.testclient import TestClient
from google.genai import errors as genai_errors

from server import main

client = TestClient(main.app)

EARTHQUAKE = {"time": "2026年08月23日 02時00分頃", "location": "茨城県南部", "m": 5.9, "shindo": "5強", "lat": 36.1, "lng": 140.0}


def post_ai(body: dict, ip: str = "203.0.113.1"):
    return client.post("/api/ai", json=body, headers={"X-Forwarded-For": ip})


# ----------------- 配信 -----------------


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "震度5以上 プロットマップ" in response.text


def test_api_docs_are_disabled():
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


# ----------------- /api/ai: 正常系 -----------------


def test_report(fake_gemini):
    fake_gemini.responses = ["レポート本文"]
    response = post_ai({"task": "report"})
    assert response.status_code == 200
    assert response.json() == {"text": "レポート本文"}
    call = fake_gemini.calls[0]
    assert "トレンドレポート" in call["contents"]
    # 地震データはサーバーが取得したものをシステムプロンプトに入れる
    assert "茨城県南部" in call["config"].system_instruction


def test_analyze_builds_prompt_on_server(fake_gemini):
    response = post_ai({"task": "analyze", "earthquake": EARTHQUAKE})
    assert response.status_code == 200
    prompt = fake_gemini.calls[0]["contents"]
    assert "震源: 茨城県南部" in prompt
    assert "最大震度: 5強" in prompt


def test_chat_passes_message(fake_gemini):
    response = post_ai({"task": "chat", "message": "  家具の固定方法は？  "})
    assert response.status_code == 200
    assert fake_gemini.calls[0]["contents"] == "家具の固定方法は？"


def test_uses_configured_model(fake_gemini, monkeypatch):
    monkeypatch.setattr(main, "GEMINI_MODEL", "test-model")
    post_ai({"task": "report"})
    assert fake_gemini.calls[0]["model"] == "test-model"


# ----------------- /api/ai: 入力の検証 -----------------


@pytest.mark.parametrize(
    "body",
    [
        {"task": "free", "message": "任意のプロンプト"},
        {"task": "chat", "message": "あ" * 501},
        {"task": "analyze", "earthquake": {**EARTHQUAKE, "shindo": "9"}},
        {"task": "analyze", "earthquake": {**EARTHQUAKE, "location": "x" * 61}},
        {"task": "analyze", "earthquake": {**EARTHQUAKE, "lat": 0}},
        {"task": "analyze"},
        {"task": "chat", "message": "   "},
    ],
    ids=["unknown-task", "chat-too-long", "bad-shindo", "location-too-long", "out-of-japan", "analyze-without-earthquake", "blank-chat"],
)
def test_rejects_invalid_requests(fake_gemini, body):
    response = post_ai(body)
    assert response.status_code == 422
    assert fake_gemini.calls == []


# ----------------- /api/ai: 回数制限 -----------------


def test_rate_limit_per_ip(fake_gemini, monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MINUTE", 2)
    assert post_ai({"task": "report"}).status_code == 200
    assert post_ai({"task": "report"}).status_code == 200
    limited = post_ai({"task": "report"})
    assert limited.status_code == 429
    assert limited.json()["detail"] == main.MSG_RATE_LIMITED
    # 別の接続元は制限されない
    assert post_ai({"task": "report"}, ip="203.0.113.2").status_code == 200


def test_rate_limit_ignores_spoofed_forwarded_for(fake_gemini, monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MINUTE", 1)
    assert post_ai({"task": "report"}, ip="1.1.1.1, 203.0.113.9").status_code == 200
    # 先頭の値を変えても、末尾（実際の接続元）が同じなら同じ利用者として数える
    assert post_ai({"task": "report"}, ip="2.2.2.2, 203.0.113.9").status_code == 429


# ----------------- /api/ai: Gemini のエラー -----------------


def test_quota_error_returns_spend_cap_message(fake_gemini):
    fake_gemini.responses = [genai_errors.ClientError(429, {"error": {"message": "quota exceeded"}})]
    response = post_ai({"task": "report"})
    assert response.status_code == 503
    assert response.json()["detail"] == main.MSG_QUOTA
    assert len(fake_gemini.calls) == 1  # 上限による停止は再試行しない


def test_client_error_is_not_retried_and_hides_details(fake_gemini):
    fake_gemini.responses = [genai_errors.ClientError(400, {"error": {"message": "API key not valid"}})]
    response = post_ai({"task": "report"})
    assert response.status_code == 502
    assert response.json()["detail"] == main.MSG_UNAVAILABLE
    assert "API key" not in response.text
    assert len(fake_gemini.calls) == 1


def test_server_error_is_retried(fake_gemini):
    fake_gemini.responses = [genai_errors.ServerError(503, {"error": {"message": "overloaded"}}), "再試行で成功"]
    response = post_ai({"task": "report"})
    assert response.status_code == 200
    assert response.json() == {"text": "再試行で成功"}
    assert len(fake_gemini.calls) == 2


def test_server_error_gives_up_after_three_attempts(fake_gemini):
    fake_gemini.responses = [genai_errors.ServerError(500, {"error": {"message": "internal"}})] * 3
    response = post_ai({"task": "report"})
    assert response.status_code == 502
    assert len(fake_gemini.calls) == 3


def test_missing_api_key_returns_503(monkeypatch):
    monkeypatch.setattr(main, "_gemini_client", None)
    response = post_ai({"task": "report"})
    assert response.status_code == 503
    assert response.json()["detail"] == main.MSG_UNAVAILABLE


# ----------------- 地震データの絞り込み -----------------


def _p2p_item(time, max_scale, issue_type="DetailScale", name="茨城県南部"):
    return {
        "id": f"id-{time}",
        "issue": {"type": issue_type},
        "earthquake": {
            "time": time,
            "maxScale": max_scale,
            "hypocenter": {"name": name, "magnitude": 5.5, "latitude": 36.1, "longitude": 140.0},
        },
    }


def test_parse_quakes_filters_like_the_html():
    items = [
        _p2p_item("2026/08/23 02:00:00", 50),
        _p2p_item("2026/08/01 21:47:00", 70, name="熊本県熊本地方"),
        _p2p_item("2026/07/01 10:00:00", 40),  # 震度4は除外
        _p2p_item("2025/12/31 23:59:00", 60),  # 2025年は除外
        _p2p_item("2026/06/01 12:00:00", 55, issue_type="ScalePrompt"),  # 速報は除外
        _p2p_item("2026/08/23 02:00:00", 50),  # 同じ時刻の重複は除外
    ]
    quakes = main._parse_quakes(items)
    assert [q["time"] for q in quakes] == ["2026年08月23日 02時00分頃", "2026年08月01日 21時47分頃"]
    assert quakes[1]["shindo"] == "7"
    assert quakes[0]["shortTime"] == "08/23 02:00"

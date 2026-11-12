"""ブラウザ（web/earthquake_map.html）のスモークテスト。

pytest -m browser で実行する。Tailwind CSS と Leaflet を CDN から読み込むため、インターネット接続が必要。
Gemini と P2P地震情報への通信は横取りし、APIキーは使わない。
"""

import json
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from playwright.sync_api import Page, expect

from server import main

pytestmark = pytest.mark.browser

HTML_FILE_URL = (Path(__file__).resolve().parent.parent / "web" / "earthquake_map.html").as_uri()
GEMINI_URL_PATTERN = "https://generativelanguage.googleapis.com/**"
DUMMY_KEY = "dummy-test-key"


@pytest.fixture(scope="module")
def live_server():
    """テスト用にサーバーを別スレッドで起動する。Gemini などの偽物は conftest.py で差し替える。"""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(autouse=True)
def stub_external_requests(page: Page):
    """地図タイルは読み込まず、P2P地震情報は空のデータを返す（表示は初期データで行われる）。"""
    page.route("https://cyberjapandata.gsi.go.jp/**", lambda route: route.abort())
    page.route("https://api.p2pquake.net/**", lambda route: route.fulfill(json=[]))


def open_ai_tab(page: Page, url: str) -> None:
    page.goto(url)
    page.wait_for_load_state("load")
    page.click("#tab-ai")


def send_chat(page: Page, message: str = "家具の固定方法は？") -> None:
    page.fill("#ai-chat-input", message)
    page.click("#btn-send-chat")


def gemini_response(text: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def storage(page: Page) -> dict:
    return page.evaluate(
        "() => ({session: sessionStorage.getItem('geminiApiKey'), local: localStorage.getItem('geminiApiKey')})"
    )


# ----------------- ①② http(s):// で開いた場合 -----------------


def test_server_mode_calls_api_instead_of_gemini(page: Page, live_server, fake_gemini):
    fake_gemini.responses = ["**防災**の回答です"]
    direct_calls = []
    page.route(GEMINI_URL_PATTERN, lambda route: (direct_calls.append(route.request.url), route.abort()))

    open_ai_tab(page, live_server)
    expect(page.locator("#byok-panel")).to_be_hidden()

    with page.expect_request("**/api/ai") as request_info:
        send_chat(page)
    assert request_info.value.post_data_json == {"task": "chat", "message": "家具の固定方法は？"}

    expect(page.locator("#ai-output strong")).to_have_text("防災")
    expect(page.locator("#ai-status")).to_have_text("チャット回答完了")
    assert direct_calls == []  # ブラウザから Gemini を直接呼ばない


def test_server_mode_shows_server_error_message(page: Page, live_server, monkeypatch):
    monkeypatch.setattr(main, "_gemini_client", None)
    open_ai_tab(page, live_server)
    send_chat(page)
    expect(page.locator("#ai-output")).to_contain_text(main.MSG_UNAVAILABLE)


def test_ai_output_is_html_escaped(page: Page, live_server, fake_gemini):
    fake_gemini.responses = ['<img src=x onerror="window.__xss = true">回答']
    open_ai_tab(page, live_server)
    send_chat(page)
    expect(page.locator("#ai-output")).to_contain_text("<img src=x")
    assert page.locator("#ai-output img").count() == 0
    assert page.evaluate("() => window.__xss") is None


# ----------------- ③ file:// で開いた場合（BYOK） -----------------


def test_file_mode_requires_key(page: Page):
    open_ai_tab(page, HTML_FILE_URL)
    expect(page.locator("#byok-panel")).to_be_visible()
    expect(page.locator("#byok-status")).to_have_text("未設定")
    send_chat(page)
    expect(page.locator("#ai-output")).to_contain_text("Gemini APIキーが設定されていません")


def test_file_mode_sends_key_in_header(page: Page):
    captured = []

    def handle(route):
        captured.append(route.request)
        route.fulfill(json=gemini_response("ローカルの回答"))

    page.route(GEMINI_URL_PATTERN, handle)
    open_ai_tab(page, HTML_FILE_URL)

    page.fill("#byok-input", DUMMY_KEY)
    page.click("#byok-save")
    expect(page.locator("#byok-status")).to_have_text("設定済み")
    expect(page.locator("#byok-input")).to_have_value("")
    assert storage(page) == {"session": DUMMY_KEY, "local": None}

    send_chat(page)
    expect(page.locator("#ai-output")).to_contain_text("ローカルの回答")
    request = captured[0]
    assert request.headers["x-goog-api-key"] == DUMMY_KEY
    assert "key=" not in request.url  # キーを URL に含めない
    payload = json.loads(request.post_data)
    assert payload["contents"][0]["parts"][0]["text"] == "家具の固定方法は？"
    assert payload["generationConfig"]["thinkingConfig"]["thinkingLevel"] == "LOW"


def test_file_mode_falls_back_to_lite_model_when_busy(page: Page):
    urls = []

    def handle(route):
        urls.append(route.request.url)
        if len(urls) < 3:
            route.fulfill(status=503, json={})
        else:
            route.fulfill(json=gemini_response("予備のモデルの回答"))

    page.route(GEMINI_URL_PATTERN, handle)
    open_ai_tab(page, HTML_FILE_URL)
    page.fill("#byok-input", DUMMY_KEY)
    page.click("#byok-save")
    send_chat(page)
    expect(page.locator("#ai-output")).to_contain_text("予備のモデルの回答", timeout=10000)
    models = [url.split("/models/")[1].split(":")[0] for url in urls]
    assert models == [main.GEMINI_MODEL, main.GEMINI_MODEL, main.GEMINI_FALLBACK_MODEL]


def test_file_mode_deadline_goes_straight_to_fallback(page: Page):
    urls = []

    def handle(route):
        urls.append(route.request.url)
        if len(urls) == 1:
            route.fulfill(status=504, json={})
        else:
            route.fulfill(json=gemini_response("予備のモデルの回答"))

    page.route(GEMINI_URL_PATTERN, handle)
    open_ai_tab(page, HTML_FILE_URL)
    page.fill("#byok-input", DUMMY_KEY)
    page.click("#byok-save")
    send_chat(page)
    expect(page.locator("#ai-output")).to_contain_text("予備のモデルの回答")
    models = [url.split("/models/")[1].split(":")[0] for url in urls]
    assert models == [main.GEMINI_MODEL, main.GEMINI_FALLBACK_MODEL]


def test_file_mode_invalid_key_is_not_retried(page: Page):
    calls = []
    page.route(GEMINI_URL_PATTERN, lambda route: (calls.append(1), route.fulfill(status=400, json={})))
    open_ai_tab(page, HTML_FILE_URL)
    page.fill("#byok-input", DUMMY_KEY)
    page.click("#byok-save")
    send_chat(page)
    expect(page.locator("#ai-output")).to_contain_text("APIキーが正しいか確認してください")
    assert len(calls) == 1


def test_file_mode_remember_and_clear_key(page: Page):
    open_ai_tab(page, HTML_FILE_URL)
    page.fill("#byok-input", DUMMY_KEY)
    page.check("#byok-remember")
    page.click("#byok-save")
    assert storage(page) == {"session": None, "local": DUMMY_KEY}

    page.click("#byok-clear")
    expect(page.locator("#byok-status")).to_have_text("未設定")
    assert storage(page) == {"session": None, "local": None}

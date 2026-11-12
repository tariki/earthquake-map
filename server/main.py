"""地震プロットマップの配信と、AI機能（Gemini）の中継を行うサーバー。

Gemini APIキーは環境変数 GEMINI_API_KEY から読む。Cloud Run では Secret Manager から渡す。
ブラウザから任意のプロンプトは受け付けず、プロンプトはすべてこのサーバーで組み立てる。
設計の詳細は docs/architecture.md を参照。
"""

import asyncio
import json
import logging
import os
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("earthquake-map")

# ----------------- 設定（環境変数で変更可能） -----------------

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", "4096"))
GEMINI_TIMEOUT_MS = int(os.environ.get("GEMINI_TIMEOUT_MS", "60000"))
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "10"))
QUAKE_CACHE_SECONDS = int(os.environ.get("QUAKE_CACHE_SECONDS", "600"))
RETRY_BASE_DELAY = float(os.environ.get("RETRY_BASE_DELAY", "1.0"))
HTML_PATH = Path(os.environ.get("HTML_PATH", Path(__file__).resolve().parent.parent / "web" / "earthquake_map.html"))

P2P_QUAKE_URL = "https://api.p2pquake.net/v2/jma/quake?limit=100&since_date=20260101&min_scale=45"
SCALE_MAP = {45: "5弱", 50: "5強", 55: "6弱", 60: "6強", 70: "7"}
SCALE_CLASS_MAP = {45: "5-minus", 50: "5-plus", 55: "6-minus", 60: "6-plus", 70: "7"}

# 利用者に返すメッセージ（詳細はサーバーログにだけ残す）
MSG_UNAVAILABLE = "AI機能は現在利用できません。しばらく時間をおいて再試行してください。"
MSG_QUOTA = "AI機能は一時的に利用できません（今月の利用上限に達した可能性があります）。"
MSG_RATE_LIMITED = "リクエストが多すぎます。1分ほど待ってから再試行してください。"

SYSTEM_PROMPT_TEMPLATE = """あなたは優秀な防災専門家および地震学者「防災AIアシスタント」です。
ユーザーから提供された「2026年以降の震度5以上の地震データ」を前提知識として持っています。
回答は必ず日本語で行い、専門的でありながら一般市民にとって分かりやすく、かつ極めて実践的な防災アドバイスを交えて回答してください。
適度に適切な絵文字を使い、読みやすくマークダウン形式（箇条書き、太字など）に整形してアウトプットを構築してください。

【前提とする地震データ一覧（2026年以降）】
{data}
"""

REPORT_PROMPT = """提供された震度5以上の地震データをマクロに分析し、「日本における最近の地震活動トレンドレポート」を書き上げてください。
以下の観点を含めてください：
1. 活動概観（太平洋側、日本海側、内陸など、どのブロックにどのような規模の活動が集中したか。特に三陸沖や岩手県沖などの活動の意義）
2. 特徴的な多発エリア（例：島根県東部、長野県北部、茨城県南部など複数回発生している震源地域が示唆すること）
3. 市民が今すぐ行うべき実践的な防災アクションプラン（備蓄の見直し、家具固定、家族での連絡ルールの確認など具体的なステップ）

全体で450〜600文字程度で、分かりやすいビジネス/アカデミック報告スタイルで作成してください。"""

ANALYZE_PROMPT_TEMPLATE = """発生: {time}、震源: {location}、規模: M{m}、最大震度: {shindo}について解説してください。
1. 地理的および震源のメカニズム的特徴（例: 沈み込むプレート境界など、この震源周辺の日本地震科学的背景）
2. この規模（震度やマグニチュード）の地震が起きると、一般家屋やライフライン、周辺インフラにどのような具体的な影響が生じうるか
3. その地域や類似地域に住む人々が、発生後数日間および日常的に取るべき警戒アクション（余震・土砂災害・避難ルートの確認など）

300文字〜400文字程度で、非常に心強くて有益なアドバイスとして簡潔にまとめてください。"""

# ----------------- リクエストの型 -----------------


class EarthquakeInput(BaseModel):
    time: str = Field(min_length=1, max_length=40)
    location: str = Field(min_length=1, max_length=60)
    m: float = Field(ge=-1, le=10)  # P2P地震情報ではマグニチュード不明を -1 で表す
    shindo: Literal["5弱", "5強", "6弱", "6強", "7"]
    lat: float = Field(ge=20, le=50)
    lng: float = Field(ge=120, le=155)


class AIRequest(BaseModel):
    task: Literal["report", "analyze", "chat"]
    earthquake: EarthquakeInput | None = None
    message: str | None = Field(default=None, max_length=500)


class AIResponse(BaseModel):
    text: str


# ----------------- 地震データ（P2P地震情報 API） -----------------

_quake_cache: list[dict] = []
_quake_cache_at = 0.0
_quake_lock = asyncio.Lock()


def _parse_quakes(items: list[dict]) -> list[dict]:
    """HTML の fetchLatestEarthquakes と同じ条件（震度5弱以上・2026年以降）で絞り込む。"""
    quakes = []
    for item in items:
        eq = item.get("earthquake") or {}
        hypo = eq.get("hypocenter")
        if not hypo or (item.get("issue") or {}).get("type") != "DetailScale":
            continue
        max_scale = eq.get("maxScale")
        if not max_scale or max_scale < 45:
            continue
        try:
            dt = datetime.strptime(eq["time"], "%Y/%m/%d %H:%M:%S")
        except (KeyError, ValueError):
            continue
        if dt.year < 2026:
            continue
        quakes.append({
            "id": item.get("id") or f"api-{eq['time']}",
            "time": dt.strftime("%Y年%m月%d日 %H時%M分頃"),
            "shortTime": dt.strftime("%m/%d %H:%M"),
            "location": hypo.get("name"),
            "m": hypo.get("magnitude"),
            "shindo": SCALE_MAP.get(max_scale, "5弱"),
            "shindoClass": SCALE_CLASS_MAP.get(max_scale, "5-minus"),
            "lat": hypo.get("latitude"),
            "lng": hypo.get("longitude"),
        })

    # 発生時刻の重複を排除し、新しい順に並べる
    unique = {q["time"]: q for q in reversed(quakes)}
    return sorted(unique.values(), key=lambda q: q["time"], reverse=True)


async def get_earthquakes() -> list[dict]:
    """地震データを返す。キャッシュが古ければ取り直し、取得に失敗したら直前のキャッシュを使う。"""
    global _quake_cache, _quake_cache_at
    async with _quake_lock:
        if time.monotonic() - _quake_cache_at < QUAKE_CACHE_SECONDS and _quake_cache_at:
            return _quake_cache
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(P2P_QUAKE_URL)
                response.raise_for_status()
            _quake_cache = _parse_quakes(response.json())
            _quake_cache_at = time.monotonic()
        except (httpx.HTTPError, ValueError):
            logger.exception("P2P地震情報 API からの取得に失敗しました")
        return _quake_cache


# ----------------- 回数制限（インスタンス内のメモリで数える簡易版） -----------------

_request_log: dict[str, deque] = defaultdict(deque)


def client_ip(request: Request) -> str:
    # Cloud Run では Google のフロントエンドが実際の接続元を X-Forwarded-For の末尾に追加する。
    # 先頭の値は利用者が自由に送れるため使わない。
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def is_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    log = _request_log[ip]
    while log and now - log[0] > 60:
        log.popleft()
    if len(log) >= RATE_LIMIT_PER_MINUTE:
        return True
    log.append(now)
    return False


# ----------------- Gemini 呼び出し -----------------

_gemini_client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
) if GEMINI_API_KEY else None


async def call_gemini(prompt: str, earthquakes: list[dict]) -> str:
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(data=json.dumps(earthquakes, ensure_ascii=False, indent=2))
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    delay = RETRY_BASE_DELAY
    for attempt in range(3):
        try:
            response = await _gemini_client.aio.models.generate_content(
                model=GEMINI_MODEL, contents=prompt, config=config
            )
            if response.text:
                return response.text
            logger.warning("Gemini から空の応答が返りました: %s", response)
            raise HTTPException(status_code=502, detail=MSG_UNAVAILABLE)
        except genai_errors.APIError as error:
            logger.error("Gemini API エラー (code=%s): %s", error.code, error.message)
            if error.code == 429:
                # spend cap やティア上限による停止を含む。再試行しても回復しない
                raise HTTPException(status_code=503, detail=MSG_QUOTA) from error
            if error.code < 500 or attempt == 2:
                raise HTTPException(status_code=502, detail=MSG_UNAVAILABLE) from error
        await asyncio.sleep(delay)
        delay *= 2
    raise HTTPException(status_code=502, detail=MSG_UNAVAILABLE)


# ----------------- ルーティング -----------------

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(HTML_PATH, media_type="text/html")


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict:
    return {"status": "ok"}


@app.post("/api/ai", response_model=AIResponse)
async def ai(body: AIRequest, request: Request) -> AIResponse:
    if _gemini_client is None:
        logger.error("GEMINI_API_KEY が設定されていません")
        raise HTTPException(status_code=503, detail=MSG_UNAVAILABLE)

    if is_rate_limited(client_ip(request)):
        raise HTTPException(status_code=429, detail=MSG_RATE_LIMITED)

    if body.task == "report":
        prompt = REPORT_PROMPT
    elif body.task == "analyze":
        if body.earthquake is None:
            raise HTTPException(status_code=422, detail="分析する地震の情報がありません。")
        prompt = ANALYZE_PROMPT_TEMPLATE.format(**body.earthquake.model_dump())
    else:
        message = (body.message or "").strip()
        if not message:
            raise HTTPException(status_code=422, detail="質問を入力してください。")
        prompt = message

    earthquakes = await get_earthquakes()
    return AIResponse(text=await call_gemini(prompt, earthquakes))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))

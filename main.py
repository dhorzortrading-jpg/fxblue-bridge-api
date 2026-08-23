from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime, timezone
from collections import defaultdict
from typing import Optional, List, Dict, Any
import os
import json
import requests
import psycopg
from psycopg.rows import dict_row

app = FastAPI(
    title="Trading Research Market Intelligence API",
    version="3.0.0",
    description="OANDA market intelligence, currency strength, and trade-learning API."
)

OANDA_BASE_URL = "https://api-fxpractice.oanda.com"

OANDA_API_TOKEN = os.getenv("OANDA_API_TOKEN")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
DATABASE_URL = os.getenv("DATABASE_URL")

SUPPORTED_TIMEFRAMES = [
    "M1",
    "M5",
    "M15",
    "M30",
    "H1",
    "H4",
    "D",
    "W"
]

PAIRS = [
    "EUR_USD",
    "GBP_USD",
    "USD_JPY",
    "GBP_JPY",
    "AUD_USD",
    "USD_CAD",
    "NZD_USD",
    "AUD_JPY"
]


# -------------------------------------------------
# DATABASE
# -------------------------------------------------

def get_db():
    if not DATABASE_URL:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL is not configured"
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )


def initialize_database():
    if not DATABASE_URL:
        return

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id SERIAL PRIMARY KEY,

                    trade_id VARCHAR(100) UNIQUE NOT NULL,

                    symbol VARCHAR(30) NOT NULL,
                    direction VARCHAR(10),
                    trade_status VARCHAR(30),

                    trade_date VARCHAR(30),
                    session VARCHAR(30),
                    execution_timeframe VARCHAR(20),

                    setup_quality_score NUMERIC,
                    execution_quality_score NUMERIC,

                    entry_price NUMERIC,
                    stop_loss NUMERIC,
                    tp1 NUMERIC,
                    tp2 NUMERIC,
                    tp3 NUMERIC,

                    planned_rr NUMERIC,
                    risk_percent NUMERIC,

                    outcome VARCHAR(30),
                    r_multiple NUMERIC,
                    profit_loss NUMERIC,

                    notes TEXT,
                    lesson TEXT,

                    setup_data JSONB,
                    context_data JSONB,
                    review_data JSONB,
                    references_data JSONB,

                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

        conn.commit()


@app.on_event("startup")
def startup_event():
    initialize_database()


# -------------------------------------------------
# MODELS
# -------------------------------------------------

class TradeIngestRequest(BaseModel):
    trade_id: str
    symbol: str

    direction: Optional[str] = None
    trade_status: Optional[str] = None

    trade_date: Optional[str] = None
    session: Optional[str] = None
    execution_timeframe: Optional[str] = None

    setup_quality_score: Optional[float] = None
    execution_quality_score: Optional[float] = None

    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    tp3: Optional[float] = None

    planned_rr: Optional[float] = None
    risk_percent: Optional[float] = None

    outcome: Optional[str] = None
    r_multiple: Optional[float] = None
    profit_loss: Optional[float] = None

    notes: Optional[str] = None
    lesson: Optional[str] = None

    setup_data: Optional[Dict[str, Any]] = None
    context_data: Optional[Dict[str, Any]] = None
    review_data: Optional[Dict[str, Any]] = None
    references_data: Optional[Dict[str, Any]] = None


# -------------------------------------------------
# BASIC ENDPOINTS
# -------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Trading Research Market Intelligence API",
        "version": "3.0.0"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "oanda_token_configured": bool(OANDA_API_TOKEN),
        "oanda_account_configured": bool(OANDA_ACCOUNT_ID),
        "database_configured": bool(DATABASE_URL),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# -------------------------------------------------
# OANDA
# -------------------------------------------------

def get_headers():
    if not OANDA_API_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="OANDA_API_TOKEN is not configured"
        )

    return {
        "Authorization": f"Bearer {OANDA_API_TOKEN}",
        "Content-Type": "application/json"
    }


@app.get("/oanda/account")
def get_oanda_account():
    if not OANDA_ACCOUNT_ID:
        raise HTTPException(
            status_code=500,
            detail="OANDA_ACCOUNT_ID is not configured"
        )

    url = f"{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/summary"

    try:
        response = requests.get(
            url,
            headers=get_headers(),
            timeout=20
        )

        response.raise_for_status()

        data = response.json()
        account = data.get("account", {})

        return {
            "source": "OANDA v20 Practice API",
            "account_id": account.get("id"),
            "currency": account.get("currency"),
            "balance": account.get("balance"),
            "NAV": account.get("NAV"),
            "unrealizedPL": account.get("unrealizedPL"),
            "marginUsed": account.get("marginUsed"),
            "marginAvailable": account.get("marginAvailable"),
            "openTradeCount": account.get("openTradeCount"),
            "openPositionCount": account.get("openPositionCount"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OANDA account request failed: {str(exc)}"
        )


@app.get("/market-price")
def market_price(
    instrument: str = Query(default="XAU_USD")
):
    if not OANDA_ACCOUNT_ID:
        raise HTTPException(
            status_code=500,
            detail="OANDA_ACCOUNT_ID is not configured"
        )

    instrument = instrument.upper()

    url = (
        f"{OANDA_BASE_URL}/v3/accounts/"
        f"{OANDA_ACCOUNT_ID}/pricing"
    )

    params = {
        "instruments": instrument
    }

    try:
        response = requests.get(
            url,
            headers=get_headers(),
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()
        prices = data.get("prices", [])

        if not prices:
            raise HTTPException(
                status_code=404,
                detail=f"No pricing data returned for {instrument}"
            )

        price = prices[0]

        bids = price.get("bids", [])
        asks = price.get("asks", [])

        bid = float(bids[0]["price"]) if bids else None
        ask = float(asks[0]["price"]) if asks else None

        spread = None
        midpoint = None

        if bid is not None and ask is not None:
            spread = ask - bid
            midpoint = (bid + ask) / 2

        return {
            "source": "OANDA v20 Practice API",
            "instrument": instrument,
            "bid": bid,
            "ask": ask,
            "spread": round(spread, 6) if spread is not None else None,
            "midpoint": round(midpoint, 6) if midpoint is not None else None,
            "tradeable": price.get("tradeable"),
            "timestamp": price.get("time")
        }

    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OANDA pricing request failed: {str(exc)}"
        )


def get_oanda_candles(
    instrument: str,
    granularity: str,
    count: int
):
    url = (
        f"{OANDA_BASE_URL}/v3/instruments/"
        f"{instrument}/candles"
    )

    params = {
        "granularity": granularity,
        "count": count,
        "price": "M"
    }

    try:
        response = requests.get(
            url,
            headers=get_headers(),
            params=params,
            timeout=20
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OANDA candle request failed for {instrument}: {str(exc)}"
        )


@app.get("/market-candles")
def market_candles(
    instrument: str = Query(default="XAU_USD"),
    granularity: str = Query(default="M15"),
    count: int = Query(default=100, ge=1, le=500)
):
    instrument = instrument.upper()
    granularity = granularity.upper()

    if granularity not in SUPPORTED_TIMEFRAMES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Unsupported timeframe",
                "supported": SUPPORTED_TIMEFRAMES
            }
        )

    data = get_oanda_candles(
        instrument,
        granularity,
        count
    )

    output = []

    for candle in data.get("candles", []):
        mid = candle.get("mid")

        if not mid:
            continue

        output.append({
            "time": candle.get("time"),
            "complete": candle.get("complete"),
            "volume": candle.get("volume"),
            "open": float(mid["o"]),
            "high": float(mid["h"]),
            "low": float(mid["l"]),
            "close": float(mid["c"])
        })

    return {
        "source": "OANDA v20 Practice API",
        "instrument": instrument,
        "granularity": granularity,
        "count": len(output),
        "candles": output
    }


# -------------------------------------------------
# CURRENCY STRENGTH
# -------------------------------------------------

def calculate_pair_change(
    instrument: str,
    granularity: str,
    lookback: int
):
    data = get_oanda_candles(
        instrument,
        granularity,
        lookback + 5
    )

    candles = [
        candle
        for candle in data.get("candles", [])
        if candle.get("complete")
        and candle.get("mid")
    ]

    if len(candles) < 2:
        return None

    candles = candles[-lookback:]

    start_price = float(candles[0]["mid"]["c"])
    end_price = float(candles[-1]["mid"]["c"])

    if start_price == 0:
        return None

    change_percent = (
        (end_price - start_price)
        / start_price
    ) * 100

    return {
        "instrument": instrument,
        "start": start_price,
        "end": end_price,
        "change_percent": round(change_percent, 5)
    }


@app.get("/currency-strength")
def currency_strength(
    granularity: str = Query(default="H1"),
    lookback: int = Query(default=20, ge=2, le=200)
):
    granularity = granularity.upper()

    if granularity not in SUPPORTED_TIMEFRAMES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Unsupported timeframe",
                "supported": SUPPORTED_TIMEFRAMES
            }
        )

    strength_points = defaultdict(list)
    pair_results = []

    for pair in PAIRS:
        result = calculate_pair_change(
            pair,
            granularity,
            lookback
        )

        if result is None:
            continue

        base, quote = pair.split("_")
        change = result["change_percent"]

        strength_points[base].append(change)
        strength_points[quote].append(-change)

        pair_results.append(result)

    raw_strength = {}

    for currency, values in strength_points.items():
        if values:
            raw_strength[currency] = (
                sum(values) / len(values)
            )

    if not raw_strength:
        raise HTTPException(
            status_code=502,
            detail="Unable to calculate currency strength"
        )

    maximum = max(
        abs(value)
        for value in raw_strength.values()
    )

    ranking = []

    for currency, value in raw_strength.items():
        score = 0

        if maximum != 0:
            score = (
                value / maximum
            ) * 100

        ranking.append({
            "currency": currency,
            "raw_strength": round(value, 5),
            "score": round(score, 2)
        })

    ranking.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return {
        "source": "OANDA v20 Practice API",
        "method": "Relative percentage-change currency strength",
        "granularity": granularity,
        "lookback_candles": lookback,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ranking": ranking,
        "pair_changes": pair_results
    }


@app.get("/currency-strength/multi-timeframe")
def multi_timeframe_currency_strength(
    lookback: int = Query(default=20, ge=2, le=100)
):
    results = {}

    for timeframe in SUPPORTED_TIMEFRAMES:
        strength_points = defaultdict(list)

        try:
            for pair in PAIRS:
                result = calculate_pair_change(
                    pair,
                    timeframe,
                    lookback
                )

                if result is None:
                    continue

                base, quote = pair.split("_")
                change = result["change_percent"]

                strength_points[base].append(change)
                strength_points[quote].append(-change)

            raw_strength = {}

            for currency, values in strength_points.items():
                if values:
                    raw_strength[currency] = (
                        sum(values) / len(values)
                    )

            if not raw_strength:
                results[timeframe] = []
                continue

            maximum = max(
                abs(value)
                for value in raw_strength.values()
            )

            ranking = []

            for currency, value in raw_strength.items():
                score = 0

                if maximum != 0:
                    score = (
                        value / maximum
                    ) * 100

                ranking.append({
                    "currency": currency,
                    "score": round(score, 2)
                })

            ranking.sort(
                key=lambda item: item["score"],
                reverse=True
            )

            results[timeframe] = ranking

        except Exception as exc:
            results[timeframe] = {
                "error": str(exc)
            }

    return {
        "source": "OANDA v20 Practice API",
        "lookback_candles": lookback,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "timeframes": results
    }


# -------------------------------------------------
# TRADE LEARNING
# -------------------------------------------------

@app.post("/trades/ingest")
def ingest_trade(trade: TradeIngestRequest):

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    INSERT INTO trades (
                        trade_id,
                        symbol,
                        direction,
                        trade_status,
                        trade_date,
                        session,
                        execution_timeframe,
                        setup_quality_score,
                        execution_quality_score,
                        entry_price,
                        stop_loss,
                        tp1,
                        tp2,
                        tp3,
                        planned_rr,
                        risk_percent,
                        outcome,
                        r_multiple,
                        profit_loss,
                        notes,
                        lesson,
                        setup_data,
                        context_data,
                        review_data,
                        references_data
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s
                    )
                    ON CONFLICT (trade_id)
                    DO UPDATE SET
                        symbol = EXCLUDED.symbol,
                        direction = EXCLUDED.direction,
                        trade_status = EXCLUDED.trade_status,
                        trade_date = EXCLUDED.trade_date,
                        session = EXCLUDED.session,
                        execution_timeframe = EXCLUDED.execution_timeframe,
                        setup_quality_score = EXCLUDED.setup_quality_score,
                        execution_quality_score = EXCLUDED.execution_quality_score,
                        entry_price = EXCLUDED.entry_price,
                        stop_loss = EXCLUDED.stop_loss,
                        tp1 = EXCLUDED.tp1,
                        tp2 = EXCLUDED.tp2,
                        tp3 = EXCLUDED.tp3,
                        planned_rr = EXCLUDED.planned_rr,
                        risk_percent = EXCLUDED.risk_percent,
                        outcome = EXCLUDED.outcome,
                        r_multiple = EXCLUDED.r_multiple,
                        profit_loss = EXCLUDED.profit_loss,
                        notes = EXCLUDED.notes,
                        lesson = EXCLUDED.lesson,
                        setup_data = EXCLUDED.setup_data,
                        context_data = EXCLUDED.context_data,
                        review_data = EXCLUDED.review_data,
                        references_data = EXCLUDED.references_data,
                        updated_at = NOW()
                    RETURNING *
                    """,
                    (
                        trade.trade_id,
                        trade.symbol.upper(),
                        trade.direction,
                        trade.trade_status,
                        trade.trade_date,
                        trade.session,
                        trade.execution_timeframe,
                        trade.setup_quality_score,
                        trade.execution_quality_score,
                        trade.entry_price,
                        trade.stop_loss,
                        trade.tp1,
                        trade.tp2,
                        trade.tp3,
                        trade.planned_rr,
                        trade.risk_percent,
                        trade.outcome,
                        trade.r_multiple,
                        trade.profit_loss,
                        trade.notes,
                        trade.lesson,
                        json.dumps(trade.setup_data or {}),
                        json.dumps(trade.context_data or {}),
                        json.dumps(trade.review_data or {}),
                        json.dumps(trade.references_data or {})
                    )
                )

                saved_trade = cur.fetchone()

            conn.commit()

        return {
            "status": "saved",
            "trade": saved_trade
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Trade ingestion failed: {str(exc)}"
        )


@app.get("/trades")
def get_trades(
    symbol: Optional[str] = None,
    outcome: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500)
):

    try:
        query = "SELECT * FROM trades"
        conditions = []
        values = []

        if symbol:
            conditions.append("symbol = %s")
            values.append(symbol.upper())

        if outcome:
            conditions.append("outcome = %s")
            values.append(outcome.upper())

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT %s"
        values.append(limit)

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(query, values)
                trades = cur.fetchall()

        return {
            "count": len(trades),
            "trades": trades
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Trade retrieval failed: {str(exc)}"
        )


@app.get("/trades/{trade_id}")
def get_trade(trade_id: str):

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT *
                    FROM trades
                    WHERE trade_id = %s
                    """,
                    (trade_id,)
                )

                trade = cur.fetchone()

        if not trade:
            raise HTTPException(
                status_code=404,
                detail="Trade not found"
            )

        return trade

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Trade retrieval failed: {str(exc)}"
        )


@app.get("/trades/stats/summary")
def trade_statistics():

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT
                        COUNT(*) AS total_trades,

                        COUNT(*) FILTER (
                            WHERE UPPER(outcome) = 'WIN'
                        ) AS wins,

                        COUNT(*) FILTER (
                            WHERE UPPER(outcome) = 'LOSS'
                        ) AS losses,

                        COUNT(*) FILTER (
                            WHERE UPPER(outcome) = 'BREAKEVEN'
                        ) AS breakeven,

                        AVG(r_multiple) AS average_r,

                        SUM(profit_loss) AS total_profit_loss

                    FROM trades
                """)

                stats = cur.fetchone()

        return stats

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Trade statistics failed: {str(exc)}"
        )
# ============================================================
# OANDA MULTI-TIMEFRAME MARKET DATA
# ============================================================

@app.get("/market-multitimeframe")
def get_market_multitimeframe(
    instrument: str = Query("EUR_USD"),
    count: int = Query(100, ge=10, le=500)
):
    """
    Retrieve OANDA candle data across all core analysis
    timeframes in one request.

    Timeframes:
    W, D, H4, H1, M30, M15, M5, M1
    """

    timeframes = [
        "W",
        "D",
        "H4",
        "H1",
        "M30",
        "M15",
        "M5",
        "M1",
    ]

    # Validate instrument if PAIRS is defined in this application.
    if instrument not in PAIRS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported instrument: {instrument}"
        )

    if not OANDA_API_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="OANDA API token is not configured"
        )

    headers = {
        "Authorization": f"Bearer {OANDA_API_TOKEN}",
        "Content-Type": "application/json",
    }

    results = {}

    for timeframe in timeframes:

        try:
            url = (
                f"{OANDA_BASE_URL}/v3/instruments/"
                f"{instrument}/candles"
            )

            params = {
                "granularity": timeframe,
                "count": count,
                "price": "M",
            }

            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=20,
            )

            if response.status_code != 200:
                results[timeframe] = {
                    "status": "error",
                    "http_status": response.status_code,
                    "error": response.text,
                }
                continue

            data = response.json()

            raw_candles = data.get("candles", [])

            candles = []

            for candle in raw_candles:

                midpoint = candle.get("mid", {})

                candles.append({
                    "time": candle.get("time"),
                    "complete": candle.get("complete"),
                    "volume": candle.get("volume"),
                    "open": midpoint.get("o"),
                    "high": midpoint.get("h"),
                    "low": midpoint.get("l"),
                    "close": midpoint.get("c"),
                })

            completed = [
                candle
                for candle in candles
                if candle.get("complete") is True
            ]

            results[timeframe] = {
                "status": "ok",
                "instrument": instrument,
                "granularity": timeframe,
                "requested_count": count,
                "returned_count": len(candles),
                "completed_count": len(completed),
                "first_timestamp": (
                    candles[0]["time"]
                    if candles else None
                ),
                "last_timestamp": (
                    candles[-1]["time"]
                    if candles else None
                ),
                "candles": candles,
            }

        except requests.RequestException as exc:

            results[timeframe] = {
                "status": "error",
                "granularity": timeframe,
                "error": str(exc),
            }

    successful = sum(
        1
        for result in results.values()
        if result.get("status") == "ok"
    )

    return {
        "source": "OANDA v20 Practice API",
        "instrument": instrument,
        "requested_candles_per_timeframe": count,
        "requested_timeframes": timeframes,
        "successful_timeframes": successful,
        "total_timeframes": len(timeframes),
        "all_timeframes_successful": successful == len(timeframes),
        "timeframes": results,
    }

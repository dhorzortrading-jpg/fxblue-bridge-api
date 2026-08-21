from fastapi import FastAPI, HTTPException, Query
from datetime import datetime, timezone
from collections import defaultdict
import os
import requests

app = FastAPI(
    title="Trading Research Market Intelligence API",
    version="2.0.0",
    description="OANDA-powered market intelligence and currency strength engine."
)

OANDA_BASE_URL = "https://api-fxpractice.oanda.com"

OANDA_API_TOKEN = os.getenv("OANDA_API_TOKEN")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")

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


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Trading Research Market Intelligence API",
        "version": "2.0.0"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "oanda_token_configured": bool(OANDA_API_TOKEN),
        "oanda_account_configured": bool(OANDA_ACCOUNT_ID),
        "timestamp": datetime.now(timezone.utc).isoformat()
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
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
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
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "timeframes": results
    }

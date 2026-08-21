from fastapi import FastAPI, HTTPException
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

app = FastAPI(
    title="FX Blue Market Data Bridge",
    version="1.0.0"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "FX Blue Market Data Bridge"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/fxblue/currency-strength")
def currency_strength():
    url = "https://publisher.fxblue.com/market-data/currency-strength"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=15
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve FX Blue currency strength"
        )

    soup = BeautifulSoup(response.text, "html.parser")

    text = soup.get_text(
        separator=" ",
        strip=True
    )

    return {
        "source": "FX Blue",
        "source_url": url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "raw_text": text
    }


@app.get("/fxblue/sentiment")
def trader_sentiment():
    url = "https://publisher.fxblue.com/market-data/tools/sentiment"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=15
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve FX Blue trader sentiment"
        )

    soup = BeautifulSoup(response.text, "html.parser")

    text = soup.get_text(
        separator=" ",
        strip=True
    )

    return {
        "source": "FX Blue",
        "source_url": url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "raw_text": text
    }

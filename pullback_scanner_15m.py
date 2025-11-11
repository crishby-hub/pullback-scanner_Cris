import pandas as pd
import numpy as np
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands
import os, requests

TICKER_FILE = "tickers.txt"
INTERVAL = "15m"
PERIOD = "10d"

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def add_indicators(df):
    c, v = df["Close"], df["Volume"]
    df["EMA20"] = EMAIndicator(c, 20).ema_indicator()
    df["EMA50"] = EMAIndicator(c, 50).ema_indicator()
    df["RSI"] = RSIIndicator(c, 14).rsi()
    df["VolMA20"] = v.rolling(20).mean()
    df["VolRel"] = v / (df["VolMA20"] + 1e-9)
    bb = BollingerBands(c, 20, 2)
    df["BB_H"], df["BB_L"] = bb.bollinger_hband(), bb.bollinger_lband()
    return df

def detect_pullback(ticker):
    df = yf.download(ticker, period=PERIOD, interval=INTERVAL, progress=False, auto_adjust=True)
    if df.empty:
        return None
    df = add_indicators(df)
    df["FromHigh"] = df["Close"] / df["Close"].cummax() - 1
    cond = (
        (df["EMA20"] > df["EMA50"]) &
        (df["RSI"].between(45, 60)) &
        (df["FromHigh"].between(-0.12, -0.05)) &
        (df["VolRel"] < 0.85)
    )
    pb = df[cond]
    if pb.empty:
        return None
    last = pb.iloc[-1]
    return {
        "Ticker": ticker,
        "Close": round(last.Close, 2),
        "RSI": round(last.RSI, 1),
        "Drop%": round(last.FromHigh * 100, 1)
    }

def scan_all():
    with open(TICKER_FILE, "r") as f:
        tickers = [t.strip() for t in f.readlines() if t.strip()]
    results = []
    for t in tickers:
        sig = detect_pullback(t)
        if sig:
            results.append(sig)
    return pd.DataFrame(results)

if __name__ == "__main__":
    df = scan_all()
    if df.empty:
        print("🔹 No pullback signals found.")
    else:
        print("🔍 눌림목 신호 감지:")
        print(df)
        if TG_BOT_TOKEN and TG_CHAT_ID:
            msg = "🔔 눌림목 신호 발생 종목:
" + "
".join(df["Ticker"])
            url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": TG_CHAT_ID, "text": msg})

"""
Pullback Scanner (15m)
- EMA20/EMA50 추세 + RSI 쿨다운 + 고점대비 -5~-12% + 거래량 건조 조건
- 깃허브 액션에서 30분마다 실행 가능
- 텔레그램 알림: TG_BOT_TOKEN, TG_CHAT_ID (리포지토리 Secrets/Environment에 저장)
"""

import pandas as pd
import numpy as np
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands
import os
import requests

# ===== 기본 설정 =====
TICKER_FILE = "tickers.txt"   # 루트에 배치
INTERVAL = "15m"
PERIOD = "10d"

# GitHub Secrets / Environment에서 주입
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")


# ===== 보조지표 계산 =====
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    c = df["Close"]
    v = df["Volume"]
    df["EMA20"] = EMAIndicator(c, 20).ema_indicator()
    df["EMA50"] = EMAIndicator(c, 50).ema_indicator()
    df["RSI"] = RSIIndicator(c, 14).rsi()
    df["VolMA20"] = v.rolling(20).mean()
    df["VolRel"] = v / (df["VolMA20"] + 1e-9)
    bb = BollingerBands(close=c, window=20, window_dev=2)
    df["BB_H"] = bb.bollinger_hband()
    df["BB_L"] = bb.bollinger_lband()
    return df


# ===== 눌림목 감지 (단일 티커) =====
def detect_pullback(ticker: str):
    try:
        df = yf.download(
            ticker, period=PERIOD, interval=INTERVAL,
            progress=False, auto_adjust=True
        )
    except Exception as e:
        print(f"[{ticker}] download error: {e}")
        return None

    if df is None or df.empty:
        print(f"[{ticker}] no data")
        return None

    df = add_indicators(df)
    # 최근 고점 대비 낙폭
    df["FromHigh"] = df["Close"] / df["Close"].cummax() - 1.0

    # 눌림목 후보 조건
    cond = (
        (df["EMA20"] > df["EMA50"]) &                # 상승 추세
        (df["RSI"].between(45, 60)) &               # 과열 식힘
        (df["FromHigh"].between(-0.12, -0.05)) &    # 고점대비 -5% ~ -12%
        (df["VolRel"] < 0.85)                       # 거래량 건조
    )

    pb = df[cond]
    if pb.empty:
        return None

    last = pb.iloc[-1]
    return {
        "Ticker": ticker,
        "Close": float(round(last["Close"], 2)),
        "RSI": float(round(last["RSI"], 1)),
        "Drop%": float(round(last["FromHigh"] * 100.0, 1))
    }


# ===== 전체 스캔 =====
def scan_all() -> pd.DataFrame:
    if not os.path.exists(TICKER_FILE):
        raise FileNotFoundError(f"{TICKER_FILE} not found in repo root")

    with open(TICKER_FILE, "r", encoding="utf-8") as f:
        tickers = [t.strip() for t in f if t.strip()]

    results = []
    for t in tickers:
        sig = detect_pullback(t)
        if sig:
            results.append(sig)

    if not results:
        return pd.DataFrame(columns=["Ticker", "Close", "RSI", "Drop%"])

    df = pd.DataFrame(results)
    # 덜 깊게 눌린 순으로 정렬(혹은 스코어링 로직으로 교체 가능)
    df = df.sort_values("Drop%", ascending=False).reset_index(drop=True)
    return df


# ===== 텔레그램 전송 =====
def send_telegram(text: str):
    if not (TG_BOT_TOKEN and TG_CHAT_ID):
        print("Telegram skipped (missing TG_BOT_TOKEN or TG_CHAT_ID)")
        return
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": TG_CHAT_ID, "text": text}, timeout=15)
        print(f"Telegram status: {r.status_code}")
    except Exception as e:
        print(f"Telegram send error: {e}")


# ===== 메인 =====
if __name__ == "__main__":
    df = scan_all()

    if df.empty:
        print("🔹 No pullback signals found.")
        msg = "🔎 조건에 맞는 눌림목 신호가 없습니다."
    else:
        print("🔍 눌림목 신호 감지:")
        print(df)
        tickers_list = "\n".join(df["Ticker"].astype(str).tolist())
        msg = "🔔 눌림목 신호 발생 종목:\n" + tickers_list

    # CSV로 결과 저장(옵션)
    try:
        df.to_csv("pullback_15m_signals.csv", index=False)
        print("Saved: pullback_15m_signals.csv")
    except Exception as e:
        print(f"CSV save error: {e}")

    # 텔레그램 알림
    send_telegram(msg)

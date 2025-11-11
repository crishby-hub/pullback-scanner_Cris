# Pullback Scanner (눌림목 자동 탐지기)

이 프로젝트는 주식 차트에서 **눌림목(pullback)** 패턴을 자동으로 탐지하고  
30분마다 실행되어 텔레그램으로 신호를 보내주는 시스템입니다.

## ⚙️ 주요 기능
- 15분봉 기준 자동 분석
- EMA20/EMA50, RSI, 거래량 기반 눌림목 탐지
- GitHub Actions 자동 실행
- 텔레그램 알림

## 📦 설치
1. tickers.txt에 종목 추가
2. GitHub Secrets에 `TG_BOT_TOKEN`, `TG_CHAT_ID` 등록
3. .github/workflows/scan.yml 추가

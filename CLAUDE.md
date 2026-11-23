# 누수 감지 프로젝트

FT-210 유량계(플로우닉스 KOT-EX)의 순시유량을 RS-485(Modbus RTU)로 읽어 LoRaWAN으로 라즈베리파이의 ChirpStack에 보낸다.
구성과 연결 상태는 `docs/system_info/system_diagram.md`에서 확인한다.

## 코드 위치

- `src/host/`: PC에서 유량계를 직접 읽는 Python 코드 (`main.py`, `main_gui.py`, `utils/`). `src/host/`를 기준으로 import하므로 `python src/host/main.py`처럼 실행한다
- `src/board/`: RAK4631 펌웨어
- `src/server/`: 라즈베리파이 서버 쪽 코드 (ChirpStack 페이로드 코덱)

## 코딩 규칙

Python 코드를 작성·수정하기 전에 `.claude/rules/python-style.md`를 읽는다. 이 규칙은 python-expert 기본 규칙보다 우선한다.

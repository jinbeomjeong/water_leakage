# 누수 감지 프로젝트

YF-B1-S 유량 센서의 펄스를 MP5Y-25 펄스미터로 측정하고, 그 값을 RS-485(Modbus RTU)로 읽어 PC로 가져온다.
구성과 연결 상태는 `docs/system_info/system_diagram.md`에서 확인한다.

## 코드 위치

- `src/host/`: PC에서 펄스미터를 읽는 Python 코드 (`main.py`, `main_gui.py`, `utils/`). `src/host/`를 기준으로 import하므로 `python src/host/main.py`처럼 실행한다
- `src/board/`: RAK4631 펌웨어
- `src/server/`: 라즈베리파이 서버 쪽 코드 (ChirpStack 페이로드 코덱)

## 코딩 규칙

Python 코드를 작성·수정하기 전에 `.claude/rules/python-style.md`를 읽는다. 이 규칙은 python-expert 기본 규칙보다 우선한다.

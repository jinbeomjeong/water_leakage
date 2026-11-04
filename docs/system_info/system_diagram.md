# 시스템 구성도 색인

- 원본: [system_diagram.jpg](system_diagram.jpg)
- 정리한 날짜: 2026-11-05

이 문서는 찾아보기용이다. 그림에 있는 내용과 그림에 없는 내용을 구분해 적었다.

## 구성도

```
Flow-Rate Sensor ──Pulse Train──> Pulse Meter <──RS-485──> LoRa Client Board <──USB (Virtual COM)──> PC
YF-B1-S                           MP5Y-25                  RAK4631 + RAK5802 + RAK19007
```

## 구성 요소

| 구성 요소 | 그림의 모델 | 역할 | 관련 문서 |
|---|---|---|---|
| Flow-Rate Sensor | YF-B1-S | 유량을 펄스로 변환 | [유량 센서 사양](sensor/yf_b1_s_flow_sensor_spec.md) |
| Pulse Meter | MP5Y-25 | 펄스를 측정값으로 변환, Modbus RTU로 제공 | [제품 매뉴얼 색인](../manual/pulse_meter_manual.md), [통신 매뉴얼 색인](../manual/pulse_meter_com.md), [통신 설정값](sensor/pulse_meter_com_settings.md) |
| LoRa Client Board | RAK4631 + RAK5802 + RAK19007 | 펄스미터의 값을 읽어 PC로 전달 | [WisBlock 보드 정보](board/wisblock_board_info.md) |
| PC | - | 보드에서 값을 수신 | - |

LoRa Client Board의 모듈 역할은 다음과 같다.

| 모듈 | 역할 |
|---|---|
| RAK4631 | 코어: 펌웨어 실행, LoRa 무선 |
| RAK5802 | IO: RS-485와 UART 변환 |
| RAK19007 | 베이스: 모듈 장착, USB-C, 전원 |

## 연결

| 구간 | 신호 | 방향 | 세부 내용 | 상태 |
|---|---|---|---|---|
| Flow-Rate Sensor → Pulse Meter | Pulse Train | 단방향 | 센서 빨강: 5번 +12 V, 노랑: 1번 INA, 검정: 4번 0 V | 미연결 |
| Pulse Meter ↔ LoRa Client Board | RS-485 | 양방향 | MP5Y 7번 A(+), 8번 B(−). Modbus RTU, 9600 bps, 8N2, 국번 1 | 미연결, 통신 미확인 |
| LoRa Client Board ↔ PC | USB (Virtual COM) | 양방향 | USB CDC, 펌웨어의 `Serial` | 2026-11-04 양방향 확인 |

세부 내용은 그림에 없고 관련 문서와 시험에서 가져왔다. 상태는 정리한 날짜 기준이다.

## 그림에 없는 내용

- 펄스미터 전원: 24 VAC 또는 24~48 VDC를 별도로 공급해야 한다.
- 보드 내부 연결: RAK4631과 RAK5802는 UART(`Serial1`)로 연결된다.
- LoRaWAN 경로: 그림의 보드는 PC와 USB로만 연결되어 있고, 게이트웨이와 서버는 없다.

## 관련 코드

| 위치 | 내용 |
|---|---|
| `board/board.ino` | 1초마다 PV를 읽어 USB로 출력 |
| `board/header/pulse_meter.h`, `board/src/pulse_meter.cpp` | 보드에서 RS-485로 펄스미터 읽기 |
| `utils/pulse_meter.py` | PC에서 Modbus로 펄스미터 읽기 (보드를 거치지 않는 구성) |

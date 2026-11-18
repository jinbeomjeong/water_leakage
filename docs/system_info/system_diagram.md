# 시스템 구성도 색인

- 원본: [system_diagram.jpg](system_diagram.jpg)
- 정리한 날짜: 2026-11-05

이 문서는 찾아보기용이다. 그림에 있는 내용과 그림에 없는 내용을 구분해 적었다.

## 구성도

```
                                                           User Device
                                                                ^
                                                                |
                                                           Wi-Fi (HTTP)
                                                                |
                                                                v
                                                           Wi-Fi Router <──Ethernet (MQTT, HTTP)──> Raspberry Pi 5
                                                                ^                                   Role: LoRaWAN Network Server
                                                                |                                         MQTT Broker Server
                                                         Ethernet (MQTT)                                  Data Collection
                                                                |                                         Web-Server
                                                                v
                                                           LoRa Gateway
                                                           TF-GW1
                                                                ^
                                                                |
                                                         LoRaWAN (KR920)
                                                                |
                                                                v
Flow-Rate Sensor ──Pulse Train──> Pulse Meter <──RS-485──> LoRa Client Board <──USB (Virtual COM)──> PC
YF-B1-S                           MP5Y-25                  RAK4631 + RAK5802 + RAK19007              Role: Local Monitoring
```

## 구성 요소

| 구성 요소 | 그림의 모델 | 그림의 역할 | 설명 | 관련 문서 |
|---|---|---|---|---|
| Flow-Rate Sensor | YF-B1-S | - | 유량을 펄스로 변환 | [유량 센서 사양](sensor/yf_b1_s_flow_sensor_spec.md) |
| Pulse Meter | MP5Y-25 | - | 펄스를 측정값으로 변환, Modbus RTU로 제공 | [제품 매뉴얼 색인](../manual/pulse_meter_manual.md), [통신 매뉴얼 색인](../manual/pulse_meter_com.md), [통신 설정값](sensor/pulse_meter_com_settings.md) |
| LoRa Client Board | RAK4631 + RAK5802 + RAK19007 | - | 펄스미터의 값을 읽고 PC, 게이트웨이와 통신 | [WisBlock 보드 정보](board/wisblock_board_info.md) |
| PC | - | Local Monitoring | 보드와 USB로 통신 | - |
| LoRa Gateway | TF-GW1 | - | 보드와 LoRaWAN으로 통신, Wi-Fi Router와 Ethernet으로 연결 | [TF-GW1 조사 정리](gateway/thingsfirst_tf-gw1_gateway.md) |
| Wi-Fi Router | - | - | 게이트웨이, 라즈베리파이, User Device를 연결 | - |
| Raspberry Pi 5 | - | LoRaWAN Network Server, MQTT Broker Server, Data Collection, Web-Server | 네트워크 서버와 MQTT 브로커 운영, 데이터 수집, 웹 제공 | [ChirpStack 서버 정리](chirp_stack_server/chirpstack_server.md) |
| User Device | - | - | Wi-Fi Router를 거쳐 HTTP로 접속 | - |

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
| LoRa Client Board ↔ LoRa Gateway | LoRaWAN (KR920) | 양방향 | Class A, OTAA, LoRaWAN 1.0.2 / RP 1.0.2 rev B, 업링크 FPort 1, 7바이트 페이로드 | 2026-11-18 라즈베리파이 ChirpStack으로 Join과 30초 주기 업링크, 디코딩 확인 |
| LoRa Gateway ↔ Wi-Fi Router | Ethernet (UDP) | 양방향 | Work Mode: Packet forwarder, Protocol: Semtech UDP GWMP, 서버 라즈베리파이 UDP 1700 | 2026-11-18 PC 인터넷 연결 공유 망에서 확인, 공유기는 미적용 |
| Raspberry Pi 5 ↔ Wi-Fi Router | Ethernet (HTTP) | 양방향 | ChirpStack 웹 UI 8080, MQTT 브로커는 Pi 내부(127.0.0.1)에서만 | 2026-11-18 PC 인터넷 연결 공유 망에서 확인, 공유기는 미적용 |
| User Device ↔ Wi-Fi Router | Wi-Fi (HTTP) | 양방향 | - | 통신 미확인 |

세부 내용은 그림에 없고 관련 문서와 시험에서 가져왔다. 상태는 각 칸에 날짜가 없으면 정리한 날짜 기준이다.

### 업링크 페이로드

보드가 FPort 1로 보내는 7바이트 페이로드다. 여러 바이트 값은 큰 자리부터 보낸다.

| 바이트 | 내용 |
|---|---|
| 0 | 펄스미터 상태: 0 정상, 1 응답 없음, 2 CRC 오류, 3 예외 응답, 4 잘못된 응답 |
| 1 | 소수점 자릿수, 상태가 정상일 때만 의미가 있다 |
| 2–5 | PV 원시값(int32), 상태가 정상일 때만 의미가 있다 |
| 6 | Modbus 예외 코드, 상태가 예외 응답일 때만 의미가 있다 |

예: `01000000000000`은 펄스미터 응답 없음이다. `0002000004D200`은 소수점 2자리, 원시값 1234로 PV 12.34다.

## 그림에 없는 내용

- 펄스미터 전원: 24 VAC 또는 24~48 VDC를 별도로 공급해야 한다.
- 보드 내부 연결: RAK4631과 RAK5802는 UART(`Serial1`)로 연결된다.
- 게이트웨이 전원: DC 12 V 또는 PoE 48 V 중 어느 쪽을 쓸지 그림에 없다.
- LoRaWAN 설정: Class A, OTAA로 정했다.
- 네트워크 서버 소프트웨어: 그림에는 역할만 있고, ChirpStack으로 정했다.
- 게이트웨이 ↔ 라즈베리파이 프로토콜: 그림은 MQTT지만 Semtech UDP로 연결했다. MQTT 브로커를 Pi 내부에만 두기 위해서다 ([게이트웨이 7절](gateway/thingsfirst_tf-gw1_gateway.md)).
- 지금 망: Wi-Fi 공유기 대신 PC의 인터넷 연결 공유(ICS) 망에 게이트웨이와 라즈베리파이를 유선으로 연결해 시험했다.
- 데이터 저장: 라즈베리파이의 저장 방식이 그림에 없다.

## 관련 코드

| 위치 | 내용 |
|---|---|
| `src/board/board.ino` | 1초마다 PV를 읽어 USB로 출력, Join 후 30초마다(시험용) 마지막 값을 LoRaWAN으로 송신 |
| `src/board/header/pulse_meter.h`, `src/board/src/pulse_meter.cpp` | 보드에서 RS-485로 펄스미터 읽기 |
| `src/board/header/lorawan_link.h`, `src/board/src/lorawan_link.cpp` | KR920 OTAA Join과 업링크 (SX126x-Arduino) |
| `src/board/header/lorawan_keys.example.h` | OTAA 키 파일 양식, 실제 키는 `lorawan_keys.h`(git 제외)에 둔다 |
| `src/server/payload_codec.js` | ChirpStack 장치 프로필의 업링크 디코더 |
| `src/host/utils/pulse_meter.py` | PC에서 Modbus로 펄스미터 읽기 (보드를 거치지 않는 구성) |

라즈베리파이의 ChirpStack과 MQTT 브로커는 설정해 동작 중이다 ([ChirpStack 서버 정리](chirp_stack_server/chirpstack_server.md)). 데이터 수집, 저장, 웹서버 코드는 아직 없다.

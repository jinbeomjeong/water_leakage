# 시스템 구성도 색인

- 원본: [system_diagram.jpg](system_diagram.jpg) (`system_diagram.pptx`에서 내보낸 그림)
- 정리한 날짜: 2026-11-05
- 수정한 날짜: 2026-11-23 (공유기 망 주소, 유량계를 FT-210으로 교체)

이 문서는 찾아보기용이다. 그림에 있는 내용과 그림에 없는 내용을 구분해 적었다.

2026-11-23 유량 센서 YF-B1-S와 펄스미터 MP5Y-25를 빼고 FT-210 유량계를 보드에 직접 연결했다. 아래 구성도와 표는 바뀐 구성이고, `system_diagram.jpg`와 `system_diagram.pptx`는 아직 예전 구성(센서 → 펄스미터)을 그리고 있다.

## 구성도

```
                                                           User Device
                                                                ^
                                                                |
                                                           Wi-Fi (HTTP)
                                                                |
                                                                v
                                                           Wi-Fi Router <──Ethernet (UDP, HTTP)──> Raspberry Pi 5
                                                                ^                                  Role: LoRaWAN Network Server (ChirpStack)
                                                                |                                        Gateway Bridge (UDP → MQTT)
                                                       Ethernet (UDP 1700)                               MQTT Broker (Pi internal only)
                                                                |                                        Data Collection (planned, via MQTT)
                                                                v                                        Web-Server (planned)
                                                           LoRa Gateway
                                                           TF-GW1 (RAK7289V2)
                                                                ^
                                                                |
                                                         LoRaWAN (KR920)
                                                                |
                                                                v
Flow Meter <─────────────RS-485 (Modbus RTU)─────────────> LoRa Client Board <──USB (Virtual COM)──> PC
FT-210 (KOT-EX)                                            RAK4631 + RAK5802 + RAK19007              Role: Local Monitoring
```

## 구성 요소

| 구성 요소 | 그림의 모델 | 그림의 역할 | 설명 | 관련 문서 |
|---|---|---|---|---|
| Flow Meter | FT-210 (플로우닉스 KOT-EX 터빈유량계) | - | 순시유량을 측정해 Modbus RTU로 제공 | [매뉴얼 색인](../manual/flow_transmitter_ft210_manual.md), [통신 설정값](sensor/ft210_flow_meter_settings.md) |
| LoRa Client Board | RAK4631 + RAK5802 + RAK19007 | - | 유량계의 값을 읽고 PC, 게이트웨이와 통신 | [WisBlock 보드 정보](board/wisblock_board_info.md) |
| PC | - | Local Monitoring | 보드와 USB로 통신 | - |
| LoRa Gateway | TF-GW1 (RAK7289V2) | - | 보드와 LoRaWAN으로 통신, Wi-Fi Router와 Ethernet으로 연결 | [TF-GW1 조사 정리](gateway/thingsfirst_tf-gw1_gateway.md) |
| Wi-Fi Router | - | - | 게이트웨이, 라즈베리파이, User Device를 연결 | - |
| Raspberry Pi 5 | - | LoRaWAN Network Server (ChirpStack), Gateway Bridge (UDP → MQTT), MQTT Broker (Pi internal only), Data Collection (planned, via MQTT), Web-Server (planned) | 네트워크 서버와 MQTT 브로커 운영 중, 데이터 수집과 웹 제공은 예정 | [ChirpStack 서버 정리](chirp_stack_server/chirpstack_server.md) |
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
| Flow Meter ↔ LoRa Client Board | RS-485 | 양방향 | FT-210 COM_A(+) ↔ RAK5802 RS485-A, COM_B(−) ↔ RS485-B. Modbus RTU, 9600 bps, 8N1, 국번 1 | 2026-11-23 순시유량 읽기 확인 |
| LoRa Client Board ↔ PC | USB (Virtual COM) | 양방향 | USB CDC, 펌웨어의 `Serial` | 2026-11-04 양방향 확인 |
| LoRa Client Board ↔ LoRa Gateway | LoRaWAN (KR920) | 양방향 | Class A, OTAA, LoRaWAN 1.0.2 / RP 1.0.2 rev B, 업링크 FPort 1, 유량 레코드 2바이트 페이로드 | 2026-11-18 라즈베리파이 ChirpStack으로 Join과 30초 주기 업링크, 디코딩 확인. 2026-11-23 유량 레코드 형식 펌웨어와 코덱을 적용해 디코딩 확인 |
| LoRa Gateway ↔ Wi-Fi Router | Ethernet (UDP 1700) | 양방향 | Work Mode: Packet forwarder, Protocol: Semtech UDP GWMP, 서버 라즈베리파이 `192.168.0.6` UDP 1700. 게이트웨이 주소 `192.168.0.4` | 2026-11-23 iptime 공유기 망에서 확인, DHCP 예약 안 함 |
| Raspberry Pi 5 ↔ Wi-Fi Router | Ethernet (UDP, HTTP) | 양방향 | 주소 `192.168.0.6`. 게이트웨이 UDP 1700 수신, ChirpStack 웹 UI 8080. MQTT 브로커는 Pi 내부(127.0.0.1)에서만 | 2026-11-23 iptime 공유기 망에서 확인, DHCP 예약 안 함 |
| User Device ↔ Wi-Fi Router | Wi-Fi (HTTP) | 양방향 | - | 통신 미확인 |

세부 내용은 그림에 없고 관련 문서와 시험에서 가져왔다. 상태는 각 칸에 날짜가 없으면 정리한 날짜 기준이다.

### 업링크 페이로드

보드는 FPort 1로 레코드를 보낸다. 페이로드에는 레코드를 여러 개 이어 붙일 수 있고, 여러 바이트 값은 큰 자리부터 보낸다(빅 엔디안). 지금 보드는 유량 레코드 하나(2바이트)만 보낸다.

레코드의 첫 바이트는 상위 4비트가 센서 종류, 하위 4비트가 상태다.

| 첫 바이트 | 센서 종류 | 상태 |
|---|---|---|
| `0x00` | 유량 | 정상 |
| `0x01` | 유량 | 고장 |
| `0x10` | 전류 | 정상 |
| `0x11` | 전류 | 고장 |

| 센서 종류 | 데이터 | 레코드 길이 | 환산 | 범위 | 해상도 |
|---|---|---|---|---|---|
| 유량 (0x0) | 원시값 1바이트 | 2바이트 | y = x × 0.01 | 0~2 LPM, 2를 넘으면 200으로 자른다 | 0.01 LPM |
| 전류 (0x1) | 원시값 2바이트 | 3바이트 | y = x × 0.1 − 30 | −30~30 mA | 0.1 mA |

- 고장은 유량계의 응답 없음, CRC 오류, 예외 응답, 잘못된 응답을 모두 묶은 것이다. 고장이면 데이터 바이트는 0이고 의미가 없다. 원인은 보드의 USB 로그에서 확인한다.
- 유량 원시값은 FT-210의 순시유량을 0.01 단위로 반올림한 값이다. FT-210의 단위는 L/min(LPM)으로 설정했다 (2026-11-23). 음수는 0으로 보낸다.
- 전류는 형식만 정했고, 보드에 전류 입력이 없어 아직 보내지 않는다.
- 유량 레코드 형식은 커밋 `0c5efd6`에서 정했고, 2026-11-23 범위를 0~20 LPM(0.1 단위)에서 0~2 LPM(0.01 단위)으로 바꿨다. 바꾼 펌웨어와 코덱은 같은 날 보드와 ChirpStack에 적용했다.

예: `0100`은 유량 고장이다. `007B`는 원시값 123으로 유량 1.23 LPM이다. `007B100258`은 유량 1.23 LPM과 전류 30.0 mA(원시값 600)다.

## 그림에 없는 내용

- 유량계 전원: FT-210은 DC 24 V 또는 AC 90~300 V를 별도로 공급해야 한다 (매뉴얼 p.2).
- 보드 내부 연결: RAK4631과 RAK5802는 UART(`Serial1`)로 연결된다.
- 게이트웨이 전원: DC 12 V 또는 PoE 48 V 중 어느 쪽을 쓸지 그림에 없다.
- LoRaWAN 설정: Class A, OTAA, LoRaWAN 1.0.2 / RP 1.0.2 rev B로 정했다.
- 게이트웨이 작동 모드: Packet forwarder, Protocol은 Semtech UDP GWMP. MQTT Bridge 대신 UDP를 고른 것은 MQTT 브로커를 Pi 내부에만 두기 위해서다 ([게이트웨이 7절](gateway/thingsfirst_tf-gw1_gateway.md)).
- Pi 내부의 MQTT 흐름: Gateway Bridge가 게이트웨이의 UDP 패킷을 `kr920/gateway/...` 토픽으로 바꿔 ChirpStack에 넘기고, ChirpStack은 디코딩한 업링크를 `application/.../event/up` 토픽으로 내보낸다. ChirpStack v4는 게이트웨이와 MQTT로만 연결하므로 게이트웨이 프로토콜과 관계없이 브로커가 필요하다.
- 라즈베리파이의 나머지 구성 요소: Redis, SQLite DB, ChirpStack REST API ([ChirpStack 서버 정리](chirp_stack_server/chirpstack_server.md)).
- 지금 망: 2026-11-23 게이트웨이(`192.168.0.4`)와 라즈베리파이(`192.168.0.6`)를 iptime 공유기(`192.168.0.1`)에 유선으로 연결했다. 2026-11-18까지는 PC의 인터넷 연결 공유(ICS) 망에서 시험했다.
- 데이터 저장: 라즈베리파이의 저장 방식은 아직 정하지 않았다.

## 관련 코드

| 위치 | 내용 |
|---|---|
| `src/board/board.ino` | 1초마다 순시유량을 읽어 USB로 출력, Join 후 30초마다(시험용) 마지막 값을 LoRaWAN으로 송신 |
| `src/board/header/flow_meter.h`, `src/board/src/flow_meter.cpp` | 보드에서 RS-485로 FT-210 순시유량 읽기 |
| `src/board/header/lorawan_link.h`, `src/board/src/lorawan_link.cpp` | KR920 OTAA Join과 업링크 (SX126x-Arduino) |
| `src/board/header/lorawan_keys.example.h` | OTAA 키 파일 양식, 실제 키는 `lorawan_keys.h`(git 제외)에 둔다 |
| `src/server/payload_codec.js` | ChirpStack 장치 프로필의 업링크 디코더 |
| `src/host/utils/flow_meter.py` | PC에서 USB-RS485 어댑터로 FT-210 순시유량 읽기 (보드를 거치지 않는 구성) |

라즈베리파이의 ChirpStack과 MQTT 브로커는 설정해 동작 중이다 ([ChirpStack 서버 정리](chirp_stack_server/chirpstack_server.md)). 데이터 수집, 저장, 웹서버 코드는 아직 없다.

# WisBlock 보드 조사 정리 (RAKwireless)

작성일: 2026-11-04

## 1. 구성 요약

| 층 | 모듈 | 확신도 | 비고 |
|---|---|---|---|
| 코어 | RAK4631 (RAK4630 모듈 탑재) | 높음 | H/L 버전은 사진으로 확인 불가 |
| 베이스 | RAK19007 (2세대 베이스보드) | 높음 | USB-C, 슬롯 A~D 4개, `AIN1` 헤더 표기 확인. 모델명 직접 인쇄는 미확인 |
| IO | RAK5802 (RS485 모듈) | 확정 | 칩 마킹 `3PEAK TP8485E`, 단자대 실크로 확인, 사용자 최종 확인 완료 |

## 2. 코어: RAK4631 / RAK4630

- MCU: Nordic nRF52840 (BLE 5.0)
- LoRa 트랜시버: Semtech SX1262
- LoRaWAN 1.0.3 Class A/B/C, LoRa P2P 지원
- RAK4631 크기: 20 x 30 mm (RAK4630 스탬프 모듈 + 확장 PCB, SWD 핀 포함)
- 버전: H(고주파: EU868, US915, IN865 등), L(저주파: EU433 등)
  - 한국(KR920)은 H 버전이어야 함 → **라벨/구매 내역으로 확인 필요**
- 사진상 LoRa/BLE용 u.FL 안테나 커넥터 확인 (LoRa 안테나 연결됨)

## 3. 베이스: RAK19007 (추정)

- 코어 슬롯 1개, IO 슬롯 1개, 센서 슬롯 A~D 4개
- USB-C(프로그래밍/디버깅/배터리 충전), 리셋 버튼
- 배터리 커넥터 3.7V (최대 4.3V 초과 금지)
- 태양광 커넥터 5V (최대 5.5V 초과 금지)
- 크기 30 x 60 mm
- J10/J11/J12 2.54mm 헤더(BOOT, I2C, GPIO, UART) 노출

## 4. IO 모듈: RAK5802 (RS485)

- 역할: RS485 ↔ UART 변환 (Modbus RTU 용도)
- 칩: 3PEAK TP8485E
- RS485 1포트, 최대 16노드, ESD 18kV HBM 보호
- 크기 35 x 25 mm
- 전원: VBAT 2.6~4.2V 권장, 3V3 3.0~3.6V

### 단자대 핀맵 (공식 8핀)

| 위쪽 4핀 | 아래쪽 4핀 |
|---|---|
| RS485-B | I2C_SCL |
| RS485-A | I2C_SDA |
| GND | 3V3 |
| PWR (배터리 전원) | A1 (실크 `AIN`) |

> 주의: 실크 문구 위쪽 끝 두 칸은 사진상 `RX/TX`처럼 보였으나, 공식 핀맵상 `A/B`일 가능성이 큼.
> 배선 전 멀티미터/확대 사진으로 A/B 위치 확인 필요. A/B를 반대로 연결하면 통신 불가.

### 코어와의 내부 연결 (40핀 IO 커넥터)

- UART_TX: 33번, UART_RX: 34번
- DE: 29번 (예약)
- I2C1 SDA/SCL: 19/20번, Analog1: 21번
- 공식 문서에 전력 소모, 120Ω 종단 저항 정보 없음 → 장거리 배선 시 별도 확인

## 5. 데이터 전송 경로 (LoRa 센서 프로젝트 기준)

```
Modbus RS485 센서 → RAK5802 → (UART) → RAK4631 → LoRaWAN(KR920) → 게이트웨이 → ChirpStack
```

1. 센서의 Modbus 슬레이브 주소, 보레이트/패리티, 레지스터 맵 확보
2. 코어 펌웨어는 RUI3(Arduino BSP) 권장: 읽기 → 패킹 → `api.lorawan.send()`
3. ChirpStack에 디바이스 등록 (OTAA: DevEUI, AppKey), DevEUI는 RAK4630 라벨에 인쇄됨
4. 디코더는 ChirpStack 장치 프로파일에 JS로 작성

### 300~400노드 규모 유의사항

- 페이로드 최소화 (float 대신 2바이트 정수 등)
- 업링크 주기를 수 분 단위로 길게 설정
- 센서 전원은 별도 전원 사용 (`BAT` 핀은 배터리 전압이라 센서 전원으로 부적합)

## 6. 미확인 / 다음 확인 사항

- [ ] 코어 H/L 버전: 라벨에 H/L 표기 없음. 한국 KC 인증 마크(`R-R-SrT-RAK4630`)와 한글 제조국 표기가 있어 국내용으로 보이나, 주파수 대역은 구매 내역이나 AT 명령(`AT+BAND=?`)으로 확인 필요
- [ ] DevEUI: 라벨에 `AC1F09FF FE0?D696` 형태로 인쇄, 중간 한 자리가 매직 글씨에 가려짐. QR코드나 AT 명령(`AT+DEVEUI=?`)으로 확인
- [x] 베이스 모델: 뒷면 사진으로 슬롯 A~D 4개와 헤더(BAT, IO2, IO1, AIN1, RX1, TX1, GND, BOOT0 / SDA, SCL, GND, VDD) 확인 → RAK19007과 일치 (모델명 인쇄만 미확인)
- [ ] RAK5802 위쪽 단자대 A/B 위치
- [ ] 연결할 센서 모델, Modbus 지원 여부
- [ ] 업링크 주기

## Sources

- [RAK4630 Datasheet](https://docs.rakwireless.com/product-categories/wisduo/rak4630-module/datasheet/)
- [RAK4631 Datasheet](https://docs.rakwireless.com/product-categories/wisblock/rak4631/datasheet/)
- [RAK19007 Datasheet](https://docs.rakwireless.com/product-categories/wisblock/rak19007/datasheet/)
- [RAK5802 Datasheet](https://docs.rakwireless.com/product-categories/wisblock/rak5802/datasheet/)

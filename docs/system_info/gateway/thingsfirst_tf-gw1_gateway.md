# ThingsFirst LoRa 게이트웨이 TF-GW1 조사 정리

작성일: 2026-11-05

## 1. 라벨 정보 (사진에서 읽은 내용)

| 항목 | 내용 |
|---|---|
| 제품명 / 모델명 | ThingsFirst-LoRa-Gateway / TF-GW1 |
| 제조사 | Shenzhen RAKwireless Technology CO., Ltd. (중국) |
| 입력 전원 | DC 12V 1A, PoE 48V 0.3A |
| OS | WisGateOS 2 |
| 인증 LoRa 모듈 | RAK5146 (R-R-SrT-RAK5146) |
| 인증 WiFi 모듈 | RAK634 (R-C-SrT-RAK634) |
| 인증 번호 | R-R-FNI-TF-GW1 (KC) |
| 제조년월 | 2026년 3월 |

- ThingsFirst 상표를 단 RAK 제조품(OEM)으로 보임
- `TF-GW1`이라는 이름의 공개 자료는 검색되지 않음 → 정확한 사양은 웹 UI 또는 ThingsFirst 문의로 확인 필요

## 2. 핵심 부품

### RAK5146 (LoRa 집중기)
- Semtech SX1303 기반 mini-PCIe 형태 LoRa concentrator (LBT용 SX126X 포함)
- KR920을 포함해 EU868, US915, AS923, AU915, IN865 등 지원
- SPI/USB 인터페이스 선택 가능, GPS(ZOE-M8Q) 내장 옵션
- 수신 감도 -139dBm (SF12, BW125kHz), 송신 최대 27dBm

### RAK634 (CPU/WiFi 메인보드)
- WisGate Edge 계열의 CPU 모듈로 알려져 있음 (MT7628, DDR2 128MB)

## 3. 기종 추정 (검증되지 않은 추정)

- 흰색 실외형 하우징, 12V/PoE 입력, WisGateOS 2, RAK5146 구성이 **RAK7289V2 WisGate Edge Pro**와 유사
  - RAK7289V2: IP67 산업용 실외 LoRaWAN 게이트웨이, 8채널/16채널(SX1303 1개/2개)
- 라벨에 LoRa 모듈이 RAK5146 하나뿐이라 **8채널**일 가능성이 큼
- 확정하려면 게이트웨이 웹 UI의 LoRa 설정 화면이나 제조사 확인 필요

## 4. ChirpStack 프로젝트 연결

- KR920 설정 가능
- WisGateOS 2는 패킷 포워더 / Basics Station 모드 지원 (Basics Station 모드는 최대 16채널)
- 라즈베리파이의 ChirpStack에 연결: 게이트웨이 웹 UI에서 서버 주소 설정, ChirpStack에는 라벨의 GWEUI로 게이트웨이 등록
- 노드(RAK4630)의 DevEUI도 `AC1F09FF`로 시작하는 같은 RAK 제조 계열
- 300~400노드를 8채널 한 대로 감당 가능한지는 업링크 주기와 페이로드 크기에 따라 달라짐

## 5. 미확인 / 다음 확인 사항

- [ ] 채널 수(8/16)와 정확한 기종 (RAK7289V2 계열 여부)
- [ ] 웹 UI 접속 주소와 계정
- [x] 사용할 모드: 패킷 포워더 + LoRa Gateway MQTT Bridge (ChirpStack 4.x, Protobuf)
- [ ] 노드 업링크 주기 (용량 계산용)

## Sources

- [RAK5146 Datasheet](https://docs.rakwireless.com/product-categories/wislink/rak5146/datasheet/)
- [RAK7289V2 Datasheet](https://docs.rakwireless.com/product-categories/wisgate/rak7289v2/datasheet/)
- [RAK7289CV2 (rossma)](https://rossma.ru/fr/products/lorawan-gateway-rak-7289cv2-fr)
- [Basics Station 16채널 가이드](https://learn.rakwireless.com/hc/en-us/articles/35798804070423-16-Channel-Support-in-Basics-Station-Mode)

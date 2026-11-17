# ThingsFirst LoRa 게이트웨이 TF-GW1 조사 정리

작성일: 2026-11-05
수정일: 2026-11-17 (기종 확인, 접속 방법, 공장 초기화, 내장 네트워크 서버 시험 추가)

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

## 3. 기종

- **RAK7289V2 WisGate Edge Pro**로 확인 (2026-11-17)
  - 근거: Wi-Fi AP 이름 `RAK7289V2_3633`, 콘솔 로그인 프롬프트 `RAK7289V2 login:`
  - RAK7289V2: IP67 산업용 실외 LoRaWAN 게이트웨이, 8채널/16채널(SX1303 1개/2개)
- 라벨에 LoRa 모듈이 RAK5146 하나뿐이라 **8채널**일 가능성이 큼 (미확인)

## 4. 장비 정보와 접속 방법 (2026-11-17 확인)

| 항목 | 값 |
|---|---|
| OS | WisGateOS 2.2.16 |
| 이더넷 MAC | `AC:1F:09:26:36:33` |
| Wi-Fi AP | SSID `RAK7289V2_3633` (BSSID `ac:1f:09:26:36:34`), 공장 초기값은 비밀번호 없음 |
| 웹 UI 계정 | `root` |

접속 경로:

| 경로 | 주소 | 조건 |
|---|---|---|
| Wi-Fi AP | `https://192.168.230.1` | AP가 켜져 있을 때 |
| 이더넷, DHCP 서버 없음 | `https://169.254.54.51` | PC와 직접 연결. 주소는 MAC 마지막 2바이트(`36:33` → 54.51)에서 정해짐 |
| 이더넷, DHCP | `https://192.168.137.177` | PC의 인터넷 연결 공유(ICS) 망에 연결했을 때 받은 주소. 고정 아님 |
| USB-C 콘솔 | CH340, 57600-8-N-1 | 부팅 로그 확인, 로그인에는 `root` 비밀번호 필요 |

- 웹 UI는 부팅 후 1분 정도 늦게 뜬다. 그 전에는 ping과 SSH(22)만 응답하고 80/443은 연결이 거부된다.
- `/api/info`(로그인 불필요)로 펌웨어 버전과 비밀번호 설정 여부(`passwordSet`)를 볼 수 있다.

## 5. 공장 초기화

- Reset 버튼: 짧게 누르면 재부팅, 길게 누르면 공장 초기화
- 부팅이 끝나기 전에 누르면 초기화되지 않는다. 다음 순서로 확인했다.
  1. USB-C 콘솔로 부팅 로그를 본다.
  2. `boot done`이 찍힌 뒤 Reset 버튼을 약 30초 누른다.
  3. 콘솔에 `FACTORY RESET`이 찍히고 재부팅된다.
  4. 부팅 로그의 `last factory reset executed by ... at <시각>`으로 초기화 시각을 확인한다.
- 공장 초기화 뒤에도 `passwordSet`이 `true`였다. 공장 초기값에 비밀번호가 들어 있는 것으로 보인다 (OEM 설정 추정, 미확인).
- Wi-Fi 설정은 초기화로 되돌아가서 AP가 다시 켜졌다.

## 6. 내장 네트워크 서버 시험 (2026-11-17)

라즈베리파이 없이 보드와의 LoRaWAN 연결을 확인하려고 게이트웨이 내장 네트워크 서버를 썼다.

| 항목 | 설정 |
|---|---|
| Work Mode | Built-in Network Server |
| Region | KR920 |
| Application | `water_leakage`, Application Type UNIFIED, Auto Add Device 켬 |
| Application EUI | `106ae760df700794` |
| Application Key | 웹 UI와 `board/header/lorawan_keys.h`(git 제외)에만 둔다 |

결과:

- 보드(DevEUI `4A0A4A3FB63B9137`)가 OTAA로 Join했고 `dev_4a0a4a3fb63b9137`로 자동 등록됐다.
- End Device Packet Capture에서 FPort 1, 페이로드 `01000000000000`(펄스미터 응답 없음) 업링크를 확인했다.
- 보드와 게이트웨이가 가까워 RSSI가 -40 dBm을 넘는 패킷이 있었다.

## 7. ChirpStack 프로젝트 연결

- KR920 설정 가능
- WisGateOS 2는 패킷 포워더 / Basics Station 모드 지원 (Basics Station 모드는 최대 16채널)
- 라즈베리파이의 ChirpStack에 연결: 게이트웨이 웹 UI에서 서버 주소 설정, ChirpStack에는 라벨의 GWEUI로 게이트웨이 등록
- 노드(RAK4630)의 DevEUI도 `AC1F09FF`로 시작하는 같은 RAK 제조 계열
- 300~400노드를 8채널 한 대로 감당 가능한지는 업링크 주기와 페이로드 크기에 따라 달라짐

## 8. 미확인 / 다음 확인 사항

- [ ] 채널 수(8/16)
- [x] 기종: RAK7289V2
- [x] 웹 UI 접속 주소와 계정 (4절)
- [x] 사용할 모드: 패킷 포워더 + LoRa Gateway MQTT Bridge (ChirpStack 4.x, Protobuf). 지금은 시험용으로 내장 네트워크 서버 사용 중
- [ ] MQTT 브로커 주소: 라즈베리파이 IP, 라즈베리파이 준비 후 설정
- [ ] 게이트웨이 IP 고정 (고정 IP 또는 공유기 DHCP 예약)
- [ ] 노드 업링크 주기 (용량 계산용). 지금 펌웨어는 시험용 30초

## Sources

- [RAK5146 Datasheet](https://docs.rakwireless.com/product-categories/wislink/rak5146/datasheet/)
- [RAK7289V2 Datasheet](https://docs.rakwireless.com/product-categories/wisgate/rak7289v2/datasheet/)
- [RAK7289CV2 (rossma)](https://rossma.ru/fr/products/lorawan-gateway-rak-7289cv2-fr)
- [Basics Station 16채널 가이드](https://learn.rakwireless.com/hc/en-us/articles/35798804070423-16-Channel-Support-in-Basics-Station-Mode)
- [RAK7289V2 Quick Start](https://docs.rakwireless.com/product-categories/wisgate/rak7289v2/quickstart/)
- [WisGateOS 2 LoRa Configuration](https://docs.rakwireless.com/product-categories/software-apis-and-libraries/wisgateos2/wisgateos2-edge-soho/lora-configuration/)
- [WisGateOS 2 Network](https://docs.rakwireless.com/product-categories/software-apis-and-libraries/wisgateos2/wisgateos2-edge-soho/network/)
- [RAK 포럼: RAK7268V2 Reset button](https://forum.rakwireless.com/t/rak7268v2-reset-button/16408)

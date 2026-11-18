# 라즈베리파이 ChirpStack 서버 정리

작성일: 2026-11-18

라즈베리파이 5에 ChirpStack을 띄우고, 게이트웨이와 보드를 연결해 업링크가 디코딩되는 것까지 확인한 내용이다.

## 1. 장비와 접속 (2026-11-18 확인)

| 항목 | 값 |
|---|---|
| 기종 | Raspberry Pi 5 Model B Rev 1.0, RAM 8 GB |
| OS | Debian GNU/Linux 13 (trixie), 커널 6.18.50+rpt-rpi-2712 |
| 저장 장치 | SD 카드 115 GB (2026-11-18 기준 25 GB 사용) |
| 호스트 이름 | `raspberrypi` (`raspberrypi.local`, ICS 망에서는 `raspberrypi.mshome.net`) |
| eth0 MAC | `2C:CF:67:2A:50:62` (wlan0 `2C:CF:67:2A:50:63`, 사용 안 함) |
| IP | `192.168.137.155`, PC의 인터넷 연결 공유(ICS) 망에서 받은 주소. 고정 아님 |
| 시간대 | `Asia/Seoul` (2026-11-18 `America/New_York`에서 변경), NTP 동기화 |
| 계정 | `pi`. PC의 SSH 키(`~/.ssh/id_ed25519`)로 로그인, sudo는 비밀번호 필요 |
| sudo 비밀번호 | `sudo_pwd.txt`(git 제외)에만 둔다 |

열려 있는 포트:

| 포트 | 프로그램 | 바인드 | 용도 |
|---|---|---|---|
| 22/tcp | sshd | 전체 | SSH |
| 5900/tcp | wayvnc | 전체 | VNC |
| 1700/udp | chirpstack-gateway-bridge | 전체 | 게이트웨이 패킷 포워더(Semtech UDP) |
| 8080/tcp | chirpstack | 전체 | 웹 UI, gRPC API |
| 8090/tcp | chirpstack-rest-api | 전체 | REST API |
| 1883/tcp | mosquitto | 127.0.0.1 | MQTT, Pi 내부에서만 |
| 6379/tcp | redis-server | 127.0.0.1 | Redis, Pi 내부에서만 |

## 2. 구성 요소

| 구성 요소 | 버전 | 설치 방식 | 상태 |
|---|---|---|---|
| ChirpStack | v4.20.0-test.2 이후 커밋 (`v4.20.0-test.2-12-g3237e30d`) | 소스 빌드, `~/workspace/chirpstack/target/release/chirpstack` | 동작 중, 부팅 시 자동 시작 |
| ChirpStack Gateway Bridge | 4.1.2 | Debian 패키지 | 동작 중 |
| ChirpStack REST API | 4.19.0 | Debian 패키지 | 동작 중 |
| Mosquitto | 2.0.21 | Debian 패키지 | 동작 중 |
| Redis | 8.0.2 | Debian 패키지 | 동작 중 |
| DB | SQLite | ChirpStack SQLite 빌드 | `/var/lib/chirpstack/chirpstack.sqlite` |

- PostgreSQL은 설치되어 있지 않다. 이 빌드는 SQLite를 쓴다.
- 정식 릴리스가 아닌 시험용 빌드다. 오래 운영하려면 정식 릴리스(Debian 패키지 또는 Docker)로 바꾸는 것을 검토한다.

데이터 흐름:

```
게이트웨이 ──UDP 1700──> Gateway Bridge ──MQTT kr920/gateway/...──> ChirpStack
                                                                     │
                                       MQTT application/.../event/up ┘ (디코딩 결과 포함)
```

## 3. 설정 파일과 2026-11-18 변경 내용

### ChirpStack (`/etc/chirpstack/chirpstack.toml`)

변경 전 파일은 `/etc/chirpstack/chirpstack.toml.bak-20261118`로 백업했다.

| 항목 | 변경 전 | 변경 후 |
|---|---|---|
| `[network] enabled_regions` | 15개 지역 | `kr920`만 |
| `[sqlite] path` | 없음 (기본값 `sqlite://chirpstack.sqlite`, 작업 폴더 기준) | `sqlite:///var/lib/chirpstack/chirpstack.sqlite` |
| `/var/lib/chirpstack` 소유자 | root | pi |
| systemd `chirpstack.service` | disabled, 꺼져 있음 | enabled, 동작 중 |

- **SQLite 빌드는 `[postgresql] dsn`을 읽지 않는다.** DB 경로는 `[sqlite] path`로 정한다. 파일에 남아 있는 `dsn` 값은 쓰이지 않는다.
- 예전 DB `~/workspace/chirpstack/chirpstack.sqlite`에는 시험용 데이터(`my-gateway` `0102030405060708`, `my-device` `0011223344556677`)만 있었다. 지우지 않고 남겨 두었다.
- MQTT 통합이 켜져 있어(`[integration.mqtt]`, `server = "tcp://localhost:1883/"`, `json = true`) 애플리케이션 이벤트를 JSON으로 MQTT에 내보낸다.
- `[monitoring]` 설정이 없어 기본값을 쓴다. 장치마다 이벤트와 프레임을 10개씩, 최대 31일 보관한다.

### KR920 지역 (`/etc/chirpstack/region_kr920.toml`)

변경하지 않았다. 확인한 값:

| 항목 | 값 |
|---|---|
| 게이트웨이 MQTT `topic_prefix` | `kr920` |
| 기본 채널 | 922.1, 922.3, 922.5 MHz |
| `rx1_delay` / `rx2_frequency` / `rx2_dr` | 1 s / 921.9 MHz / DR0 |
| `min_dr` / `max_dr` | 0 / 5 |
| `installation_margin` | 10 dB |

### Gateway Bridge (`/etc/chirpstack-gateway-bridge/chirpstack-gateway-bridge.toml`)

변경하지 않았다.

| 항목 | 값 |
|---|---|
| backend | `semtech_udp`, `0.0.0.0:1700` |
| marshaler | `protobuf` |
| 이벤트 토픽 | `kr920/gateway/{{ .GatewayID }}/event/{{ .EventType }}` |
| 명령 토픽 | `kr920/gateway/{{ .GatewayID }}/command/#` |
| MQTT 서버 | `tcp://127.0.0.1:1883`, 인증 없음 |

### REST API (`/etc/chirpstack-rest-api/environment`)

`BIND=0.0.0.0:8090`, `SERVER=0.0.0.0:8080`, `INSECURE=true`. 변경하지 않았다.

## 4. ChirpStack 등록 내용

모두 기본 테넌트 `ChirpStack` 안에 있다. 테넌트는 따로 만들지 않았다.

| 종류 | 이름 | 내용 |
|---|---|---|
| 게이트웨이 | `rak7289v2` | Gateway ID `ac1f09fffe263633` (이더넷 MAC 가운데에 `FFFE`), 통계 주기 30초 |
| 장치 프로필 | `water_leakage` | 아래 표 |
| 애플리케이션 | `water_leakage` | ID `35e23894-606d-4ee6-b00e-1f55c00fd4dc` |
| 장치 | `board-01` | DevEUI `4A0A4A3FB63B9137`, Join EUI `106AE760DF700794` |

장치 프로필 `water_leakage`:

| 항목 | 값 | 근거 |
|---|---|---|
| Region | KR920 | |
| MAC version | LoRaWAN 1.0.2 | SX126x-Arduino 2.0.33 README: MAC V1.0.2 |
| Regional parameters revision | B | SX126x-Arduino 2.0.33 README: PHY V1.0.2 REV B |
| ADR algorithm | Default | |
| Expected uplink interval | 30 s | 시험용 펌웨어 주기 |
| OTAA / Class-B / Class-C | 켬 / 끔 / 끔 | |
| Payload codec | JavaScript, `src/server/payload_codec.js` | |

- Application Key는 ChirpStack과 `src/board/header/lorawan_keys.h`(git 제외)에만 둔다. 게이트웨이 내장 네트워크 서버 시험 때와 같은 키를 쓴다.
- 서버에 넣은 코덱은 주석 한 줄(펌웨어 경로)만 저장소 파일과 다르고 코드는 같다.

## 5. 연결 확인 (2026-11-18)

| 구간 | 결과 |
|---|---|
| 게이트웨이 → Gateway Bridge | 18:27:57부터 연결, 30초마다 `event/stats` 수신 |
| Gateway Bridge → ChirpStack | 게이트웨이 등록 뒤 Online, Last seen 갱신 |
| 보드 Join | 18:54:40 KST Join 성공 |
| 보드 업링크 | 18:55:34부터 30초마다 `UnconfirmedDataUp` |

업링크 예 (18:57:33 KST):

| 항목 | 값 |
|---|---|
| fCnt / fPort / DR | 5 / 1 / DR5 (ADR) |
| data | `AQAAAAAAAA==` (`01000000000000`) |
| object | `{"status": "timeout", "status_code": 1}`, 펄스미터 미연결 |
| RSSI / SNR / 주파수 | -37 dBm / 9.5 dB / 922.1 MHz |
| MQTT 토픽 | `application/35e23894-606d-4ee6-b00e-1f55c00fd4dc/device/4a0a4a3fb63b9137/event/up` |

- ChirpStack은 코덱이 돌려준 숫자를 실수로 바꾼다 (`status_code: 1.0`). 수집 프로그램에서 정수로 바꿔 읽는다.
- 웹 UI에서는 Applications → `water_leakage` → Devices → `board-01` → Events 탭의 `up` 이벤트에서 `object`를 본다.

### Join이 늦어진 문제

- 리셋 뒤 18:50~18:54에 Join Request가 약 15번 들어왔다. 펌웨어는 7초 간격 3번 시도 후 60초 쉬고 다시 시도한다.
- 서버는 매번 Join Accept를 만들었고, 게이트웨이는 매번 전송 ack를 보냈다. 보드는 18:54:40 응답에서야 Join했다.
- 원인은 확인하지 못했다. 보드와 게이트웨이가 가까워 RSSI가 -37 dBm으로 강해서 보드 수신기가 포화되었을 가능성이 있다. 거리를 떼고 첫 시도에 Join되는지 확인한다.

## 6. 운영 명령

```bash
systemctl status chirpstack chirpstack-gateway-bridge chirpstack-rest-api mosquitto redis-server
sudo journalctl -u chirpstack -f
mosquitto_sub -h 127.0.0.1 -t 'application/+/device/+/event/up' -v
```

## 7. 미확인 / 다음 확인 사항

- [ ] ChirpStack `admin` 기본 비밀번호 변경
- [ ] `pi` 계정 비밀번호 변경 (2026-11-18 작업 중 `/etc/timezone`에 몇 초간 노출된 적이 있음)
- [ ] Wi-Fi 공유기로 옮긴 뒤 Pi와 게이트웨이 DHCP 예약, 게이트웨이의 서버 주소 변경
- [ ] Join 지연 원인 확인 (보드와 게이트웨이 거리)
- [ ] 데이터 수집 프로그램: MQTT `event/up` 구독 → DB 저장
- [ ] 웹 서버 (유저 장치용 HTTP)
- [ ] 장치 프로필 Measurements에 `pv` 등록 (펄스미터 연결 후)
- [ ] ChirpStack 정식 릴리스로 교체 여부

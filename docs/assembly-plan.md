# 조립 계획 1.0

> 운영 구현은 병합된 실제 3D 자산 메타데이터를 사용합니다.
> 물리 배치, 분할 전원 레일, 전기 그룹 및 배치 실패 동작은
> `docs/physical-assembly-engine.md`에서 확인할 수 있습니다.

`AssemblyPlan`은 `POST /api/v1/circuit/generate` 응답의 `assemblyPlan`으로
반환되는 서버 소유의 물리 배치 정보입니다. K-EXAONE은 논리 회로를 생성하고,
백엔드는 그 회로를 매번 동일한 물리 계획으로 변환합니다.

## 최상위 계약

- `schemaVersion`: 현재 버전은 `1.0`
- `components`: 고유한 `instanceId`, 자산 데이터베이스의 `assetSlug`, 표시 이름
- `placements`: 부품별 변환 정보 하나(`position`, `rotation`, `scale`)
- `connections`: 형식이 지정된 양 끝점, 안정적인 전기 노드 ID, 배선 색상
- `warnings`: 기계 판독용 코드, 심각도, 한글 메시지, 관련 참조

Pydantic 기준 모델은 `backend/app/schemas/assembly_plan.py`입니다.
알 수 없는 필드와 잘못된 부품 참조는 거부됩니다.

## 물리 주소

- `A1`부터 `J30`: 브레드보드 홀입니다. 각 번호 열에서 `A-E`와 `F-J`는
  서로 분리된 접점 그룹입니다.
- 운영 엔진의 전원 레일 주소는 `T+1`~`T+25`, `T-1`~`T-25`,
  `B+1`~`B+25`, `B-1`~`B-25`를 사용합니다.
- `GND_P1`, `5V` 같은 Arduino 핀은 보드 핀입니다.
- 중복될 수 있는 Arduino 아날로그·디지털 핀 이름은 `BOARD:A1`,
  `BOARD:D3`처럼 명시할 수 있습니다. 접두사가 없으면 `A1`~`J30`은
  브레드보드 홀을 뜻합니다.

## 배치 규칙

운영 엔진은 실제 3D 자산의 핀 피치, 부품 크기, keep-out 여백과
브레드보드 모델 좌표를 사용합니다. 서로 겹치거나 보드 외곽을 벗어나는
후보는 거부합니다. 현재 5mm LED, 220Ω 저항, HC-SR04 헤더를 지원합니다.

## 경고 코드

| 코드 | 심각도 | 의미 |
| --- | --- | --- |
| `PIN_DUPLICATE` | WARNING | 하나의 핀에 둘 이상의 배선이 직접 연결됨 |
| `POWER_GROUND_SHORT` | ERROR | 전원과 GND가 같은 전기 노드에 속함 |
| `LED_REVERSED` | ERROR | LED 애노드와 캐소드의 극성이 반대로 연결됨 |
| `LED_RESISTOR_MISSING` | ERROR | LED에 전류 제한 저항이 직렬로 연결되지 않음 |
| `SENSOR_PIN_ROLE` | ERROR | 센서의 전원 또는 신호 핀이 잘못된 역할의 핀에 연결됨 |
| `ASSEMBLY_VALID` | INFO | 치명적인 조립 오류가 발견되지 않음 |

잘못된 주소와 구현할 수 없는 다리 간격 후보는 계획 반환 전에 거부됩니다.
배치할 수 없는 부품은 `failed` 상태와 실패 코드, 사용자 해결 안내를 포함한
부분 계획으로 반환됩니다.

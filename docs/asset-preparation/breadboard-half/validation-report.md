# 하프 브레드보드 3D 자산 후보

## 결과

- 부품: 하프 사이즈 브레드보드
- 부품 slug: `breadboard-half`
- 브랜치: `feat/asset-breadboard-jumper`
- 상태: `candidate`
- 제작 도구: Blender 5.2 LTS
- 원본 작업 흐름: Bambu Studio를 통해 STEP을 가져온 뒤 Blender에서 정규화

## 출처와 라이선스

- 원본 모델: [Half Breadboard — GrabCAD Community Library](https://grabcad.com/library/half-breadboard-1)
- 원본 소유권: 제3자 사용자가 제출한 자료
- 기록된 허가: GrabCAD Community 안내에서는 Library 모델을 개인 용도로 무료 사용할 수 있다고 설명함
- 라이선스 검토 상태: `pending`

접근 가능한 모델 페이지에는 오픈소스, 재배포 또는 상업적 이용에 관한 명시적인
라이선스가 표시되어 있지 않습니다. 따라서 정규화한 GLB는 계속 후보 상태로 유지하며,
팀이 저장소 재배포 허용 여부를 확인하거나 적절한 라이선스의 자산으로 교체하기 전에는
`approved`로 승격하면 안 됩니다.

## 정규화된 자산

- 런타임 좌표계: 오른손 좌표계
- 런타임 위쪽 축: `+Y`
- 런타임 앞쪽 축: `+Z`
- 런타임 단위: 미터
- 측정한 런타임 경계: `X/Y/Z` 기준 `83.01 x 9.51 x 56.08 mm`
- 원점: 상단 삽입면의 중앙
- 원점에서 몸체가 향하는 방향: 런타임 `-Y`
- GLB SHA-256: `09574a9d7b95d22dec389cef3048615289c18bcd4ed12287323bd4e223b1de76`

## 터미널 홀 보정

- Empty 이름: `pin_A1`부터 `pin_J30`
- 터미널 Empty 수: 300
- 전원 레일 Empty 수: 100
- 전체 Empty 수: 400
- Empty 기준 데이터: GLB 노드 변환값
- 런타임 바깥 방향: `[0, 1, 0]`
- 열 시작점: `X = -37.495 mm`
- 열 간격: `2.54 mm`
- 열 계산식: `X(column) = -37.495 + (column - 1) * 2.54 mm`
- A1에서 A30까지의 거리: `73.66 mm`

측정한 제작 좌표계의 행 위치:

| 행 | Y(mm) |
| --- | ---: |
| A | 14.725 |
| B | 12.185 |
| C | 9.645 |
| D | 7.105 |
| E | 4.565 |
| F | -3.235 |
| G | -5.775 |
| H | -8.315 |
| I | -10.855 |
| J | -13.395 |

런타임 변환식은 `[authoring X, authoring Z, -authoring Y]`입니다.

## 전기 연결

- 각 열에는 내부적으로 연결된 `A-E` 그룹 하나가 있습니다.
- 각 열에는 내부적으로 연결된 `F-J` 그룹 하나가 있습니다.
- 터미널 그룹은 총 60개입니다.
- 각 터미널 그룹에는 홀 5개가 있습니다.
- 전원 레일 4개 행은 각각 서로 분리된 5홀 구간 5개로 구성됩니다.
- 기록된 전원 레일 구간은 총 20개입니다.
- 서로 다른 레일 구간과 서로 다른 양극·음극 행은 전기적으로 절연됩니다.

## 소켓과 점퍼 결합

- 측정한 정사각 소켓 입구: `0.723666 x 0.723666 mm`
- 측정한 모델 삽입 깊이: `7.09568 mm`
- 런타임 바깥 방향 축: `+Y`
- 런타임 삽입 방향 축: `-Y`
- 기준 수 점퍼 단면: `0.64 x 0.64 mm`
- 전체 단면 여유: `0.083666 mm`
- 중앙 정렬 시 한쪽당 여유: `0.041833 mm`
- 형상 결합 결과: `PASS`
- 기계 판독용 명세:
  `assets_db/db_scripts/jumper_connectors/breadboard-half-jumper-fit.json`

`0.64 mm` 정사각 수 핀과 `2.54 mm` 간격은 Molex 제품 명세
`PS-10-07-001`과 Amphenol BergStik 문서를 근거로 합니다. Harwin M20 암 크림프
접점도 `2.54 mm` 간격의 `0.64 mm` 정사각 결합 핀을 명시합니다. 이 결과는 형상만
검증합니다. 원본 메시는 브레드보드 내부 금속 스프링 접점을 모델링하지 않았으므로
삽입력과 인출력은 이 검증 범위에 포함되지 않습니다.

## 시각적 검사

- 선택한 GLB 홀 형상을 기준으로 A1, E1, F1, J1을 배치했습니다.
- A2를 통해 `2.54 mm` 간격을 확인했습니다.
- D17, H23, J30을 실제 GLB 홀 중심과 비교했습니다.
- Asset Lab에서 터미널 홀 Empty 300개와 전원 레일 Empty 100개가 포함된 최종 후보를 불러왔습니다.
- 빨간색 GLB `pin_*` 마커와 청록색 메타데이터 마커가 모델의 홀 중심에서 겹칩니다.
- 전체 화면 근거 자료: `evidence/asset-lab-full.png`
- 터미널 및 전원 레일 확대 근거 자료: `evidence/asset-lab-pin-closeup.png`

## 검증 명령

```powershell
python assets_db/db_scripts/validate_breadboard_half_candidate.py
python assets_db/db_scripts/validate_component_3d_metadata.py
python assets_db/db_scripts/validate_3d_pin_anchors.py
python assets_db/db_scripts/validate_pin_coordinates.py
python assets_db/db_scripts/validate_3d_models.py
pnpm --dir frontend run build
```

위에 나열한 모든 데이터 검증과 프론트엔드 운영 빌드가 통과합니다.

## 남은 검토 항목

- 실제 소켓 입구와 사용 가능한 삽입 깊이를 측정해야 합니다. 후보 메타데이터에서는 이 값을 `null`로 유지합니다.
- GrabCAD 기반 메시의 재배포 허가를 확인하거나 승인 전에 적절한 라이선스의 원본으로 교체해야 합니다.
- 삽입력과 인출력 검증이 필요하다면 사용할 실제 점퍼 제품을 확정해야 합니다.

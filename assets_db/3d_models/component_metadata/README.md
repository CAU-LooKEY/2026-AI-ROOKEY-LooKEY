# 3D Component Metadata Standard

이 폴더는 GLB 부품을 자동 배치하고 핀, 소켓, 점퍼선을 연결하기 위한 기계 판독용 메타데이터를 관리합니다.

기존 부품 카탈로그는 이름, 분류, 설명, 검색 키워드와 전기적 핀 목록을 담당합니다. 이 규격은 해당 정보를 복제하지 않고 다음의 3D 조립 정보만 담당합니다.

- GLB 파일과 정확한 파일 버전
- 실제 치수와 측정 근거
- Blender 제작 좌표계와 최종 GLB 좌표계
- 원점과 기본 방향
- 핀의 위치, 방향, 암수, 형태, 삽입 정보
- 브레드보드 배치 및 회전 정책
- 작성자, 측정 방법, 검수 상태

## 폴더 구조

~~~text
component_metadata/
|-- schema/
|   +-- component-3d-metadata.schema.json
|-- templates/
|   +-- component-3d-metadata.template.json
|-- examples/
|   +-- led-5mm-blue.projected-2d.example.json
|-- candidates/
|   +-- <component-slug>/<github-id>-<method>.json
+-- approved/
    +-- <component-slug>.json
~~~

examples는 형식 설명용이며 제품 데이터가 아닙니다. candidates에는 팀원별 측정안을 서로 덮어쓰지 않고 올립니다. 리뷰가 끝난 좌표 하나만 approved로 승격합니다.

## 좌표계

Blender 제작 좌표와 최종 GLB 좌표를 섞지 않습니다.

| 단계 | 오른쪽 | 위 | 앞 | 기본 단위 |
| --- | --- | --- | --- | --- |
| Blender authoring | +X | +Z | -Y | mm |
| GLB runtime | +X | +Y | +Z | m |

핀 position과 outwardDirection은 항상 coordinateSystems.runtime, 즉 최종 GLB model-local 좌표로 저장합니다. Three.js scene/world 좌표나 Blender 화면 좌표를 저장하면 안 됩니다.

승인 데이터는 GLB 1 unit = 1 m를 사용하므로 modelUnitsPerMillimeter 값은 0.001이어야 합니다. 기존처럼 크기가 보정되지 않은 모델은 model-unit으로 후보나 예제만 만들 수 있습니다.

## 원점 규칙

모든 부품에 무조건 body-bottom-center를 적용하지 않습니다. 조립할 때 가장 안정적인 기준면을 사용합니다.

- Arduino, 센서 모듈: mounting-surface-center
- Breadboard: 부품을 꽂는 윗면 중심인 mounting-surface-center
- LED, 저항, 버튼처럼 몸체와 리드가 분리된 부품: body-bottom-center
- 특수 부품: custom과 설명을 함께 사용

normalized가 true이면 referencePoint는 GLB 로컬 원점 [0, 0, 0]이어야 합니다.

## 방향 규칙

팀 문서의 방향 표시는 orientation.markers에 기록합니다.

- Arduino UNO: USB 포트가 기본 자세의 왼쪽
- Breadboard: A1이 기본 화면 기준 왼쪽 위
- HC-SR04: 센서 면이 앞을 향하고 핀 순서는 VCC, TRIG, ECHO, GND
- LED: 긴 리드 ANODE가 오른쪽

카메라 Yaw, Pitch, FOV는 썸네일 렌더링 규칙입니다. GLB 조립 좌표나 핀 위치에는 포함하지 않습니다.

## 핀과 커넥터

각 핀에는 다음 값이 필요합니다.

- pinKey: 기존 부품 카탈로그와 동일한 고정 키
- nodeName: GLB에 내보낼 Blender Empty 이름. pin_ 접두사를 사용
- position: 실제 접촉점의 최종 GLB 로컬 좌표
- outwardDirection: 부품 몸체에서 핀 끝 또는 결합 상대 방향으로 향하는 단위 벡터
- connector.gender: male, female, genderless, unknown
- connector.form: lead, pin, socket, hole, pad, wire-end 등
- electrical: 전원, 접지, 신호, 수동소자 역할과 별칭
- mounting: 브레드보드 호환 여부와 삽입 깊이

점퍼선은 양 끝을 각각 connector로 표현합니다. 예를 들어 수-암 점퍼선은 한쪽 끝을 male/wire-end, 다른 쪽 끝을 female/wire-end로 관리합니다.

## Blender 작업 순서

1. Scene Units를 Metric으로 설정하고 실제 치수를 mm 기준으로 맞춥니다.
2. +X 오른쪽, +Z 위, -Y 앞 방향으로 부품의 기본 자세를 맞춥니다.
3. 부품 종류에 맞는 기준점을 원점으로 정하고 Location, Rotation, Scale 변환을 적용합니다.
4. 각 전기 접촉점에 Empty를 만들고 pin_<pin_key_lowercase>로 이름을 지정합니다.
5. Empty의 로컬 +Z가 몸체에서 접촉점 바깥쪽으로 향하도록 회전시킵니다.
6. Empty를 포함해 GLB로 내보냅니다.
7. 최종 GLB를 Three.js 또는 검수 도구에서 불러와 핀 좌표를 추출합니다.
8. 후보 JSON에 GLB SHA-256과 측정 방법을 기록합니다.

GLB를 다시 내보내면 해시가 바뀌므로 기존 좌표를 그대로 승인할 수 없습니다. 새 해시 기준으로 다시 검수해야 합니다.

## 후보 제출

템플릿을 복사해 다음 경로에 추가합니다.

~~~text
assets_db/3d_models/component_metadata/candidates/<component-slug>/<github-id>-<method>.json
~~~

예:

~~~text
candidates/led-5mm-blue/kimnakyung-blender-empty.json
candidates/led-5mm-blue/tmd9898-threejs-picker.json
~~~

기존 legacy pin anchor JSON이나 집계 파일은 후보 제출 과정에서 수정하지 않습니다.

## 승인 기준

approved 데이터는 다음 조건을 만족해야 합니다.

- GLB가 실제 크기이며 runtime 단위가 meter
- modelUnitsPerMillimeter가 0.001
- 모델 원점과 기본 방향이 정규화됨
- GLB 해시가 현재 파일과 일치함
- 기존 부품 카탈로그의 모든 핀이 중복 없이 존재함
- 각 핀 방향 벡터가 단위 벡터임
- 핀 confidence가 0.8 이상임
- projected-2d 방식이 아님
- 브레드보드 호환 male 핀은 삽입 깊이가 기록됨

## 검증

저장소 루트에서 실행합니다.

~~~powershell
python assets_db/db_scripts/validate_component_3d_metadata.py
~~~

이 검사는 파일 경로, GLB 해시, 단위, 좌표와 방향 벡터, 핀 중복, 기존 핀 카탈로그 일치 여부, 상태별 승인 조건을 확인합니다.

전체 에셋 검사와 CI에서 사용하는 통합 명령은 다음과 같습니다.

~~~bash
python3 assets_db/db_scripts/validate_assets.py --mode all
~~~

- `pr`: 변경된 GLB에 candidate 또는 approved 메타데이터가 없으면 실패
- `all`: 현재 전체 데이터의 무결성을 검사하고 기존 메타데이터 누락은 경고
- `release`: 모든 GLB에 approved 메타데이터가 없으면 실패

통합 검사는 GLB 내부 `pin_*` 노드의 translation과 메타데이터 position을
2µm 허용 오차로 비교합니다. 실제 크기 메타데이터는 GLB manifest bounds와
0.25mm 또는 2% 중 큰 허용 오차로 비교하며, JSON과 Markdown 리포트를 함께
생성합니다.

## 이후 연결

AI 회로 응답은 부품 이름만 반환하지 않고 instanceId, componentSlug, pinKey, net을 반환해야 합니다. 배치 엔진은 approved 메타데이터의 핀 좌표와 브레드보드 홀 좌표를 결합해 GLB 위치와 점퍼선 경로를 계산합니다. 전기 시뮬레이션용 netlist와 3D 배치 데이터는 별도 계층으로 유지합니다.

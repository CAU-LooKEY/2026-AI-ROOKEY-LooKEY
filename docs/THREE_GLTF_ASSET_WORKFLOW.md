# Three.js GLB Asset Workflow

## 목적

팀원이 제작한 센서, 저항, 스위치 등의 GLB를 기존 2D 회로와 독립적으로 검사합니다. 저장소에 추가된 GLB는 3D Asset Lab 목록에 자동으로 나타납니다.

## 파일 추가

GLB 파일명은 componentSlug와 같아야 합니다.

~~~text
assets_db/3d_models/glb/<component-slug>.glb
~~~

예:

~~~text
assets_db/3d_models/glb/dht11.glb
assets_db/3d_models/glb/resistor-220-ohm.glb
assets_db/3d_models/glb/pushbutton-6x6.glb
~~~

프론트엔드 폴더에 모델을 복사하지 않습니다. Vite의 import.meta.glob이 위 폴더를 자동으로 읽어 개발 서버와 빌드 자산으로 변환합니다.

## 미리보기

저장소 루트 기준:

~~~powershell
cd frontend
npm install
npm run dev
~~~

브라우저에서 다음 주소를 엽니다.

~~~text
http://127.0.0.1:5173/assets-3d
~~~

저장소에 넣기 전 파일은 Local GLB 버튼으로 임시 확인할 수 있습니다.

## Blender 출력 기준

1. 실제 치수를 맞추고 Location, Rotation, Scale 변환을 적용합니다.
2. 제작 좌표는 +X 오른쪽, +Z 위, -Y 앞을 사용합니다.
3. 부품 종류에 맞는 원점을 설정합니다.
4. 핀 접촉점에 pin_<pin_key_lowercase> 이름의 Empty를 추가합니다.
5. Empty의 로컬 +Z가 몸체에서 핀 끝 방향을 향하게 합니다.
6. glTF 2.0 Binary 형식으로 Empty를 포함해 내보냅니다.
7. 재질은 glTF metallic-roughness를 사용합니다.
8. KHR_materials_pbrSpecularGlossiness 구형 확장은 사용하지 않습니다.
9. 텍스처는 GLB 안에 포함하고 외부 절대 경로를 남기지 않습니다.

현재 로더에는 Draco 압축 디코더를 연결하지 않았으므로 Draco를 켜지 않습니다. 압축 로더를 추가하기 전까지는 일반 GLB로 출력합니다.

## 검사 항목

- 모델이 비어 있지 않고 재질이 표시되는가
- 원점 축과 모델의 기준점이 일치하는가
- 모델 bounds가 실물 비율과 맞는가
- GLB 안에 pin_* 노드가 존재하는가
- 메타데이터 핀과 GLB 핀 노드가 같은 위치인가
- 알 수 없는 glTF 확장 경고가 없는가
- 모델 파일 크기가 과도하지 않은가

목표 파일 크기는 부품당 5 MB 이하입니다. 10 MB가 넘으면 메시 단순화, 중복 메시 제거, 텍스처 해상도 축소를 먼저 검토합니다.

## 메타데이터 연결

GLB 추가 후 다음 템플릿으로 후보 좌표를 만듭니다.

~~~text
assets_db/3d_models/component_metadata/templates/component-3d-metadata.template.json
~~~

팀원별 후보는 다음 위치에 추가합니다.

~~~text
assets_db/3d_models/component_metadata/candidates/<component-slug>/<github-id>-<method>.json
~~~

검증:

~~~powershell
python assets_db/db_scripts/validate_component_3d_metadata.py
~~~

Asset Lab은 approved를 가장 먼저 사용하고, approved가 없으면 candidate, example 순서로 하나의 메타데이터를 표시합니다.

## 표시 의미

- 빨간색 채움 점: GLB 내부의 pin_* 노드
- 청록색 테두리 점: JSON 메타데이터에 저장된 핀 좌표
- 두 점이 겹침: GLB와 메타데이터 좌표가 일치
- 두 점이 떨어짐: 좌표계, 스케일 또는 측정 좌표 재검수 필요

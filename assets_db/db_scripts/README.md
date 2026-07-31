# Supabase DB 스크립트

회로 에셋 패키지를 Supabase에 적재하기 위한 DB 스크립트 폴더입니다.

## 파일 설명

- `001_schema.sql`
  Storage 버킷, 부품 테이블, 이미지 테이블, 핀 테이블, 읽기 정책을 만듭니다.
  핀 테이블에는 2D 좌표 `x_px`, `y_px`와 선택형 3D 좌표 `x_3d`, `y_3d`,
  `z_3d`가 포함되어 있습니다.
- `002_seed_assets_and_pins.sql`
  현재 부품 메타데이터, 이미지 경로, 핀 좌표를 insert/upsert합니다.
- `003_add_optional_3d_pin_columns.sql`
  이미 예전 schema를 실행한 DB에 3D 핀 좌표 컬럼만 추가하기 위한 보정
  스크립트입니다.
- `004_add_models_and_breadboard_layouts.sql`
  이미 예전 schema를 실행한 DB에 GLB 모델 metadata 테이블과 브래드보드 layout
  테이블을 추가하기 위한 보정 스크립트입니다.
- `005_seed_breadboards_and_models.sql`
  일반/긴 브래드보드 metadata, procedural layout, 대표 anchor pin, GLB model
  metadata를 insert/upsert합니다.
- `006_seed_3d_pin_anchors.sql`
  기존 2D 핀 좌표를 GLB bounds에 투영해 만든 draft 3D pin anchor를
  `circuit_component_pins.x_3d`, `y_3d`, `z_3d`에 업데이트합니다.
- `pin_coordinates/*.json`
  부품별 핀 좌표 export 파일입니다.
- `breadboard_layouts/*.json`
  모든 브래드보드 홀 좌표를 계산하기 위한 procedural layout export 파일입니다.
- `all_component_pin_coordinates.json`
  모든 부품의 핀 좌표를 합친 JSON 파일입니다.
- `image_processing_manifest.json`
  원본 이미지 처리와 출력 파일 경로를 기록한 manifest입니다.
- `validate_pin_coordinates.py`
  좌표가 이미지 범위 안에 있는지 확인하는 로컬 검증 스크립트입니다.
- `validate_3d_models.py`
  GLB 파일 header, 파일 길이, bounds metadata, ready 모델 크기를 확인하는 로컬
  검증 스크립트입니다.
- `generate_3d_pin_anchors.py`
  2D 핀 좌표와 GLB bounds를 이용해 draft 3D pin anchor JSON과 SQL을 생성합니다.
- `validate_3d_pin_anchors.py`
  생성된 3D pin anchor가 GLB bounds 안에 있는지 검증합니다.
- `validate_component_3d_metadata.py`
  후보·승인 메타데이터의 스키마, 단위, 원점, 방향, 핀과 승인 조건을
  검증합니다.
- `validate_breadboard_half_candidate.py`
  half breadboard의 2.54mm 피치, 분리 레일, 핀 노드와 점퍼 삽입 규격을
  검증합니다.
- `validate_assets.py`
  위 검사기를 하나의 명령으로 실행하고 GLB·manifest·메타데이터 대응 및
  GLB 내부 `pin_*` 노드 좌표까지 검증한 뒤 JSON/Markdown 리포트를 만듭니다.

## 통합 에셋 승인 검사

일상적인 전체 검사는 저장소 루트에서 다음과 같이 실행합니다.

~~~bash
python3 assets_db/db_scripts/validate_assets.py --mode all
~~~

결과는 `artifacts/asset-validation/` 아래 JSON과 Markdown으로 생성됩니다.
이 경로는 빌드 산출물이므로 Git에 커밋하지 않습니다.

PR에서는 기준 커밋 이후 변경된 GLB에 candidate 또는 approved 메타데이터가
반드시 있어야 합니다.

~~~bash
python3 assets_db/db_scripts/validate_assets.py --mode pr --base-ref origin/main
~~~

모든 GLB에 approved 메타데이터가 준비됐는지 확인하는 릴리스 게이트는 별도로
실행합니다. 현재 미승인 에셋이 있으면 의도적으로 실패합니다.

~~~bash
python3 assets_db/db_scripts/validate_assets.py --mode release
~~~

검증 정책의 자동 테스트는 다음 명령으로 실행합니다.

~~~bash
python3 -m unittest discover -s assets_db/tests -v
~~~

## 실행 순서

처음부터 새 Supabase DB에 넣는 경우:

1. Supabase SQL Editor에서 `001_schema.sql`을 실행합니다.
2. `../2d_svgs/raster_sources/` 안의 파일을 Storage 버킷
   `circuit-assets/raster_sources/`에 업로드합니다.
3. `../2d_svgs/react_flow_nodes/` 안의 파일을 Storage 버킷
   `circuit-assets/react_flow_nodes/`에 업로드합니다.
4. `assets_db/3d_models/glb/` 안의 파일을 Storage 버킷
   `circuit-assets/3d_models/glb/`에 업로드합니다.
5. `002_seed_assets_and_pins.sql`을 실행합니다.
6. `005_seed_breadboards_and_models.sql`을 실행합니다.
7. `006_seed_3d_pin_anchors.sql`을 실행합니다.
8. 좌표나 이미지가 바뀌면 로컬에서 `python validate_pin_coordinates.py`를
   실행합니다.
9. GLB가 바뀌면 로컬에서 `python validate_3d_models.py`를 실행합니다.
10. 3D anchor가 바뀌면 로컬에서 `python validate_3d_pin_anchors.py`를 실행합니다.

이미 이전 버전의 `001_schema.sql`을 실행한 DB라면, seed 실행 전에
`003_add_optional_3d_pin_columns.sql`과 `004_add_models_and_breadboard_layouts.sql`을
한 번씩 실행하세요.

현재 Storage 허용 MIME 타입은 `image/png`, `image/jpeg`, `image/svg+xml`,
`model/gltf-binary`입니다.

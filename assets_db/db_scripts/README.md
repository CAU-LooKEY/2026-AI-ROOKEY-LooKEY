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
7. 좌표나 이미지가 바뀌면 로컬에서 `python validate_pin_coordinates.py`를
   실행합니다.
8. GLB가 바뀌면 로컬에서 `python validate_3d_models.py`를 실행합니다.

이미 이전 버전의 `001_schema.sql`을 실행한 DB라면, seed 실행 전에
`003_add_optional_3d_pin_columns.sql`과 `004_add_models_and_breadboard_layouts.sql`을
한 번씩 실행하세요.

현재 Storage 허용 MIME 타입은 `image/png`, `image/jpeg`, `image/svg+xml`,
`model/gltf-binary`입니다.

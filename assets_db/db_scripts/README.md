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
- `pin_coordinates/*.json`
  부품별 핀 좌표 export 파일입니다.
- `all_component_pin_coordinates.json`
  모든 부품의 핀 좌표를 합친 JSON 파일입니다.
- `image_processing_manifest.json`
  원본 이미지 처리와 출력 파일 경로를 기록한 manifest입니다.
- `validate_pin_coordinates.py`
  좌표가 이미지 범위 안에 있는지 확인하는 로컬 검증 스크립트입니다.

## 실행 순서

처음부터 새 Supabase DB에 넣는 경우:

1. Supabase SQL Editor에서 `001_schema.sql`을 실행합니다.
2. `../2d_svgs/raster_sources/` 안의 파일을 Storage 버킷
   `circuit-assets/raster_sources/`에 업로드합니다.
3. `../2d_svgs/react_flow_nodes/` 안의 파일을 Storage 버킷
   `circuit-assets/react_flow_nodes/`에 업로드합니다.
4. `002_seed_assets_and_pins.sql`을 실행합니다.
5. 좌표나 이미지가 바뀌면 로컬에서 `python validate_pin_coordinates.py`를
   실행합니다.

이미 이전 버전의 `001_schema.sql`을 실행한 DB라면, `002_seed_assets_and_pins.sql`
실행 전에 `003_add_optional_3d_pin_columns.sql`을 한 번 실행하세요.

현재 Storage 허용 MIME 타입은 `image/png`, `image/jpeg`, `image/svg+xml`입니다.
GLB 같은 실제 3D 파일까지 Supabase Storage에서 제공하려면 별도의 모델 테이블과
`model/gltf-binary` 등 3D MIME 타입 허용을 추가해야 합니다.

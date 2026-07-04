# 회로 에셋 DB

하드웨어 회로 시각화를 위한 에셋 DB 패키지입니다. 현재 범위는 부품
메타데이터, 투명 배경 이미지, 핀 좌표, Supabase 적재 스크립트입니다.

## 포함된 부품

현재 seed 데이터에는 8개 부품과 대표 핀 총 98개가 들어 있습니다.

- Arduino Uno R3
- Arduino Nano
- HC-SR04 초음파 센서
- 5 mm 파란색 LED
- 6x6 푸쉬 버튼
- SG90 계열 서보모터
- 일반 브래드보드
- 긴 브래드보드

현재 확정된 핀 좌표는 투명 PNG 기준의 `x_px`, `y_px`입니다. 좌표 원점은
이미지의 왼쪽 위 `(0, 0)`입니다.

## 2.5D와 3D 좌표 기준

- 2.5D 아이소메트릭 회로도에서는 PNG 위의 연결점만 필요하므로
  `x_px`, `y_px`만으로 배치와 배선이 가능합니다.
- 실제 GLB/Blender 모델의 핀에 선을 꽂는 3D 회로도를 만들려면 모델 로컬
  좌표계 기준의 `x_3d`, `y_3d`, `z_3d`가 추가로 필요합니다.
- 위에서 찍은 사진 한 장만으로는 정확한 `z_3d`를 알 수 없습니다. 3D 좌표는
  GLB, Blender, VARCO 원본 모델에서 핀 앵커를 직접 찍어 추출해야 합니다.
- 그래서 DB에는 3D 핀 좌표를 저장할 수 있는 선택형 컬럼을 열어두었고,
  현재 값은 아직 비워두는 구조입니다.

## 브래드보드 좌표 기준

브래드보드는 LED나 푸쉬 버튼처럼 한두 개 핀을 가진 부품이 아니라, 연결 가능한
홀이 수백 개 있는 부품입니다. 그래서 모든 홀을 `circuit_component_pins` row로
저장하지 않고, `db_scripts/breadboard_layouts/`에 procedural layout으로 저장했습니다.

- `circuit_component_pins`: 프론트/백엔드가 바로 참조할 수 있는 대표 anchor 핀만 저장
- `circuit_breadboard_layouts`: 전체 홀 좌표를 계산하기 위한 행/열/전원레일 규칙 저장

즉, 브래드보드에는 좌표가 필요하지만 수작업 핀 좌표를 전부 찍는 방식은 권장하지
않습니다.

## 폴더 구조

- `2d_svgs/`
  투명 PNG 원본, React Flow용 SVG 래퍼, 핀맵 확인용 미리보기 이미지가
  들어 있습니다.
- `db_scripts/`
  Supabase schema, seed SQL, 핀 좌표 JSON, 검증 스크립트가 들어 있습니다.
- `3d_models/`
  선별한 GLB 모델, GLB audit report, 모델 manifest가 들어 있습니다.

## 주의사항

- SVG 파일은 투명 PNG를 감싼 노드용 파일입니다. Supabase seed SQL을 실행하기
  전에 PNG와 SVG를 Storage에 먼저 업로드해야 합니다.
- LED 이미지는 엄밀한 위쪽 사진이 아니라 사선 사진이라, 현재 좌표는
  프로토타입용입니다. 배포 전에는 위에서 찍은 투명 PNG로 교체하는 것을
  권장합니다.
- Arduino 계열 이미지에는 상표/로고 이슈가 있을 수 있으므로 공개 배포 전
  라이선스와 상표권 검토가 필요합니다.
- `breadboard-full.glb`는 구조상 정상 GLB지만 25MB라 웹 배포 전 최적화를
  권장하며, DB manifest에서도 `needs_optimization`으로 표시했습니다.

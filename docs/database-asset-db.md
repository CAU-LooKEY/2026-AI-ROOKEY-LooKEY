# 2.5D 회로 자산 DB

하드웨어 교육 챗봇에서 사용할 부품 에셋 DB 초안입니다. 프론트엔드와 백엔드는 다른 팀원이 만들고, 이 문서는 Supabase에 저장할 부품 이미지, 핀 좌표, 라이선스 상태를 관리하기 위한 기준입니다.

## 이번 1차 부품 범위

- `arduino-uno-r3`
- `arduino-nano`
- `breadboard-half`
- `hc-sr04`
- `led-5mm-red`
- `pushbutton-6x6`
- `servo-sg90`

LED와 푸쉬버튼은 점퍼선으로 직접 연결하기보다 브레드보드 위에 배치하는 회로가 자연스럽습니다. 그래서 브레드보드 이미지와 홀 좌표도 함께 관리해야 합니다.

## Supabase 구성

`supabase/migrations/20260702000000_circuit_asset_schema.sql`은 다음을 만듭니다.

- `circuit-assets` 스토리지 버킷
- `circuit_component_assets`
- `circuit_component_asset_images`
- `circuit_component_pins`
- 공개 읽기용 RLS 정책와 Data API `grant select`

초기 데이터는 `supabase/seed.sql`에 있습니다.

## ZIP 이미지 규칙

ZIP 파일 이름은 부품 slug와 같아야 합니다.

```txt
asset-import/
  arduino-uno-r3.zip
  arduino-nano.zip
  breadboard-half.zip
  hc-sr04.zip
  led-5mm-red.zip
  pushbutton-6x6.zip
  servo-sg90.zip
```

ZIP 내부 파일 예시:

```txt
isometric.png
preview-3d.jpg
schematic.png
```

파일명에 `3d` 또는 `preview`가 있으면 `preview_3d`, `schematic` 또는 `symbol`이 있으면 `schematic_2d`, 그 외 이미지는 `isometric_2d`로 저장됩니다.

## 이미지 확장자

현재 운영 규칙은 PNG/JPEG만 허용합니다.

- 회로도 배치용 메인 이미지는 투명 PNG 권장
- 3D처럼 보이는 미리보기 이미지는 JPEG 가능
- STL/GLB/GLTF는 이번 DB 흐름에 넣지 않음

여기서 말하는 “3D 이미지”는 실제 3D 모델 파일이 아니라, Blender/VARCO에서 고정 카메라 각도로 렌더링한 PNG/JPEG 이미지입니다.

## 핀 좌표

핀 좌표는 최종 이미지의 왼쪽 위를 기준으로 한 픽셀 좌표입니다. 이미지 crop, padding, export size가 바뀌면 좌표도 다시 보정해야 합니다.

ZIP 업로드만으로 핀 좌표가 자동 생성되지는 않습니다. 새 부품은 최초 1회 핀 중심 좌표를 직접 찍거나 검수해야 합니다.

## 검증

```bash
pnpm validate:pins
pnpm typecheck
pnpm build
```

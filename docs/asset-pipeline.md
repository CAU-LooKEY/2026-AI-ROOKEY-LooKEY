# 회로 자산 파이프라인

## Supabase 모델

파일은 공개 `circuit-assets` 버킷에 저장하고 렌더링 메타데이터는 다음 테이블에 저장합니다.

- `circuit_component_assets`: 부품당 한 행
- `circuit_component_asset_images`: 이미지 변형당 한 행
- `circuit_component_pins`: 연결 가능한 핀당 한 행

프론트엔드는 RLS 정책을 통해 `ready` 상태인 자산만 읽습니다. 업로드할 때는
`npm run upload:assets`를 통해 서버 전용 `SUPABASE_SERVICE_ROLE_KEY`를 사용해야 합니다.

## ZIP 가져오기 구조

ZIP 파일을 `asset-import/`에 넣습니다. ZIP 파일 이름은 부품 slug와 같아야 합니다.

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

각 ZIP의 내부 구조:

```txt
isometric.png
preview-3d.jpg
schematic.png
```

파일 이름에 `3d` 또는 `preview`가 포함되면 `preview_3d`, `schematic` 또는
`symbol`이 포함되면 `schematic_2d`, 나머지 지원 이미지는 `isometric_2d`가 됩니다.

## 이미지 형식

이 프로젝트의 ZIP 가져오기에서는 PNG와 JPEG만 허용합니다.

- 가능하면 주요 2.5D 회로도 자산에는 투명 PNG를 사용합니다.
- 불투명한 3D 형태의 미리보기 렌더에는 JPEG만 사용합니다.
- 이 DB 흐름의 ZIP에는 STL, GLB, GLTF, WebP, SVG, PDF를 넣지 않습니다.

여기서 “3D 이미지”는 3D 모델 파일이 아니라 고정된 3D 카메라 각도에서 렌더링한 PNG/JPEG를 뜻합니다.

## 핀 좌표

모든 핀 위치는 최종적으로 잘라낸 자산 이미지 기준의 픽셀 좌표입니다. PNG의
자르기 영역, 여백 또는 내보내기 크기가 변경되면 `x_px`, `y_px`를 다시 보정해야 합니다.

ZIP을 업로드한다고 해서 임의 이미지에서 정확한 핀 중심이 자동으로 검출되지는 않습니다.
업로드 스크립트는 파일을 자동 저장할 수 있지만, 핀 좌표는 다음 출처 중 하나에서 가져와야 합니다.

1. `arduino-uno-r3` 같은 부품 slug별 사전 정의 템플릿
2. 각 핀 중심을 한 번씩 클릭하는 수동 보정
3. 컴퓨터 비전 보조 도구로 검출한 뒤 사람의 검수

교육용 회로에서 정확한 핀 좌표는 사람이 작성하고 검증하는 메타데이터로 취급해야 합니다.

권장 작업 흐름:

1. 모든 부품을 고정된 픽셀 크기로 내보냅니다.
2. 투명 여백 규칙을 일관되게 유지합니다.
3. 각 핀 중심을 이미지 픽셀 좌표로 기록합니다.
4. 프롬프트 해석에 사용할 `13`, `GPIO17`, `SDA`, `GND` 같은 별칭을 저장합니다.

## 초기 자산 목록

현재 첫 번째 자산 묶음은 다음과 같습니다.

- `arduino-uno-r3`
- `arduino-nano`
- `breadboard-half`
- `hc-sr04`
- `led-5mm-red`
- `pushbutton-6x6`
- `servo-sg90`

생성 회로에서 LED와 푸시 버튼은 일반적으로 브레드보드를 통해 배치해야 합니다.
초기 프로토타입에서도 브레드보드 이미지에 보정된 홀 좌표나 대표 기준 홀이 필요합니다.

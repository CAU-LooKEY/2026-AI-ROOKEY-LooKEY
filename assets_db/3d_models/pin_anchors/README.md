# 3D Pin Anchors

이 폴더에는 GLB 모델 로컬 좌표계 기준의 draft 핀 anchor가 들어 있습니다.

## 생성 방식

현재 값은 사람이 GLB에서 직접 클릭해 찍은 최종 좌표가 아니라, 기존 2D 핀 좌표
`x_px`, `y_px`를 각 GLB의 bounds에 투영해 만든 초안입니다.

```text
2D image pin coordinate -> normalized x/y -> GLB bounds axis mapping -> x_3d/y_3d/z_3d
```

따라서 프로토타입 3D wire snapping에는 사용할 수 있지만, 최종 배포 전에는
Blender 또는 Three.js calibration view에서 실제 핀/홀 중심과 맞는지 검수해야
합니다.

## 파일

- `<component-slug>-3d-pin-anchors.json`
  부품별 3D 핀 anchor입니다.
- `all_3d_pin_anchors.json`
  모든 부품의 anchor를 합친 파일입니다.

Supabase에는 `db_scripts/006_seed_3d_pin_anchors.sql`을 실행해 반영합니다.

# 2D 에셋

프론트엔드 회로 노드에서 사용할 시각 에셋을 모아둔 폴더입니다.

## 하위 폴더

- `raster_sources/`
  각 부품의 투명 배경 PNG 원본 이미지입니다.
- `react_flow_nodes/`
  React Flow 노드처럼 사용할 수 있는 SVG 래퍼입니다. 부품 크기를 유지하고
  핀 위치를 표시할 수 있게 구성했습니다.
- `pin_map_previews/`
  좌표가 제대로 찍혔는지 확인하기 위한 핀맵 미리보기 이미지입니다.

## 좌표계

모든 2D 핀 좌표는 `raster_sources/`의 투명 PNG를 기준으로 측정했습니다.
원점은 이미지 왼쪽 위입니다.

```text
x: 왼쪽에서 오른쪽
y: 위에서 아래
```

프론트엔드에서 이미지를 다른 크기로 렌더링할 경우, `db_scripts`의 JSON 또는
DB 값을 이미지 크기 비율에 맞춰 스케일링하면 됩니다.

## Supabase Storage 경로

Supabase Storage 버킷 이름은 `circuit-assets`입니다. 업로드할 때는 아래처럼
버킷 내부 경로를 유지하세요.

- `raster_sources/<component-slug>-top.png`
- `react_flow_nodes/<component-slug>.svg`

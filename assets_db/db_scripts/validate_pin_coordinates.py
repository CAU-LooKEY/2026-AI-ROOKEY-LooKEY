from pathlib import Path
import json
from PIL import Image

root = Path(__file__).resolve().parents[1]
coords_dir = root / 'db_scripts' / 'pin_coordinates'
errors = []
for path in sorted(coords_dir.glob('*-pin-coordinates.json')):
    data = json.loads(path.read_text(encoding='utf-8'))
    image_path = root.parent / data['image']['path'] if not Path(data['image']['path']).is_absolute() else Path(data['image']['path'])
    if not image_path.exists():
        errors.append(f'{path.name}: missing image {image_path}')
        continue
    img = Image.open(image_path)
    width, height = img.size
    if width != data['pixel_width'] or height != data['pixel_height']:
        errors.append(f'{path.name}: image size mismatch {width}x{height} != {data["pixel_width"]}x{data["pixel_height"]}')
    for pin in data['pins']:
        x, y = pin['x_px'], pin['y_px']
        if not (0 <= x < width and 0 <= y < height):
            errors.append(f'{path.name}: pin {pin["pin_key"]} out of bounds ({x}, {y})')
if errors:
    raise SystemExit('\n'.join(errors))
print(f'Validated {len(list(coords_dir.glob("*-pin-coordinates.json")))} coordinate files.')

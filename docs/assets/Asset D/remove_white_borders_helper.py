from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_propagation

INPUT_DIR = Path('/mnt/data/asset_d_bgremoved')
OUTPUT_DIR = Path('/mnt/data/asset_d_no_white_borders')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Near-white pixels at the edge of extracted artwork are treated as matte/border.
# Because the flood fill starts from already-transparent background, interior whites
# such as the Unique 6★ singularity are retained unless connected to the outside.
WHITE_MIN = 235
CHROMA_MAX = 35
CROP_PADDING = 24

outputs = []
for src in sorted(INPUT_DIR.glob('asset-d-unique-*-bgremoved.png')):
    img = Image.open(src).convert('RGBA')
    arr = np.array(img)
    alpha = arr[:, :, 3]
    rgb = arr[:, :, :3].astype(np.int16)
    chroma = rgb.max(axis=2) - rgb.min(axis=2)

    transparent_seed = alpha == 0
    near_white = (rgb.min(axis=2) > WHITE_MIN) & (chroma < CHROMA_MAX) & (alpha > 0)
    low_alpha_matte = (alpha > 0) & (alpha < 128)
    removable = near_white | low_alpha_matte

    reachable = binary_propagation(
        transparent_seed,
        structure=np.ones((3, 3), dtype=bool),
        mask=(transparent_seed | removable),
    )
    remove_mask = reachable & (alpha > 0)
    arr[remove_mask, 3] = 0

    out = Image.fromarray(arr, 'RGBA')
    bbox = out.getbbox()
    if bbox:
        left, top, right, bottom = bbox
        left = max(0, left - CROP_PADDING)
        top = max(0, top - CROP_PADDING)
        right = min(out.width, right + CROP_PADDING)
        bottom = min(out.height, bottom + CROP_PADDING)
        out = out.crop((left, top, right, bottom))

    dst_name = src.name.replace('-bgremoved', '-no-white-borders')
    dst = OUTPUT_DIR / dst_name
    out.save(dst)
    outputs.append(dst)

# Dark preview sheet
thumbs = []
for path in outputs:
    im = Image.open(path).convert('RGBA')
    im.thumbnail((360, 360), Image.LANCZOS)
    thumbs.append((path, im.copy()))

preview_w = 40 + len(thumbs) * 360 + (len(thumbs) - 1) * 40 + 40
preview_h = 450
preview = Image.new('RGB', (preview_w, preview_h), (5, 6, 10))
draw = ImageDraw.Draw(preview)
x = 40
for path, im in thumbs:
    preview.paste(im, (x + (360 - im.width) // 2, 25 + (360 - im.height) // 2), im)
    draw.text((x, 410), path.name, fill=(225, 225, 225))
    x += 400
preview_path = Path('/mnt/data/asset_d_no_white_borders_preview_dark.png')
preview.save(preview_path)

zip_path = Path('/mnt/data/asset_d_no_white_borders_pngs.zip')
with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zf:
    for path in outputs:
        zf.write(path, arcname=path.name)
    zf.write(Path('/mnt/data/remove_white_borders_helper.py'), arcname='remove_white_borders_helper.py')

print('Created:')
for path in outputs:
    print(path)
print(preview_path)
print(zip_path)

"""Generate packaging/flux.ico from the product mark shaped like frontend/public/favicon.svg."""
from pathlib import Path

from PIL import Image, ImageDraw

SCALED = 800  # oversample, then let the ICO writer scale down each listed size
img = Image.new('RGBA', (SCALED, SCALED), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle([0, 0, SCALED, SCALED], radius=11 / 40 * SCALED, fill=(23, 23, 23, 255))
bolt = [(22, 7), (11, 22), (19, 22), (17, 33), (30, 16), (21, 16)]
draw.polygon([(SCALED * x / 40, SCALED * y / 40) for x, y in bolt], fill=(250, 250, 250, 255))
target = Path(__file__).resolve().parent / 'flux.ico'
img.save(target, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print('wrote', target)

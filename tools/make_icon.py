"""Generate a deterministic, original network icon; no external artwork needed."""
from pathlib import Path
from PIL import Image, ImageDraw

folder = Path(__file__).resolve().parents[1] / "story_atlas" / "resources"
folder.mkdir(parents=True, exist_ok=True)
image = Image.new("RGBA", (256, 256), "#111827")
draw = ImageDraw.Draw(image)
nodes = ((55, 78), (193, 65), (129, 195))
draw.line([nodes[0], nodes[1], nodes[2], nodes[0]], fill="#9fb5c8", width=10)
for x, y in nodes:
    draw.ellipse((x-25, y-25, x+25, y+25), fill="#28c5ab", outline="#e5f4f2", width=5)
image.save(folder / "story-atlas.ico", sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
image.save(folder / "story-atlas.png")

"""Reproduce the reviewed UI subset: python tools/build_ui_assets.py SOURCE_ROOT.

Only the selected product artwork is copied; the full packs are never bundled.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from PIL import Image, ImageDraw

ICON_PACK = 'HAS IconPack (v.1.2)'
BUILDING_PACK = 'HAS Buildings Pack 1.01'
DESCRIPTIONS = {
    'book': ['Red book with a gold star', 'Orange book with gold bands', 'Dark red book with gold ornament', 'Blue book with silver diamond', 'Violet book with silver sun', 'Red book with gold pillars'],
    'artifact': ['Silver crossed ornamental talisman', 'Red and violet patterned talisman', 'Blue gem on an orange pendant', 'Green clustered gem'],
    'key': ['Bronze key', 'Red key', 'Blue key'],
    'ring': ['Gold band', 'Silver band', 'Broad pale gold band'],
    'shield': ['Layered gold shield with red rim', 'Narrow violet shield', 'Blue and silver pointed shield'],
    'cape': ['Gold-edged dark cape', 'Red cape with pale clasp'],
}


def selection():
    entries = []
    for group, numbers in [('Book', range(1, 7)), ('Artifact', range(1, 5)), ('Key', range(1, 4)), ('Ring', range(1, 4)), ('Shield', range(1, 4)), ('Cape', range(1, 3))]:
        category = f'Miscellaneous/{group}' if group in ('Book', 'Artifact', 'Key') else group
        for number in numbers:
            key = f'motif.{group.lower()}{number}'
            variant = group + ('Origin' if group in ('Book', 'Key') else 'Original')
            source = f'IconPack 1.0/AllItems/{category}/{variant}/{variant} {number}.png'
            entries.append((key, ICON_PACK, source, DESCRIPTIONS[group.lower()][number - 1]))
    for name in ('Library', 'ArcaneLibrary', 'Fort', 'Fountain', 'Gazebo', 'RallyFlag', 'LearningStone', 'Armorsmith', 'BeastmasterHut'):
        entries.append((f'building.{name.lower()}', BUILDING_PACK, f'HAS Buildings Pack/AttributeModifier/{name}.png', name))
    return entries


def build(source, output, sheet=None):
    output.mkdir(parents=True, exist_ok=True)
    (output / 'licenses').mkdir(exist_ok=True)
    manifest = {'version': 1, 'author': 'Aleksandr Makarov', 'assets': {}, 'aliases': {
        'section.identity': 'motif.book1', 'section.story': 'motif.book2',
        'section.goals': 'motif.key1', 'section.abilities': 'motif.artifact1',
        'section.inventory': 'motif.shield1', 'section.notes': 'motif.book3',
        'section.chapter': 'motif.book4', 'section.event': 'motif.book5',
        'welcome': 'building.library', 'empty.story': 'building.gazebo'}}
    for pack, license_name in ((ICON_PACK, 'has-icons.txt'), (BUILDING_PACK, 'has-buildings.txt')):
        shutil.copyfile(source / pack / 'license.txt', output / 'licenses' / license_name)
    for key, pack, relative, description in selection():
        original = source / pack / relative
        folder = 'illustrations' if key.startswith('building.') else 'icons'
        destination = f'{folder}/{key.split(".")[1]}.png'
        (output / folder).mkdir(exist_ok=True)
        shutil.copyfile(original, output / destination)
        with Image.open(original) as image:
            dimensions = list(image.size)
        manifest['assets'][key] = dict(path=destination, source_pack=pack, source_path=relative,
            source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(), crop=None,
            native_size=dimensions, variants=['native'], roles=['decoration'], description=description,
            author='Aleksandr Makarov', license='licenses/' + ('has-icons.txt' if pack == ICON_PACK else 'has-buildings.txt'),
            distribution_review='Selected artwork incorporated into Story Atlas; do not redistribute as an asset pack.',
            fallback=None, themes=['dark', 'light'], states=['normal'])
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    if sheet:
        canvas = Image.new('RGB', (800, 120 * ((len(manifest['assets']) + 4) // 5)), '#192333')
        draw = ImageDraw.Draw(canvas)
        for index, (key, item) in enumerate(manifest['assets'].items()):
            with Image.open(output / item['path']) as image:
                image = image.convert('RGBA')
                image.thumbnail((80, 80), Image.Resampling.NEAREST)
                if max(image.size) <= 32:
                    image = image.resize((image.width * 2, image.height * 2), Image.Resampling.NEAREST)
                x, y = (index % 5) * 160, (index // 5) * 120
                canvas.paste(image, (x + 40, y + 5), image)
                draw.text((x + 4, y + 90), key, fill='white')
        canvas.save(sheet)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'story_atlas/resources/ui')
    parser.add_argument('--contact-sheet', type=Path)
    args = parser.parse_args()
    build(args.source, args.output, args.contact_sheet)

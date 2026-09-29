"""Product artwork contracts: provenance, safe fallback, Tk ownership and drafts."""
import hashlib
import json
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from types import SimpleNamespace
from story_atlas.paths import resource
from story_atlas.settings import Settings
from story_atlas.ui_assets import UIAssetCache, cache_for, decorate, refresh_illustrations
from story_atlas.version import source_fingerprint


class AssetCatalogTests(unittest.TestCase):
    def test_bundled_catalog_bytes_and_licenses(self):
        folder = resource('ui')
        manifest = json.loads((folder / 'manifest.json').read_text())
        self.assertEqual(len(manifest['assets']), 30)
        for entry in manifest['assets'].values():
            path = folder / entry['path']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry['source_sha256'])
            self.assertTrue((folder / entry['license']).is_file())
        self.assertTrue(set(manifest['aliases'].values()) <= set(manifest['assets']))

    def test_preference_validation_and_fingerprint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = Settings(root / 'settings.json')
            settings.save(illustrations='Minimal')
            self.assertEqual(Settings(settings.path).values['illustrations'], 'Minimal')
            settings.save(illustrations='wrong')
            self.assertEqual(Settings(settings.path).values['illustrations'], 'Illustrated')
            (root / 'main.py').write_text('')
            assets = root / 'story_atlas/resources/ui'
            assets.mkdir(parents=True)
            (assets / 'manifest.json').write_text('{}')
            before = source_fingerprint(root)
            (assets / 'manifest.json').write_text('{"version": 1}')
            self.assertNotEqual(before, source_fingerprint(root))


class AssetTkTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def test_lru_retains_displayed_image_and_root_isolation(self):
        cache = cache_for(self.root)
        cache.capacity = 1
        label = decorate(ttk.Label(self.root, text='Story'), 'section.story')
        photo = label.atlas_art_image
        self.assertIsNotNone(photo)
        cache.get('section.goals')
        self.assertEqual(len(cache.images), 1)
        self.assertIn(str(photo), self.root.tk.call('image', 'names'))
        other = tk.Tk()
        try:
            other.withdraw()
            self.assertIsNot(cache_for(other), cache)
            self.assertIsNot(cache_for(other).get('section.story'), photo)
        finally:
            other.destroy()

    def test_missing_corrupt_manifest_and_escape_fall_back(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for content in ('broken', '[]', '{"assets": []}', '{"assets":{"escape":{"path":"../outside.png"},"broken":{"path":"bad.png"}}}'):
                (folder / 'manifest.json').write_text(content)
                (folder / 'bad.png').write_bytes(b'broken image')
                cache = UIAssetCache(self.root, folder)
                for key in ('missing', 'escape', 'broken'):
                    self.assertIsNone(cache.get(key))

    def test_minimal_refresh_preserves_entry_and_imported_image(self):
        self.root.settings = SimpleNamespace(values={'illustrations': 'Illustrated'})
        label = decorate(ttk.Label(self.root, text='Story'), 'section.story')
        entry = ttk.Entry(self.root)
        entry.insert(0, 'Uncommitted text')
        portrait = tk.PhotoImage(master=self.root, width=2, height=2)
        portrait_label = ttk.Label(self.root, image=portrait)
        self.root.settings.values['illustrations'] = 'Minimal'
        refresh_illustrations(self.root)
        self.assertIsNone(label.atlas_art_image)
        self.assertEqual(entry.get(), 'Uncommitted text')
        self.assertEqual(str(portrait_label.cget('image')[0]), str(portrait))
        self.root.settings.values['illustrations'] = 'Illustrated'
        refresh_illustrations(self.root)
        self.assertIsNotNone(label.atlas_art_image)

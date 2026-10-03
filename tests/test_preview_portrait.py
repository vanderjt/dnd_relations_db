import base64
from pathlib import Path
import tempfile
import unittest
import uuid
from story_atlas.preview_store import PreviewStore, Conflict


class PortraitTests(unittest.TestCase):
    def test_portable_portrait_replace_remove_and_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'story.atlas-preview'
            s = PreviewStore.create(path, 'Portrait test')
            def write(command, payload, revision=None):
                return s.write(command, payload, s.revision() if revision is None else revision, uuid.uuid4().hex)
            ident = write('create_character', {'name':'Ada','event_id':1})['data']['character_id']
            # Real JPEG produced by the same image format used by the frontend.
            from PIL import Image
            import io
            buffer = io.BytesIO()
            Image.new('RGB',(8,12),'red').save(buffer,format='JPEG')
            image = 'data:image/jpeg;base64,' + base64.b64encode(buffer.getvalue()).decode()
            old_revision = s.revision()
            write('save_portrait', {'character_id':ident,'image':image})
            self.assertEqual(s.workspace()['characters'][0]['portrait'], image)
            with self.assertRaises(Conflict):
                write('save_portrait', {'character_id':ident,'image':''}, old_revision)
            for invalid in ['data:image/svg+xml;base64,AAAA', 'data:image/jpeg;base64,broken', 'x'*2800001]:
                with self.assertRaises(ValueError):
                    write('save_portrait', {'character_id':ident,'image':invalid})
            backup = Path(folder)/'copy.atlas-preview'
            s.backup(backup)
            s.close()
            s = PreviewStore(backup)
            self.assertEqual(s.workspace()['characters'][0]['portrait'], image)
            write('save_portrait', {'character_id':ident,'image':''})
            self.assertEqual(s.workspace()['characters'][0]['portrait'], '')
            s.close()

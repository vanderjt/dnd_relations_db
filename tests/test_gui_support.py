"""Supporting-screen reachability and preference/data isolation contracts."""
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from story_atlas.app import StoryAtlas
from story_atlas.settings import Settings
from story_atlas.onboarding import Welcome
from story_atlas.story_setup import StorySetup
from story_atlas.appearance import AppearanceDialog
from story_atlas.recovery import RecoveryDialog
from story_atlas.guidance import show_artwork_credits
from story_atlas.illustrated_widgets import IdentityHeader
from tools.check_ui_contrast import audit


class SupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.app = StoryAtlas(self.folder / 'story.db', settings_path=self.folder / 'settings.json')
        self.errors = []
        self.app.report_callback_exception = lambda *args: self.errors.append(args)

    def tearDown(self):
        try:
            self.app.database.close()
        finally:
            self.app.destroy()
            self.temp.cleanup()
        self.assertEqual(self.errors, [])

    def assert_reachable(self, widget, window):
        self.app.update()
        self.assertTrue(widget.winfo_viewable())
        x, y = widget.winfo_rootx()-window.winfo_rootx(), widget.winfo_rooty()-window.winfo_rooty()
        self.assertGreaterEqual(x,0)
        self.assertGreaterEqual(y,0)
        self.assertLessEqual(x+widget.winfo_width(),window.winfo_width()+2)
        self.assertLessEqual(y+widget.winfo_height(),window.winfo_height()+2)
        self.assertIs(widget.winfo_containing(widget.winfo_rootx()+widget.winfo_width()//2,
                                            widget.winfo_rooty()+widget.winfo_height()//2),widget)

    def test_setup_expanded_minimum_has_reachable_commit_and_cancel(self):
        self.app.set_appearance('dark',16)
        setup = StorySetup(self.app,self.folder / 'stories',lambda _:None)
        setup.geometry('360x280')
        setup.fields[0].set('A very long title for a new story')
        setup.customize_button.invoke()
        self.assert_reachable(setup.create_button,setup)
        self.assert_reachable(setup.cancel_button,setup)
        self.assertEqual(setup.fields[1].get(),'Chapter 1')
        self.assertGreater(setup.scroller.content.winfo_height(),setup.scroller.canvas.winfo_height())
        setup.destroy()

    def test_appearance_apply_preserves_draft_portrait_and_persists(self):
        self.app.characters.fields['name'].set('Uncommitted name')
        path=self.folder/'portrait.png'
        Image.new('RGB',(24,24),'teal').save(path)
        ref=self.app.database.assets.import_image(path)
        identity=IdentityHeader(self.app)
        photo=identity.show_portrait(self.app.database.assets,ref)
        dialog=AppearanceDialog(self.app)
        dialog.geometry('360x280')
        dialog.theme.set('light'); dialog.size.set('16'); dialog.illustrations.set('Minimal')
        dialog.apply_button.invoke()
        self.assert_reachable(dialog.apply_button,dialog)
        self.assertEqual(self.app.characters.fields['name'].get(),'Uncommitted name')
        self.assertEqual(self.app.database.characters(),[])
        self.assertIs(identity.photo,photo)
        self.assertEqual(Settings(self.app.settings.path).values['illustrations'],'Minimal')
        dialog.destroy(); identity.destroy()

    def test_credits_full_licenses_are_selectable_and_read_only(self):
        self.app.set_appearance('light',16)
        dialog=show_artwork_credits(self.app)
        dialog.geometry('360x280')
        self.app.update()
        content=dialog.credits_text.get('1.0','end')
        self.assertIn('Aleksandr Makarov',content)
        self.assertIn('has-icons.txt',content)
        self.assertIn('has-buildings.txt',content)
        self.assertIn('may not host',content)
        self.assertEqual(dialog.credits_text.cget('state'),'disabled')
        dialog.credits_text.insert('1.0','MUTATION')
        self.assertEqual(dialog.credits_text.get('1.0','end'),content)
        dialog.credits_text.tag_add('sel','1.0','1.8')
        self.assertTrue(dialog.credits_text.tag_ranges('sel'))
        dialog.destroy()

    def test_recovery_selection_and_minimum_action_reachability(self):
        self.app.set_appearance('dark',16)
        ident=self.app.database.save_character({'name':'Recoverable'})
        self.app.database.trash.delete_character(ident)
        self.app.database.drafts.save(None,{'name':'Uncommitted'})
        dialog=RecoveryDialog(self.app)
        dialog.geometry('650x440')
        self.assertIn('disabled',dialog.recover_button.state())
        for tab,tree,button in [('Trash',dialog.trash,dialog.restore_trash_button),
                                ('Drafts',dialog.drafts,dialog.recover_button),
                                ('Backups & import',dialog.backups,dialog.restore_backup_button)]:
            dialog.tabs.select(dialog.pages[tab])
            if tree.get_children():
                tree.selection_set(tree.get_children()[0]); dialog.update_actions()
                self.assertNotIn('disabled',button.state())
            self.assert_reachable(button,dialog)
            self.assertGreater(tree.winfo_height(),35)
        dialog.tabs.select(dialog.pages['Trash'])
        dialog.restore_trash_button.invoke()
        self.assertEqual(self.app.database.characters()[0]['name'],'Recoverable')
        self.assertEqual(len(self.app.database.drafts.list()),1)
        dialog.destroy()


class WelcomeAndContrastTests(unittest.TestCase):
    def test_empty_graph_guidance_fits_compact_canvas_at_largest_text(self):
        import networkx as nx
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from story_atlas.graph_render import GraphRenderer
        figure=Figure(figsize=(3,1.8),dpi=100)
        canvas=FigureCanvasAgg(figure)
        renderer=GraphRenderer(figure)
        renderer.draw(nx.MultiDiGraph(),{},set(),text_size=16)
        canvas.draw()
        text=renderer.axes.texts[0]
        self.assertIn('focus and filters',text.get_text())
        bounds=text.get_window_extent(canvas.get_renderer())
        viewport=renderer.axes.bbox
        self.assertGreaterEqual(bounds.x0,viewport.x0)
        self.assertLessEqual(bounds.x1,viewport.x1)
        self.assertGreaterEqual(bounds.y0,viewport.y0)
        self.assertLessEqual(bounds.y1,viewport.y1)

    def test_welcome_primary_actions_at_minimum(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            settings=Settings(root/'settings.json'); settings.save(text_size=16)
            app=Welcome(root,settings)
            try:
                app.geometry('500x350'); app.update()
                for button in (app.start_button,app.open_button):
                    self.assertTrue(button.winfo_viewable())
                    self.assertLessEqual(button.winfo_y()+button.winfo_height(),button.master.winfo_height()+2)
                self.assertEqual(app.start_button.cget('style'),'Primary.TButton')
                self.assertEqual(app.open_button.cget('style'),'Secondary.TButton')
            finally:
                app.destroy()

    def test_palette_enabled_state_contrast_targets(self):
        failures=[row for row in audit() if not row['passed']]
        self.assertEqual(failures,[])

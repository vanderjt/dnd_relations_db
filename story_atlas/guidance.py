"""Short contextual tips and a reusable help window; dismissal is a preference."""
import tkinter as tk
from tkinter import ttk, messagebox
from .widgets import wrapping_label, ActionBar
from .scroll_frame import ScrollFrame
from .theme import style_tree
from .version import about_text

TIPS = {
    "saving": ("Saving", "Only a name is required. Save changes commits edits; a recovery draft is not a committed save. Ctrl+S saves the selected profile."),
    "relationships": ("Relationship direction", "Directional means Source → Target; an inverse label describes the same link. Mutual is one shared connection. Successful additions clear the form and keep it open."),
    "graph": ("Graph navigation", "Click to inspect; drag a character to move and pin it. Zoom/Pan toggle navigation modes; Fit reveals the view. Previous/Next changes time without moving the layout. Filters offers Highlight event changes and Changes only (including endings); Clear filters keeps time and focus. Visual categories are explicit presentation choices, saved with a named view. Dense labels appear near selection; the inspector lists every connection."),
    "recovery": ("Recovery", "Recovery opens backups, imports, drafts, and Trash. Restore opens a new database. Backups include portraits and history; keep a copy on another drive for disk failure."),
    "events": ("Chapters and story changes", "Browse chapters on the left and their events in the middle. The right pane shows the selected event's description, a list of every character marked active in the event, collapsible current goals for those characters, and relationship changes grouped by character. Characters appear in the active list even without a relationship change. The outline includes empty chapters and Unassigned. More actions edits or reorders chapters, with a chronology preview before a chapter move. Double-click an event or press Enter to change its chapter or position. Start relationship keeps the selected event visible and suggests its participants; Use this event deliberately dates the new connection. Record change saves a dated state for an existing relationship. Reordering chapters or events recalculates relationship history. New event saves reveal the destination chapter. Search participants and use Tab/Space to check them; filtering preserves selections. Current goals preview beside the chooser. Record story change and Correct entry have edit/review steps within one dialog. Expand details hides navigation until Show chapters and events. Edit current goals opens the current profile; Back returns here. Event → Graph → Profile → Back → Back restores context. Current means after the last event; profile fields and goals are never historically versioned."),
}

# Keep inline guidance short at large text sizes; F1 contains the full explanation.
SHORT_TIPS = {
    "saving": "Name is enough to start. Ctrl+S saves; drafts are recovery copies. F1 for help.",
    "relationships": "Directional: Source → Target. Mutual: shared connection. F1 for help.",
    "graph": "Click to inspect; drag to pin. Fit shows the network. F1 for help.",
    "recovery": "Recovery: backups, drafts, imports and Trash. F1 for help.",
    "events": "Choose a chapter and event; the overview is on the right. F1 for help.",
}


class GuidanceBar(ttk.Frame):
    def __init__(self, parent, topic="saving"):
        super().__init__(parent)
        self.app = parent.winfo_toplevel()
        self.topic = topic
        self.label = wrapping_label(self, style="Muted.TLabel")
        self.dismiss_button = ttk.Button(self, text="Dismiss tip", command=self.dismiss)
        self.show(topic)

    def show(self, topic):
        self.topic = topic
        self.label.pack_forget()
        self.dismiss_button.pack_forget()
        if topic in self.app.settings.values["dismissed_guidance"]:
            self.configure(height=1)
            return
        self.dismiss_button.pack(side="right", padx=8)
        self.label.configure(text=SHORT_TIPS[topic])
        self.label.pack(fill="x", expand=True, padx=16)

    def dismiss(self):
        dismissed = list(dict.fromkeys([*self.app.settings.values["dismissed_guidance"], self.topic]))
        try:
            self.app.settings.save(dismissed_guidance=dismissed)
        except OSError as error:
            messagebox.showerror("Cannot save preference", str(error), parent=self)
            return
        self.show(self.topic)


def show_help(app):
    dialog = tk.Toplevel(app)
    dialog.title("Story Atlas help")
    dialog.geometry("650x560")
    dialog.transient(app)
    body = ScrollFrame(dialog)
    body.pack(fill="both", expand=True, padx=16, pady=12)
    simple_help = ("Simple mode", "Start with a story title; Create story chooses an unused filename in your Stories folder. Change location and Customize opening are optional. New character emphasizes Name and Character type; optional sections retain hidden input. Suggestions never populate fields automatically. Tags are additive. Click a saved node to read its summary; Edit character opens the full profile. Connect… makes it Source; click nodes to toggle targets, or use keyboard selectors. Make source changes the ordered source; Exit selection keeps the form. Relationship presets stay editable. Review lists every pair, inverse label, notes and effective event before an atomic save. Success clears every field and selection and focuses Source; Use graph selection and Use selected event are explicit reuse actions. Next event navigates or suggests a new scene in the current chapter. Introduction timing has a Change action; chronology safeguards remain. Character type combines the former classification, narrative-role and template selectors. Choose Player, Merchant, Allied NPC, Neutral NPC or Enemy NPC. Add writing prompts for this type is optional and fills only empty prose. Old labels are mapped to these five options and their original values archived for recovery. New graph workspaces default to Circle (round). View → Legend · dots & links explains all five dot colors and the Support, Conflict, Personal and Other link colors. Dot entries filter the graph. Link categories are presentation choices saved with a view. Story offers Greyhaven and the modern prometheus examples; More → Saved graph views opens their guided scenes. New nodes use unoccupied spaces; their saved positions stay fixed. Planned cast is dashed with a text label. Simple character, event and relationship drafts recover through Settings → Recovery without committing; missing references need explicit resolution. Save / Discard / Stay protects unfinished tasks. More → Undo recent character creation is available only before later committed actions; Trash can restore it. Drag background to pan, wheel to zoom, drag nodes to pin. Shift-click builds ordered selection. Change at this event records development; Correct entry targets the exact effective state, including endings. Ctrl+Z undoes and Ctrl+Y redoes typing in a field, or saved story changes in the workspace. Finish unsaved forms first. Story also has Undo saved change and Redo saved change. History starts fresh when opening a story. Both modes share the same story services.")
    for title, text in (simple_help, *TIPS.values()):
        ttk.Label(body.content, text=title, style="Heading.TLabel").pack(anchor="w", pady=(12, 4))
        wrapping_label(body.content, text=text).pack(fill="x")
    wrapping_label(body.content, text=f"Active story: {app.database.path}\nPreferences: {app.settings.path}").pack(fill="x", pady=14)
    bar = ActionBar(dialog)
    bar.pack(fill="x", padx=16, pady=10)
    def restore():
        try:
            app.settings.save(dismissed_guidance=[])
            app.guidance.show(app.guidance.topic)
        except OSError as error:
            messagebox.showerror("Cannot save preference", str(error), parent=dialog)
    bar.add(ttk.Button(bar, text="Show contextual tips again", command=restore))
    bar.add(ttk.Button(bar, text="Close", command=dialog.destroy))
    dialog.bind("<Escape>", lambda _: dialog.destroy())
    style_tree(dialog)


def show_about(app):
    return messagebox.showinfo("About Story Atlas", about_text(app.database), parent=app)


def show_artwork_credits(app):
    from .ui_assets import artwork_credits
    from .paths import resource
    from .widgets import read_only_text_area, set_read_only_text
    dialog = tk.Toplevel(app)
    dialog.title('Artwork credits')
    dialog.geometry('660x480')
    dialog.minsize(360, 280)
    dialog.transient(app)
    bar = ttk.Frame(dialog, padding=12)
    bar.pack(side='bottom', fill='x')
    ttk.Button(bar, text='Close', command=dialog.destroy, style='Secondary.TButton').pack(side='right')
    body = ttk.Frame(dialog, padding=12)
    body.pack(fill='both', expand=True)
    ttk.Label(body, text='Artwork and licenses', style='Heading.TLabel').pack(anchor='w', pady=(0, 8))
    text = artwork_credits()
    for name in ('has-icons.txt', 'has-buildings.txt'):
        try:
            license_text = resource('ui/licenses/' + name).read_text(encoding='utf-8-sig')
        except OSError:
            license_text = 'License file unavailable. Restore the complete application package to view it.'
        text += '\n\n' + name + '\n' + license_text
    dialog.credits_text = read_only_text_area(body)
    dialog.credits_text.pack(fill='both', expand=True)
    set_read_only_text(dialog.credits_text, text)
    dialog.bind('<Escape>', lambda _: dialog.destroy())
    style_tree(dialog)
    return dialog

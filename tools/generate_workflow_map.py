"""Render the current workflow map while retaining the dated review baseline."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).resolve().parents[1] / 'docs' / 'reviews' / '2026-09-24'
OUT.mkdir(parents=True, exist_ok=True)
# Each box groups an interface stage, not a measured click count.
ROUTES = [
    ('Create a cast member', [
        ('Characters', 'nav'), ('+ New character', 'action'), ('Enter name\nand profile', 'edit'),
        ('Save character', 'save'), ('Saved overview', 'result')]),
    ('Give a character goals', [
        ('Characters\nSelect character', 'nav'), ('Overview\nEdit goals', 'action'),
        ('Write goals\nFree-form text', 'edit'), ('Save character', 'save'), ('Cast goals\nCommitted view', 'result')]),
    ('Plan a chapter + scene', [
        ('Chapter outline', 'nav'), ('New chapter\nTitle + summary', 'edit'),
        ('Save chapter\nVisible when empty', 'save'), ('New event', 'action'),
        ('Title, participants\nPosition in chapter', 'edit'), ('Save event', 'save')]),
    ('Change an existing bond', [
        ('Chapters & events\nSelect event', 'nav'), ('Change an existing\nrelationship', 'action'),
        ('Select relationship\nDescribe change', 'edit'), ('Set new state\nReview change', 'edit'),
        ('Review\nRecord change', 'save'), ('View graph\nat this event', 'result')]),
    ('Start a bond at an event', [
        ('Chapters & events\nSelect event', 'nav'), ('Start a new\nrelationship here', 'action'),
        ('Event context +\nparticipant hints', 'result'), ('Source, target, type\nMutual / Directional', 'edit'),
        ('Use this event\nExplicit choice', 'action'), ('Save relationship\nAll fields clear', 'save'),
        ('Inspect here\nor return to event', 'result')]),
    ('Reorder a chapter', [
        ('Chapter outline\nSelect chapter', 'nav'), ('More actions', 'action'),
        ('Move chapter\nearlier / later', 'action'), ('Preview old/new\nchronology', 'edit'),
        ('Events move together\nHistory recalculates', 'result')]),
    ('Find a story detail', [
        ('Search / Ctrl+K', 'nav'), ('Enter query', 'edit'), ('Select typed\nstory result', 'action'),
        ('Open selected', 'action'), ('Exact chapter / event\nor history state', 'result')]),
    ('Recover unsaved goals', [
        ('Maintenance', 'nav'), ('Recovery, Trash,\nand drafts...', 'action'), ('Drafts\nSelect draft', 'action'),
        ('Recover selected', 'action'), ('Review recovered\ncharacter profile', 'edit'), ('Save character\nCommit recovery', 'save')]),
    ('Share a historical graph', [
        ('Graph', 'nav'), ('Select event\nSet focus / filters', 'edit'), ('View & layout', 'action'),
        ('Export snapshot...', 'action'), ('Choose PNG filename', 'edit'), ('PNG + JSON\nExport logged', 'result')]),
]
COLORS = {'nav': '#254c72', 'action': '#35475b', 'edit': '#4b466d',
          'save': '#166553', 'result': '#244b46', 'friction': '#79532c'}
fig, ax = plt.subplots(figsize=(23, 16), facecolor='#101722')
ax.set_facecolor('#101722')
ax.set_xlim(0, 24)
ax.set_ylim(-.9, 14.2)
ax.axis('off')
ax.text(.15, 13.65, 'STORY ATLAS  /  UPDATED USER JOURNEYS', fontsize=24, weight='bold', color='#edf4fa')
ax.text(.15, 13.1, 'Read each row left to right. Boxes group menu/form stages, not individual clicks. Updated source · 24 September 2026',
        fontsize=12, color='#acbfd3')
for index, (goal, steps) in enumerate(ROUTES):
    y = 11.75 - index * 1.36
    ax.text(.15, y + .14, f'{index+1:02d}', color='#61d4bf', fontsize=12, weight='bold')
    import textwrap
    ax.text(.7, y + .14, textwrap.fill(goal, 23), color='#edf4fa', fontsize=12,
            va='center', weight='bold', linespacing=1.3)
    for j, (label, kind) in enumerate(steps):
        x = 4.05 + j * 2.82
        ax.add_patch(FancyBboxPatch((x, y-.35), 2.55, .96, boxstyle='round,pad=0.04,rounding_size=0.09',
                                   facecolor=COLORS[kind], edgecolor='#ffc876' if kind == 'friction' else '#718298', linewidth=1.2))
        ax.text(x + 1.275, y + .13, label, ha='center', va='center', color='white', fontsize=10.5, linespacing=1.35)
        if j:
            ax.add_patch(FancyArrowPatch((x-.24, y+.13), (x-.06, y+.13), arrowstyle='-|>',
                                        mutation_scale=12, linewidth=1.1, color='#b4c4d4'))
for i, (kind, label) in enumerate([('nav', 'Navigation'), ('edit', 'Form / choice'), ('save', 'Explicit save'), ('friction', 'Context or consequence to notice')]):
    x = .15 + i * 5.7
    ax.add_patch(FancyBboxPatch((x, -.33), .3, .24, boxstyle='round,pad=0.02', facecolor=COLORS[kind], edgecolor='#9dacbd'))
    ax.text(x+.46, -.21, label, color='#c5d1df', fontsize=11, va='center')
ax.text(.15, -.75, 'Search includes chapter/event text and relationship history. New-relationship saves clear every field and keep the dialog open.',
        fontsize=11, color='#acbfd3')
fig.subplots_adjust(left=.015, right=.995, top=.99, bottom=.03)
for extension in ('png', 'svg'):
    fig.savefig(OUT / f'user-workflow-map-current.{extension}', dpi=160, facecolor=fig.get_facecolor())
plt.close(fig)
print(OUT / 'user-workflow-map-current.png')

# Try the Story Atlas examples

**Current app:** open the `.atlas-preview` files in [saved-stories](saved-stories/README.md).
Frankenstein and Dracula are ready to open through the ordinary file picker.
The remainder of this guide describes the older Tkinter examples and `.db` format.

In Story Atlas 0.14.0 or later, choose **Story → Try the modern prometheus…** or
**Story → Try expanded Greyhaven sample…**. The welcome screen offers both too.
Each action creates a fresh, separate story, so experimentation never overwrites
your existing work. The `.db` files beside this guide are ready-made copies;
open one with **Story → Open**.

## the modern prometheus

This is a selected-scene model of Mary Shelley's **Frankenstein; or, The Modern
Prometheus**, using the [1831 text](https://www.gutenberg.org/files/42324/42324-h/42324-h.htm).
It contains **17 characters, 6 editorial chapters, 20 events, and 33 connections**.
It includes the ending. Scene summaries are original paraphrases with source
chapter references.

1. Open **Legend · dots & links**. Dots show current character types. Links use
   explicitly assigned Support, Conflict, Personal, or Other categories. These
   are presentation choices, not automatic judgments about a character's morality.
2. Open **More → Saved graph views…**, choose **01 · Creation and abandonment**,
   and click **Load**. Victor's Creator / Creation link records origin. A separate
   Abandonment link records his treatment of the creature.
3. Load **03 · The glacier bargain**. The same changing connection is now a mutual
   Conditional agreement, colored Support. The Creator connection still exists
   independently. A character dot can remain Enemy NPC while a particular link
   temporarily shows cooperation.
4. Load **04 · The promise breaks**. That agreement becomes a directional Broken
   promise, colored Conflict. Select the link and open **History** to compare its
   states. It later becomes mutual Pursuit, ending when Victor dies.
5. Load **05 · Marriage before the murder**. Move to the next event to see the
   active Spouse link end. Earlier relationship states remain in History.
6. Load **06 · The Arctic ending**. Read the creature's profile: his departure is
   witnessed, but his announced death is not. Walton's connection to Margaret is
   correspondence; she is not on the ship.
7. Return to **Example overview** to see the whole cast with link labels hidden
   for readability. Click a node or link to inspect its details. To experiment,
   select an event, add a new character, and connect it using **Add relationship**.
   Review the source, target, direction, and effective event before saving.

### Modeling choices

- Events follow an editorial chronological sequence rather than the novel's
  nested narration. The De Lacey/Safie history is identified as backstory revealed
  during the cottage sequence. These six chapters are not the book's chapter numbering.
- **Player** marks Victor and Walton as principal viewpoints in this adaptation.
  **Enemy NPC** marks the creature's opposition to Victor, not a claim that he is
  wholly evil. The profiles retain his learning, rejection, demands, violence,
  and remorse. Safie's father is the **Merchant** example.
- Introduction means entry into this selected-scene model, not birth. Before
  the creation scene, the creature is hidden unless **Show planned cast** is on.
- Types, status, and profile goals describe Current. Goals explicitly distinguish
  earlier and later motives in text; the app does not time-version profile fields.
  Use event summaries and relationship History for development over time.
- Parentage and recorded acts such as Killed remain historical facts after a
  death. An active fact-link does not imply that both people are alive. Interaction
  states such as friendship, marriage, and pursuit explicitly end in this model.
- Victor destroys the second being before animation. There is no invented living
  female creature, Igor, or film-specific episode. The final self-destruction is
  an intention, not a witnessed event.

## Updated Greyhaven

Greyhaven has **18 characters, 3 chapters, 10 events, and 50 recorded connections**.
All five character types are represented, every character has goals, and the
overview opens in a round layout with explicit link categories. Its saved views
show Mira's pact becoming hostility and Thorne/Sable's cooperation ending and
resuming. Newly added characters still find free space without shifting saved nodes.

## Files

The `.db` examples include the colored opening view and saved scenes. The JSON
exports contain portable story data; ordinary story export does not include saved
graph-view presentation presets. The PNGs are graph previews, not screenshots of
the complete application. Full-storage and real-Tk tests use disposable copies,
so these supplied examples do not contain test characters or test connections.

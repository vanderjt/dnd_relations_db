# Saved story examples

These are real, editable **Story Atlas Preview** files. No special example buttons
or per-story launchers are needed.

1. Launch the app using **Launch Story Atlas.cmd** at the repository root.
2. Choose **Open story…** on the welcome page. From an open story, first choose **Story file → New / open…**.
3. Browse to this folder and select a `.atlas-preview` story. The offline installer
   also adds these examples to `%LOCALAPPDATA%\StoryAtlasPreview\stories` without
   overwriting existing files.

Opening edits the selected file directly. To experiment while preserving these
examples, copy a file first or use **Restore backup as a copy…** to make a working
copy. The files can be copied to another computer alongside the installer.

| Story | Editorial chapters | Scenes | Cast entries |
| --- | ---: | ---: | ---: |
| Frankenstein | 6 | 20 | 17 |
| Dracula | 5 | 19 | 13 |
| Cyberpunk: Edgerunners Season 1 | 10 | 21 | 18 |

All include full spoilers, original scene summaries, purposes, location entries,
participant tags, character profiles and evolving relationships. The novels use
the Gothic theme; Edgerunners uses Cyberpunk. Unspecified ages remain blank; no
invented combat stats are supplied. “The three vampire women” is one explicitly grouped
cast entry in Dracula.

Frankenstein includes 16 coordinated, web-sourced AI portrait interpretations from
[Book2Life](https://book2.life/books/frankenstein); Safie’s father retains a placeholder.
Edgerunners includes all 18 cast portraits from the anime, sourced through NekoTeka,
Cyberpunk Wiki, and Anime.com/MyAnimeList. Images are embedded for offline use.
`portrait-sources.json` records each source and image hash; attribution also travels
inside the story. These references do not grant ownership or redistribution rights
to the original artwork. Dracula currently has no portraits.

## Reading the examples

Frankenstein follows [Mary Shelley's 1831 edition](https://www.gutenberg.org/files/42324/42324-h/42324-h.htm),
including Elizabeth's adoption. It adapts the repository's earlier legacy scene
outline into the current saved-story format with time-specific profiles. Events
follow story chronology, placing Walton's framing narrative near the end. The
creature's final death is not asserted: only his departure and stated intention
are witnessed.

Dracula follows [Bram Stoker's 1897 novel](https://www.gutenberg.org/cache/epub/45839/pg45839-images.html).
Its parallel documents are condensed into selected scenes with original chapter
references. Mina does not fully become a vampire. Jonathan and Quincey jointly
deliver the final attack; Quincey dies from his wound. Lucy's death, undeath and
release are separate timeline states.

Edgerunners models Season 1 of the [CD PROJEKT RED / TRIGGER anime](https://www.cyberpunk.net/en/edgerunners).
Its chapters follow the ten episodes, with selected scene subdivisions and a separate
Moon epilogue. Relationship categories are explicitly recorded for color coding.

The chapter groupings and relationship labels are editorial interpretations,
not the authors' original chapter divisions. Participation can include someone
discussed or addressed; notes identify important exceptions such as Margaret
Saville, who receives Walton's letters in England. All characters remain visible
in the cast because this preview does not hide them before their first scene.
Historical ties remain labeled after death instead of implying continued living
interaction. One connection per pair combines roles where necessary.

## Validation

Run `tools/verify_examples.py` with the current Python environment to check all
three stories for SQLite integrity, timeline facts, and matching snapshots after
closing and reopening. Portrait credits are recorded in `portrait-sources.json`
and inside the illustrated story files. All examples use the current
`.atlas-preview` format.

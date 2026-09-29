# GUI overhaul integration record

The implementation follows `ASSET_VISUAL_ROADMAP.md` on an integration branch named
`gui_overhaul`, created from local `main` at `7f84251`. Main is not the integration
target and remains unchanged. The pre-overhaul project archive is also retained.

## Workflow

Each feature branch starts from the latest reviewed integration commit. An
implementation agent changes the feature; another agent reviews it independently.
Findings are corrected and checked before merging. The primary agent coordinates
tests, pushes the feature branch, opens a pull request against `gui_overhaul`,
records review evidence, merges, and pulls the integrated result before starting
the next stage. GUI tests and screenshot capture run sequentially to avoid desktop
and focus interference. All test stories/settings are disposable.

## Stages

| Branch | Scope | State |
|---|---|---|
| `gui-overhaul/01-foundation` | Curated assets, provenance, image cache, shared components, character pilot, validation capture tool | Merged PR #1; 233 tests passed; pulled `aacf783` |
| `gui-overhaul/02-navigation` | Header, menus, Simple toolbar, Advanced navigation, help references | Merged PR #2; 237 tests passed; pulled `6ddb63c` |
| `gui-overhaul/03-workspaces` | Roster/search, relationship details, chronology, graph inspector | Merged PR #3; 248 tests passed; pulled `add06e8` |
| `gui-overhaul/04-support-release` | Welcome, setup, appearance/credits, support screens, release verification and packaging | Validated; awaiting reviewed PR integration |

The roadmap's later product opportunities (map editor, structured inventory,
user-authored covers, audio, retro theme) remain separate scope. Portrait graph
nodes are an optional later prototype, not required for this visual release.

## Evidence

Implementation and independent review reports belong in `docs/reviews/gui-overhaul`.
Generated test logs, screenshot matrices, and build output belong in the ignored
`build-verification` and `dist` directories. Reports distinguish source, packaged,
simulated scaling, and actual hardware checks; unperformed physical DPI/user
studies are not represented as passing.

The [0.19.0 release verification](reviews/gui-overhaul/04-release-verification.md)
records the independent test results, 116 final screenshots, Windows package
identity and measured startup/theme performance tradeoffs. The complete package
is available locally as `dist/StoryAtlas-Windows-x64.zip`.

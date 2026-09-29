# GUI overhaul baseline — 28 September 2026

Eight real Tk client-window screenshots were captured before foundation integration using `tools/capture_gui_overhaul.py`. Source version: **0.18.0**. Source fingerprint: `7e8edc59d41f3a9852a60d3a2a36d65011c6f480e9a599187d98c67f5308d96e`. The script creates disposable settings and a two-character fictional story under ignored `build-verification`; no actual user stories were opened.

Local evidence: `build-verification/gui-overhaul/baseline-20260928-203433/`. This contains eight PNGs, `report.json`, and `scale-benchmark.json`. Generated screenshots are local review artifacts, not committed assets. Each combination of Simple/Advanced and dark/light was captured at 1180×720/10pt and 760×480/16pt. No Tk callback errors occurred. Desktop capture required execution outside the sandbox after the initial screenshot attempt failed.

## Findings from screenshot inspection

- At 1180×720/10pt, the Simple graph and character summary remain legible. Navigation is visually busy and the summary lacks a portrait/identity treatment, matching the roadmap's proposed pilot.
- At 760×480/16pt, the **existing** Simple view has overlapping graph scope text and legend. Inspector actions occupy almost all available inspector height and the profile summary is effectively squeezed out. Timeline content reaches the bottom edge.
- At 760×480/16pt, the **existing** Advanced header's rightmost Back control is cut off. Header, guidance and two navigation levels consume much of the height; the selected profile and roster are pushed below the visible area. These are baseline issues, not overhaul regressions. The overhaul must improve them to meet its stated acceptance gate.
- The original report's raw geometry candidates include hidden notebook content and controls inside scrolling surfaces. They are not confirmed defects. The reusable tool was subsequently corrected to skip unviewable and scrolling controls explicitly and report their counts. Screenshot observations above are independent of those candidates.

## Baseline validation and timing

The coordinating agent reported the complete pre-change suite passing: **226 tests in 121.490s**, no skips shown. Its established 100-character/300-relationship graph measurements were initial 0.750s, note redraw 0.041s, direct scope 0.045s, Simple 0.503s.

The existing `tools/benchmark_story_scale.py` was also run against its disposable 100-character, 300-relationship, 30-chapter, 300-event, 1,200-history-state fixture. After one warm-up, five-run medians on this machine were:

| Operation | Median |
|---|---:|
| Initial chapter display | 4.784 ms |
| Chapter switch | 8.759 ms |
| Search | 14.024 ms |
| Exact history dialog | 16.227 ms |
| Chapter move preview | 6.411 ms |

These are one-session measurements, not responsiveness guarantees. The benchmark includes Tk idle layout for chapter/history operations and storage-only search/preview. It does not measure portrait graph nodes, first process paint, or memory use.

## Scope and remaining release evidence

Windows 11 build 26200, Python 3.13.9, desktop 3440×1440, Tk scaling about 1.33358. This records the actual current desktop; physical Windows 100/125/150/200% configurations and mixed-monitor movement were **not** tested. Optional `--tk-scaling` is only a simulation. No clean-machine package or representative-user evaluation was performed.

Baseline fixtures have missing portraits and overview/read states. The reusable capture tool's `--pilot` adds imported synthetic portrait overview/editor cases for independent review after integration. Release verification must additionally cover Minimal presentation, empty/error/historical/planned/filtered states, Welcome, shipped resource resolution and the final navigation commands. The synthetic portrait is a test drawing, not pack artwork or user content.

# Stage 04 — independent validation review

This reviewer independently checked the primary's benchmark and launcher changes, the palette audit and release/menu documentation. Foundation independently reviews supporting-screen production code in `04-independent-review.md`. This is agent review evidence, not a separate human approval.

## Benchmark and release tooling

The disposable benchmark measures 100 characters and 300 relationships, with separate cases containing zero or 100 managed portraits. It uses real mode switches, checks callback failures and closes database/Tk resources in nested cleanup. Repeated samples exclude fixture creation/imports and discard warm-up. First paint is explicitly same-process Tk display, not cold process startup.

Reviewed the Windows `PROCESS_MEMORY_COUNTERS_EX` layout and API signatures. Working-set and private-byte snapshots occur after warmed operations, with process ID and case order recorded. The report explicitly disclaims attribution to artwork and direct subtraction between portrait cases because allocator retention spans roots/cases. Cache assertions check observed occupancy against bounds; 100 portraits is not itself an eviction stress test. Baseline cache fields are null when those APIs do not exist. No benchmark timings or memory results are invented by this static review; actual runs belong in the release evidence.

The packaged launcher previously preferred a hard-coded 0.17.0 build over `dist/StoryAtlas`. Primary removed exactly that stale branch; independent review confirms sibling executable and current checkout package routes, argument forwarding and the missing-build message remain. README now correctly separates packaged and source launchers. Current sample, Appearance, Artwork credits and graph-filter menu documentation agrees with implemented routes. Historical package identities are marked historical and current staged review records are linked; final package verification remains separately required.

## Palette audit

Independently inspected actual enabled ttk/Tk text, selected, hover, pressed, border and focus pairings. The initial checker omitted Danger hover/selected and success text, although independent calculation showed they already passed. QA added those pairs. The final checker executes **66 pairs with zero failures**: minimum text contrast **4.752:1**, minimum audited border/focus contrast **3.062:1**. Disabled controls and decorative artwork are explicitly outside this numerical audit.

Primary button internal focus originally used the general focus color against the accent fill, with weak contrast. Primary/Accent styles now use `on_accent` for their internal focus cue, while retaining the external focus border against the surrounding surface. The same `on_accent`/normal/hover/pressed combinations are already covered by the stricter text threshold. Selected rows use regular text rather than muted text. This measures intended palette pairs; it is not a claim of platform accessibility conformance or physical per-monitor DPI verification.

## Full-suite gate

Final full discovery executed against source fingerprint `de31b721afa7a8eab99c4b8e14de113c8ea482af4a1a47bf81f92be744542d8f`, with exclusive GUI access. Command: `.build-env/Scripts/python.exe -m unittest discover -s tests -v`. Log: `build-verification/gui-stage4-full-tests.log`. **254 tests passed in 159.856 seconds**, no skips or failures, exit 0. The fingerprint was independently checked again after completion and remained identical. No fix iteration was needed for this Stage 04 full run.

The suite's single-run 100-node/300-edge timings were initial 0.757s, unrelated-note refresh 0.046s, direct focus 0.048s and Simple draw 0.292s. The repeated baseline/current benchmark remains separate evidence.

**Recommendation: the independently executed source-test and reviewed-tooling gates pass.** Final release approval additionally depends on foundation's production-code/supporting-screen visual review, the complete final capture evidence and primary's frozen package build/smoke verification. These are not inferred from the test result. Actual clean-machine execution and physical per-monitor DPI remain explicit verification limits.

## Final evidence follow-up

Following the full run, foundation independently reviewed the shortened two-line empty-graph instruction and its rendered-text boundary regression. The owner reports **seven supporting-screen tests passed in 2.427 seconds**. This remains separate from the preceding 254-test full run, rather than being reported as a 255-test full run.

Independently reviewed the corrected benchmark endpoint: initial window timing and its graph-node count are retained, while `first_content_paint` measures from the same start through `ensure_current()` and `update()`, asserting all 100 nodes and 300 edges. This makes the endpoint comparable when the baseline initially maps an empty graph but the current source already draws populated content. The correction changes benchmark methodology, not application source.

Independently read the final packaged smoke JSON: `ok=true`, `frozen=true`, version 0.19.0, schema 13, 37 recorded checks and source fingerprint `98bb3cce5bcbfee253c0ebcc7ea91b2a68e345a64057115cebdbb0376f138573`. Reviewed the strict bundled manifest/hash/license and Tk-image probes so runtime fallback cannot conceal omitted artwork. The Minimal-mode probe retains the imported portrait. Independently recomputed artifact hashes and confirmed both match the release report: EXE `D56DE77C06C6521165DA8D4B77FE3571A4C8A1BE78950DB54BA34BDF6721CCA7`; ZIP `F95A48978942264986A29E2DB04CFB1D81546D129DA56DA8DECC123D886EAB27`. This confirms local package evidence, not execution on a separate clean machine.

## Corrected performance and final recommendation

Independently read `performance-main.json`, `performance-overhaul.json` and `performance-comparison.json`: five retained samples per case, no callback errors, and the current fingerprint matches the package. Every baseline initial-window sample contains zero graph nodes; every current sample contains 100. The populated-content endpoint is therefore the appropriate startup comparison.

| Median operation | No portraits, baseline → current | 100 portraits, baseline → current |
|---|---|---|
| Populated first paint | 650 → 994 ms (+53%) | 658 → 1,072 ms (+63%) |
| Mode round trip | 1,646 → 1,578 ms (-4%) | 1,668 → 1,752 ms (+5%) |
| Theme round trip | 688 → 850 ms (+24%) | 709 → 820 ms (+16%) |
| Graph refresh | 335 → 316 ms (-6%) | 312 → 326 ms (+5%) |

Startup and theme costs are real measured regressions, not a claim of unchanged performance. The roadmap asks to investigate changes above 10%, rather than setting an unconditional 10% rejection ceiling. Primary investigated startup with profiling and found equal graph-build counts but increased rasterization while initial geometry settles. The resulting absolute populated-display time is approximately one second on this machine. No late application optimization is required for this integration recommendation; retain the documented costs and avoid claiming an established cause for every timing difference.

Observed artwork cache occupancy is 26/64 and 24/64; portrait-row occupancy is 100/128 in the portrait case. Whole-process working set is approximately 209 → 220 MB without portraits and 304 → 315 MB with portraits; private bytes approximately 584 → 594 MB and 680 → 691 MB. These are decimal MB, ordered-case snapshots, not isolated asset allocation.

Reviewed `scale-overhaul.json` and the original `baseline-20260928-203433/scale-benchmark.json`: matching seed, dataset, environment and five measured runs after warm-up. Their 30-chapter/300-event/100-character/300-relationship/1,200-history-state case reports chapter display 4.78 → 5.84 ms, chapter switch 8.76 → 9.97 ms and history opening 16.23 → 18.42 ms. Storage-only search is 14.02 → 13.73 ms and move preview 6.41 → 6.30 ms. The release report accurately qualifies the roughly 1.1/1.2/2.2 ms costs and slightly faster search/preview as local measurements, not representative-user results.

Reviewed the independent visual report covering 40 core images, 36 supporting-screen images and 40 font/Minimal spot checks at the final fingerprint. Together with independent production-code review, full-plus-focused test evidence and matching package smoke/hash evidence, **recommend approving Stage 04 integration and the locally verified package with the documented startup/theme costs and verification limits**. Clean-machine installation, physical mixed-monitor DPI and representative-user studies remain unperformed; this approval does not represent them as complete.

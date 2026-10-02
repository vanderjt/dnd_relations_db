# Web UI and Python desktop architecture decision

Decision date: October 1, 2026. Status: direction accepted; production implementation and distribution validation remain pending.

Story Atlas will pursue a React and TypeScript interface hosted in pywebview, with Python owning application logic and authoritative state and SQLite retaining local story data. The user accepted this direction after comparing Tauri, pywebview, NiceGUI, Electron, and a browser-based local application.

This record captures the discussion and its rationale. It does not claim that the existing Tkinter application has been migrated or that an offline web desktop build has been verified.

## User goals

- Use web-development tools to create an attractive interface for data entry and visualization.
- Keep all story rules, validation, and authoritative application state in Python.
- Give friends a simple executable to launch, without requiring a development environment.
- Run without an internet connection, with stories stored locally.

Windows is the initial distribution assumption. Supporting other operating systems was not decided.

## Selected architecture

The intended flow is React interface → pywebview JavaScript–Python bridge → Python application layer → SQLite.

React handles layout, forms, visual feedback, and graph rendering. Python handles character and relationship operations, chronology, validation, persistence, recovery, and authoritative application state. The frontend submits commands and displays results from Python rather than maintaining a second implementation of story rules.

Temporary presentation state can remain in JavaScript: hover effects, open menus, text being entered, and drag feedback. For example, the frontend can animate a node while dragging, then ask Python to accept and persist the final position. Durable drafts and saved data remain Python responsibilities. Any client-side validation is convenience feedback; Python must enforce the rules.

pywebview supports exposing Python methods through a JavaScript bridge and serving bundled static frontend assets with its internal HTTP server. A separate FastAPI or Flask application is therefore not required for this design. Local asset serving does not imply internet access. See the official [architecture guide](https://pywebview.flowrl.com/guide/architecture.html) and [bridge documentation](https://pywebview.flowrl.com/guide/interdomain.html).

The exact API contracts, state update mechanism, graph library, and handling of concurrent requests remain implementation decisions. Database access must respect Python thread ownership and transaction boundaries when bridge calls arrive.

## Alternatives considered

The assessments below reflect this project's priorities, not universal rankings of the frameworks.

| Option | Strength for Story Atlas | Tradeoff and decision |
| --- | --- | --- |
| React with pywebview | Direct use of web components and styling, with a Python desktop host and bridge. | Requires frontend tooling and a deliberate Python API. Selected for design freedom and fit with the existing Python code. |
| NiceGUI in native mode | Quickly builds forms, tables, and dashboards through Python controls and callbacks. | Customized graph interactions may require Vue or JavaScript component work. Strong alternative if writing the UI mostly in Python becomes the priority. |
| React with Tauri and a Python sidecar | Web desktop shell that supports bundling a separate Python executable. | Adds Rust tooling and sidecar process management. Viable, but those additional layers are not needed for the selected approach. |
| React with Electron and a Python process | Bundles a browser engine for a consistent rendering environment. | Larger distribution footprint and another runtime to maintain. A fallback if bundled browser consistency outweighs size. |
| Web UI with a local Python server in the default browser | Uses the friend's existing browser and avoids a desktop webview wrapper. | Browser-tab and backend lifecycles need coordination; less cohesive desktop experience. |

Tauri explicitly supports [external binaries including packaged Python applications](https://v2.tauri.app/develop/sidecar/). Electron documents its [desktop process model and web renderer](https://www.electronjs.org/docs/latest/tutorial/process-model).

## Why pywebview was chosen over NiceGUI

These options overlap: NiceGUI's native mode uses pywebview. The central choice is between a frontend we build directly with React and a UI driven through NiceGUI's Python framework. See [NiceGUI's native implementation](https://github.com/zauberzeug/nicegui/blob/main/nicegui/native/native.py).

NiceGUI is attractive for this application's routine data-entry screens. It provides Python-driven UI updates using Vue and Quasar, supports custom CSS, and allows custom Vue components. It can produce polished interfaces; appearance alone is not a reason to reject it. See its [foundations](https://nicegui.io/documentation/section_foundations), [styling support](https://nicegui.io/documentation/section_styling_appearance), and [custom component and packaging documentation](https://nicegui.io/documentation/section_configuration_deployment).

React with pywebview was preferred because the user specifically wants the flexibility of web-development tools. Story Atlas also needs coordinated graph selection, dragging, contextual tools, timeline navigation, and editing panels. Our assessment is that direct frontend development gives us more flexibility for these interactions, while an explicit Python boundary keeps domain rules reusable and testable.

The cost is maintaining two development environments and the interface between them. NiceGUI would reduce initial UI setup for standard forms, but specialized frontend components could bring web tooling back into that approach as well. No comparative performance or development-time benchmark was performed.

## Offline distribution requirements

Both approaches can be packaged for offline operation. All JavaScript, CSS, fonts, icons, images, and visualization dependencies must be included locally; production screens must not require CDNs, hosted APIs, or online asset downloads.

pywebview documents [PyInstaller packaging for built React assets](https://pywebview.flowrl.com/guide/freezing.html). Friends should not need Python, Node.js, or package managers installed. Node.js is a development/build dependency for the proposed frontend.

The final delivery format remains open:

- A portable executable is convenient to share. PyInstaller's one-file mode extracts bundled components at launch and may start more slowly.
- A setup executable can install application files and prerequisites, then provide a normal shortcut.

See [PyInstaller's packaging model](https://pyinstaller.org/en/stable/operating-mode.html). A single installer executable is not the same as a single portable application executable.

For the proposed Windows renderer, WebView2 availability must be handled explicitly. Offline operation on an already configured computer and offline installation on a clean computer are separate acceptance checks. NiceGUI's native mode does not remove this renderer dependency. See [pywebview's renderer requirements](https://pywebview.flowrl.com/guide/web_engine.html).

The initial pasted Tauri research was useful as an architectural starting point, but its small-download claims were not accepted as estimates for Story Atlas. Python, dependencies, assets, and any bundled renderer prerequisites all contribute to size. Its shell API/configuration example also needs updating for Tauri 2. Tauri's [Windows installer guide](https://v2.tauri.app/distribute/windows-installer/) explains the additional cost of offline WebView2 distribution. Actual size and startup time must be measured for our build.

## Relationship to the existing project

The current application uses Python, Tkinter, SQLite, NetworkX, and Matplotlib. Existing storage and domain logic are candidates for reuse, but their coupling to UI code must be assessed before migration estimates are made. SQLite story compatibility, backups, and recovery behavior should be preserved and verified during implementation.

The existing [Phase 2 prototype](../prototypes/phase2/README.md) is a separate browser design experiment using JavaScript modules and browser localStorage. Its visual and interaction ideas can inform the new frontend. Its browser-owned data model is not the accepted production state architecture; production operations must go through Python. This decision does not itself rewrite that prototype or change its documented scope.

## Proposed first implementation milestone

Build one end-to-end prototype before a broad migration:

1. Open a disposable copy of a story through Python.
2. Display an interactive relationship graph and a polished character-entry screen in pywebview.
3. Submit edits to Python, enforce existing rules, save through SQLite, and reload to verify persistence.
4. Package the application with all frontend assets and its required runtime components.
5. Test launch, editing, graph interaction, persistence, shutdown, and relaunch on Windows without Python or Node installed and with networking disabled.
6. Verify the selected prerequisite strategy on a machine without WebView2, and measure package size and startup time.

This milestone is a proposed validation plan, not completed work. Final packaging format, graph library, migration sequence, and estimates remain open until implementation evidence is available.

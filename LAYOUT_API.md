# `web/sg_dom_widgets.js` — the layout API

Nodes 2.0 only. Every control here is one `label | control` row in the node's **own** widget grid, so
a picker is indistinguishable from the native `task` combo beside it. Nothing draws on the classic
canvas; `requireVueNodes` says so on the node instead.

## How a row lands in the node's grid

The Vue node wraps each widget in `flex flex-col *:flex-1 col-span-2`, itself one item of the row's
`grid-cols-subgrid`. The stylesheet turns that wrapper into a subgrid and makes `.sg-dom`
`display: contents`, so our label and our control become items of the node's own label and control
tracks. That is why the columns line up — not because a width was guessed.

Consequences you have to respect:

- `.sg-dom` has **no box**. Never measure it; measure `.sg-ctl`, which is what `getMinHeight` does.
- The wrapper is `align-items: start`, so a control is content height and the slack pools at the
  bottom of the node.

## Exports

| export | what it does |
|---|---|
| `call(url, {body, signal})` | one route, decoded; every failure is a sentence |
| `cascade()` | one run of dependent reads at a time |
| `searchPicker(node, target, opts)` | trigger + popup, writes into the declared widget `target` |
| `chipSelect(node, target, opts)` | status chips in the control column |
| `hideWidget(widget)` | hide a declared widget (`hidden` **and** `options.hidden`) |
| `advancedWidget(widget)` | put a widget inside the editor's own "Show advanced inputs" fold |
| `dontSerialize(widget)` | keep an injected widget out of `widgets_values` |
| `restoreValue(widget, value)` | set a saved value **and** keep it selectable, so no red ring |
| `restoreDeclaredWidgets(nodeType, declared)` | chain an `onConfigure` that re-applies saved values by name |
| `domRow(node, name, {label, control, target})` | the raw row, for anything not a picker |
| `fitNode(node)` | set `node.size` from what the node actually renders |
| `iconHtml(icon, rgb)` | one status icon, three renderings (recipe 010) |
| `vueNodesEnabled()` / `requireVueNodes(node)` | Nodes 2.0 detection, and the notice when it is off |

### `call(url, {body, signal})`

Every round trip in `web/` goes through it, the Settings rows included, and it never throws. A
failure answers `{items: [], error}` — the shape a picker already reads — and the three failures are
told apart: a server that did not answer, a **404**, and a body that is not JSON. A 404 is a
ComfyUI that started before this version of the pack was installed, since the routes register when
ComfyUI imports it, so it is its own sentence: *The running ComfyUI predates this version of the
pack. Restart ComfyUI, then reload this page.* `body` makes it a POST. A request aborted by its
caller answers `{aborted: true}` and no sentence, because that caller is about to stop anyway.

### `cascade()`

The sequence guard. `begin()` aborts what the previous cascade still has in flight and answers a
token; the token's `live` is false from the moment a later `begin()` runs. Every step of
`loadProject` → `loadLinks` → `loadTasks` takes the token its entry point began with and checks
`live` after **every** await, before it writes anything — a widget's options, a picked id, the
panel. Picking Chariot and then Barbarian would otherwise leave Barbarian's links beside Chariot's
statuses, and a publish is filed against whatever the last answer wrote. A step that reads a
sentence instead of rows stops the cascade there: the saved values stay, and the sentence goes to
the panel.

### `searchPicker(node, target, opts)`

Options:

| option | meaning |
|---|---|
| `search(q, {live, signal})` | async, returns items (below). Multi-word goes to the server |
| `placeholder` | placeholder inside the popup's search box |
| `onPick(item)` | after `target.value` is written and the popup closed |
| `label` | the left column, lower case: it sits beside `task`, not above it |
| `empty` | the sentence shown when a search matches nothing |

A search has its own guard, the picker's rather than the node's: `signal` aborts the request a newer
keystroke supersedes, and anything the search itself records — the ids a picked label is turned back
into — goes behind `live()`.

An **item** is `{value, name, type, code, image}`; only `value` and `name` are required.
`code` is preferred over `type` on the right of a row. `image` draws a 22px thumbnail; the slot is
reserved on every row as soon as one row has a picture, so names stay aligned.

Returns `{refresh, relayout}`. `refresh(item?)` redraws the trigger; pass the current item to
put its thumbnail on the trigger too.

The popup is appended to `<body>` and positioned `fixed`, because a node lives inside a transformed,
clipping ancestor. It closes on outside click, wheel, resize and Escape; ↑/↓ move, Enter picks —
except while a keystroke's own answer is still coming, where Enter picks nothing, because the rows
on screen are the previous search's.

### `chipSelect(node, target, opts)`

Options: `load()`, `label` (left column) and `empty`. It reads nothing when it is built: the chips
are for one project, and which project that is arrives a round trip later, so the caller calls
`reload()` once it knows. Returns `{reload}`.

### `domRow(node, name, {label, control, target})`

- `label` — omit for a row that spans both columns (that is what the panel does).
- `target` — the declared widget this replaces; the row is spliced to sit where it sits.

Sets `serialize = false` on the widget it creates.

There is no `grow` any more. A row that pooled a taller node's surplus put an empty band under two
lines of text every time the content SHRANK — a node widened until the chips needed one row fewer, a
fold shut — and never served the case it was for, because dragging a node taller does not route
through `fitNode`. The node sizes to its content; surplus from a manual drag sits at the bottom, the
way it does on every other node.

### `restoreValue(widget, value)`

Sets the value, then appends it to `options.values` if the list does not already hold it. Use it
anywhere a saved graph's value lands on a combo — `restoreDeclaredWidgets` does.

Every combo here is seeded for the default project at load and repopulated per project one round
trip later, so a saved graph's `task` arrives before its list does. `WidgetSelectDefault.isInvalid`
is "there is a value and nothing in the list matches", and it draws `ring-1
ring-destructive-background` — a red ring that then stayed on for the rest of the session, because
the Vue component reads the options when it builds and a later `options.values = […]` never reached
it. Widening the list is what `VALIDATE_INPUTS` already does on the server.

### `advancedWidget(widget)`

Sets `advanced` **and** `options.advanced`, the pair `hideWidget` sets for `hidden`.
`isWidgetVisible` reads `options.advanced` exactly as it reads `options.hidden`, and the node's
footer button appears as soon as any widget carries it. This is how the readout's fine print folds:
one fold per node, the editor's own, rather than a `<details>` of ours beside it.

### Serialization — read this before adding any widget

`addDOMWidget(…, {serialize: false})` **does not work**: `LGraphNode.serialize` and `.configure`
both test `widget.serialize`, the property, never the option. An injected widget that serializes eats
a slot in a positional array and shifts every declared value after it.

Worse, the frontend's save and restore disagree even when the property is set: `serialize()` writes
`widgets_values[i]` at the index over *all* widgets (leaving a `null` hole where it skipped one),
while `configure()` reads with a counter that only advances on serialized widgets.

So: call `dontSerialize` on **every** widget you add (`addWidget("button", …)` included — litegraph
never sets the flag itself), and call `restoreDeclaredWidgets(nodeType, declared)` once per node
type, `declared` being the widget names in `INPUT_TYPES` order, derived from the definition the
server sent. It maps by name: `widgets_values_named`, which the editor always writes, or an array
exactly as long as `declared`. Any other shape is left to the frontend rather than guessed at.

### `fitNode(node)`

Replaces `node.setSize([w, node.computeSize()[1]])`. The Vue node is `min-h-(--node-height)`, so its
DOM height is the larger of `node.size` and its content and `computeSize()` can disagree with the
picture unnoticed. `fitNode` zeroes the variable for one reflow, asks the content what it wants, and
sets `node.size` to that.

### `requireVueNodes(node)`

`if (!requireVueNodes(this)) return;` at the top of `onNodeCreated`. When Nodes 2.0 is off it adds
two full-width buttons — the sentence naming the setting to turn on, and one line saying the lists
on the node do not update on the classic canvas — suffixes the node title once, and answers `false`.
Both buttons open Settings. It never flips the setting: that changes the operator's whole editor.

## `web/sg_panel.js`

`addPanel(node, title, onLayout)` adds **two** rows, and the second carries `advancedWidget`.

| where | what is in it |
|---|---|
| head, always | the Version's name, its status pill, the state pill |
| body, always | an error; `d.alert`; why nothing resolved and what IS there; `d.provenance`, `d.format`, `d.frames`, `d.facts`, `d.generated_from`; the last run's log |
| the fold | `d.link`, `d.task`, `d.echo`, `d.why`, `d.sources`, `d.fields` and `d.uploads` |

A field the site does not have is struck through in the fold, and nothing there says how to create
one: that is the site's own job, not a node's.

The line is what a widget already answers. `link`, `task` and everything in `d.echo` are the node's
own combos read back — three rows higher, in the operator's own words — so the readout repeating
them is noise where the name is supposed to be the signal. `d.facts` is what only the site knows
about this Version and stays in front of them.

`d.format` is one plain line under the image and video rows, from `/sg/resolve`: what the file the
Load node will read IS. Nothing is drawn when the answer carries none.

`d.alert` is the exception that never folds: one amber line saying the name above it is **not** the
name a Run would write. `/sg/preview_code` answers it — a template renders what it can and drops
the rest, so a collapsed `v004` and a finished `sbx_0020_depth_v008` look equally settled.

`show(d)` honours an explicit `d.state` of `"ok" | "warn" | "loading"`, which overrides the guess
made from `d.error` / `d.id`. It has to: `why` lives in the fold now, so a publish that cannot read
its provenance, or that would drop a value mapped to a field this site does not have, is only ever
said by the pill.

Both readout boxes are separate widgets and therefore separate grids: their label columns are
floored to the same 9ch so they roughly agree, but only one grid across both would line them up
exactly, and a DOM widget cannot span two rows of the node's own grid.

## `/sg/projects`

Items now carry `code` and `image` beside `label` and `id`. `image` is a presigned S3 URL, re-signed
on every read and good for about 900s (`field_types/image`); a thumbnail still transcoding is
returned as `""` rather than as a placeholder. `site.projects()` still answers `(name, id)` pairs;
`site.project_cards()` is the richer one.

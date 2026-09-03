# `web/fpt_dom_widgets.js` — the layout API

Nodes 2.0 only. Every control here is one `label | control` row in the node's **own** widget grid, so
a picker is indistinguishable from the native `task` combo beside it. Nothing draws on the classic
canvas; `requireVueNodes` says so on the node instead.

## How a row lands in the node's grid

The Vue node wraps each widget in `flex flex-col *:flex-1 col-span-2`, itself one item of the row's
`grid-cols-subgrid`. The stylesheet turns that wrapper into a subgrid and makes `.fpt-dom`
`display: contents`, so our label and our control become items of the node's own label and control
tracks. That is why the columns line up — not because a width was guessed.

Consequences you have to respect:

- `.fpt-dom` has **no box**. Never measure it; measure `.fpt-ctl`, which is what `getMinHeight` does.
- The wrapper is `align-items: start`, so a control is content height and the slack pools at the
  bottom of the node.

## Exports

| export | what it does |
|---|---|
| `searchPicker(node, target, opts)` | trigger + popup, writes into the declared widget `target` |
| `chipSelect(node, target, opts)` | status chips in the control column |
| `hideWidget(widget)` | hide a declared widget (`hidden` **and** `options.hidden`) |
| `advancedWidget(widget)` | put a widget inside the editor's own "Show advanced inputs" fold |
| `dontSerialize(widget)` | keep an injected widget out of `widgets_values` |
| `restoreDeclaredWidgets(nodeType)` | chain an `onConfigure` that re-applies saved values correctly |
| `domRow(node, name, {label, control, target})` | the raw row, for anything not a picker |
| `fitNode(node)` | set `node.size` from what the node actually renders |
| `iconHtml(icon, rgb)` | one status icon, three renderings (recipe 010) |
| `vueNodesEnabled()` / `requireVueNodes(node)` | Nodes 2.0 detection, and the notice when it is off |

### `searchPicker(node, target, opts)`

Signature unchanged. Options:

| option | since | meaning |
|---|---|---|
| `search(q)` | — | async, returns items (below). Multi-word goes to the server |
| `placeholder` | — | placeholder inside the popup's search box |
| `onPick(item)` | — | after `target.value` is written and the popup closed |
| `label` | — | the left column. **Lower case now** — it sits beside `task`, not above it |
| `empty` | new | the sentence shown when a search matches nothing |

An **item** is `{value, name, type, code, image}`; only `value` and `name` are required.
`code` is preferred over `type` on the right of a row. `image` draws a 22px thumbnail; the slot is
reserved on every row as soon as one row has a picture, so names stay aligned.

Returns `{refresh, relayout, close}`. `refresh(item?)` redraws the trigger; pass the current item to
put its thumbnail on the trigger too.

The popup is appended to `<body>` and positioned `fixed`, because a node lives inside a transformed,
clipping ancestor. It closes on outside click, wheel, resize and Escape; ↑/↓ move, Enter picks.

### `chipSelect(node, target, opts)`

Signature unchanged. Options: `load()` as before, plus `label` (new, left column) and `empty` (new).

### `domRow(node, name, {label, control, target})`

- `label` — omit for a row that spans both columns (that is what the panel does).
- `target` — the declared widget this replaces; the row is spliced to sit where it sits.

Sets `serialize = false` on the widget it creates.

There is no `grow` any more. A row that pooled a taller node's surplus put an empty band under two
lines of text every time the content SHRANK — a node widened until the chips needed one row fewer, a
fold shut — and never served the case it was for, because dragging a node taller does not route
through `fitNode`. The node sizes to its content; surplus from a manual drag sits at the bottom, the
way it does on every other node.

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
never sets the flag itself), and call `restoreDeclaredWidgets(nodeType)` once per node type. It
prefers `widgets_values_named`, which is always written, and falls back to the index the save used.

### `fitNode(node)`

Replaces `node.setSize([w, node.computeSize()[1]])`. The Vue node is `min-h-(--node-height)`, so its
DOM height is the larger of `node.size` and its content and `computeSize()` can disagree with the
picture unnoticed. `fitNode` zeroes the variable for one reflow, asks the content what it wants, and
sets `node.size` to that.

### `requireVueNodes(node)`

`if (!requireVueNodes(this)) return;` at the top of `onNodeCreated`. When Nodes 2.0 is off it adds a
full-width button that opens Settings, suffixes the node title, and answers `false`. It never flips
the setting: that changes the operator's whole editor.

## `web/fpt_panel.js`

`addPanel(node, title, onLayout)` adds **two** rows, and the second carries `advancedWidget`.

| where | what is in it |
|---|---|
| head, always | the Version's name, its status pill, the state pill |
| body, always | an error; why nothing resolved and what IS there; `d.provenance`, `d.facts`, `d.generated_from`; the last run's log |
| the fold | `d.link`, `d.task`, `d.echo`, `d.why`, `d.sources`, `d.fields` and `d.uploads` |

The line is what a widget already answers. `link`, `task` and everything in `d.echo` are the node's
own combos read back — three rows higher, in the operator's own words — so the readout repeating
them is noise where the name is supposed to be the signal. `d.facts` is what only the site knows
about this Version and stays in front of them.

`show(d)` honours an explicit `d.state` of `"ok" | "warn" | "loading"`, which overrides the guess
made from `d.error` / `d.id`. It has to: `why` lives in the fold now, so a publish that cannot read
its provenance, or that would drop a value mapped to a field this site does not have, is only ever
said by the pill.

## `/fpt/projects`

Items now carry `code` and `image` beside `label` and `id`. `image` is a presigned S3 URL, re-signed
on every read and good for about 900s (`field_types/image`); a thumbnail still transcoding is
returned as `""` rather than as a placeholder. `site.projects()` still answers `(name, id)` pairs;
`site.project_cards()` is the richer one.

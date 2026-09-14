# `web/sg_dom_widgets.js`, the layout API

Nodes 2.0 only. Each control here is one `label | control` row in the node's own widget grid, so a
picker matches the native `task` combo beside it. Nothing draws on the classic canvas, and
`requireVueNodes` writes the notice on the node instead.

## The row in the node's grid

- Nodes 2.0 wraps each widget in `flex flex-col *:flex-1 col-span-2`, one item of the row's
  `grid-cols-subgrid`.
- The stylesheet turns that wrapper into a subgrid and sets `.sg-dom` to `display: contents`, so the
  label and the control become items of the node's own label and control tracks.
- `.sg-dom` has no box. Measure `.sg-ctl`, which is what `getMinHeight` does.
- The wrapper is `align-items: start`, so a control is its content height and surplus height goes to
  the bottom of the node.

## Exports

| export | what it does |
|---|---|
| `call(url, {body, signal})` | one route, decoded, with a sentence on failure |
| `cascade()` | one run of dependent reads at a time |
| `searchPicker(node, target, opts)` | trigger and popup, writes into the declared widget `target` |
| `chipSelect(node, target, opts)` | status chips in the control column |
| `hideWidget(widget)` | hide a declared widget (`hidden` and `options.hidden`) |
| `advancedWidget(widget)` | put a widget inside the editor's own "Show advanced inputs" fold |
| `dontSerialize(widget)` | keep an injected widget out of `widgets_values` |
| `restoreValue(widget, value)` | set a saved value and keep it selectable |
| `restoreDeclaredWidgets(nodeType, declared)` | chain an `onConfigure` that re-applies saved values by name |
| `domRow(node, name, {label, control, target})` | the row, for anything that is not a picker |
| `fitNode(node)` | set `node.size` from the height the node renders |
| `iconHtml(icon, rgb)` | one status icon, in three renderings (recipe 010) |
| `vueNodesEnabled()` / `requireVueNodes(node)` | Nodes 2.0 detection, and the notice when it is off |

### `call(url, {body, signal})`

Each round trip in `web/` goes through it, the Settings rows included. It does not throw.

- A failure returns `{items: [], error}`, the shape a picker reads.
- Three failures are told apart: a server that did not answer, a 404, and a body that is not JSON.
- A 404 returns `The running ComfyUI predates this version of the pack. Restart ComfyUI, then
  reload this page.` The routes register when ComfyUI imports the pack, so a 404 means a server
  started before this version was installed.
- `body` makes the request a POST.
- A request aborted by its caller returns `{aborted: true}` and no sentence.

### `cascade()`

`begin()` aborts what the previous cascade has in flight and returns a token. The token's `live` is
false from the moment a later `begin()` runs.

- Each step of `loadProject`, `loadLinks`, `loadTasks` takes the token its entry point began with.
- A step checks `live` after each await, before it writes a widget's options, a picked id or the
  panel.
- A step that reads a sentence instead of rows stops the cascade there. The saved values stay, and
  the sentence goes to the panel.

### `searchPicker(node, target, opts)`

| option | meaning |
|---|---|
| `search(q, {live, signal})` | async, returns items. A multi-word query goes to the site |
| `placeholder` | placeholder inside the popup's search box |
| `onPick(item)` | runs after `target.value` is written and the popup is closed |
| `label` | the left column, lower case, to match the `task` combo beside it |
| `empty` | the sentence shown when a search matches nothing |

An item is `{value, name, type, code, image, icon, rgb}`. `value` and `name` are required.

- `code` is drawn on the right of a row in preference to `type`.
- `image` draws a 22px thumbnail. The slot is reserved on each row once one row has a picture, so
  the names align.
- `icon` and `rgb` draw a status the way SG draws it (recipe 010), on the row and on the trigger.

A search has its own guard, the picker's rather than the node's. `signal` aborts the request a newer
keystroke supersedes. `live()` is false for a superseded search, and what the search records, the
ids a picked label is turned back into, goes behind that check.

Returns `{refresh, relayout}`. `refresh(item?)` redraws the trigger. Pass the current item to put
its thumbnail on the trigger.

The popup:

- Is appended to `<body>` and positioned `fixed`, because a node is inside a transformed, clipping
  ancestor.
- Closes on outside click, wheel, resize and Escape.
- Moves the highlight on the up and down arrows, and picks on Enter.
- Picks nothing on Enter while a keystroke's own answer is still coming, because the rows on screen
  are the previous search's.

### `chipSelect(node, target, opts)`

Options: `load()`, `label` for the left column, and `empty`. Returns `{reload}`.

- It reads nothing when it is built. The chips are for one project, and which project that is
  arrives one round trip later.
- The caller calls `reload()` once it knows the project.

### `domRow(node, name, {label, control, target})`

- `label`: omit for a row that spans both columns, which is what the panel does.
- `target`: the declared widget this row replaces. `addDOMWidget` appends, so the row is spliced
  back to the index of its widget.
- Sets `serialize = false` on the widget it creates.
- Returns `{widget, root, ctl, relayout}`.

### `restoreValue(widget, value)`

Sets the value, then appends it to `options.values` when the list does not already have it. Use it
wherever a saved graph's value reaches a combo. `restoreDeclaredWidgets` uses it.

- A combo here is seeded for the default project and repopulated per project one round trip later,
  so a saved graph's `task` arrives before its list.
- `WidgetSelectDefault.isInvalid` is "there is a value and nothing in the list matches it", and it
  draws `ring-1 ring-destructive-background`.
- The Vue component reads the options when it builds, so a later `options.values = […]` does not
  reach it and the red ring stays for the session.
- `VALIDATE_INPUTS` widens the same list on the server.

### `advancedWidget(widget)`

Sets `advanced` and `options.advanced`, the pair `hideWidget` sets for `hidden`. `isWidgetVisible`
reads `options.advanced` as it reads `options.hidden`, and the node's footer button appears once a
widget sets it. The readout's fine print folds into that fold, the editor's own, rather than into a
`<details>` beside it.

### Serialization

Read this before adding a widget.

- `addDOMWidget(…, {serialize: false})` does not do this. `LGraphNode.serialize` and `.configure`
  both test `widget.serialize`, the property, and the option is not copied onto the widget.
- An injected widget that serializes takes a slot in a positional array and shifts each declared
  value after it.
- The frontend's save and its restore disagree even when the property is set. `serialize()` writes
  `widgets_values[i]` at the index over all widgets, leaving a `null` hole where it skipped one,
  while `configure()` reads with a counter that advances on serialized widgets alone.

The two rules:

- Call `dontSerialize` on each added widget, `addWidget("button", …)` included. Litegraph does not
  set the flag itself.
- Call `restoreDeclaredWidgets(nodeType, declared)` once per node type. `declared` is the widget
  names in `INPUT_TYPES` order, derived from the definition the server sent.

`restoreDeclaredWidgets` maps by name. It reads `widgets_values_named`, which the editor writes, or
an array the same length as `declared`. A third shape is left to the frontend.

### `fitNode(node)`

Replaces `node.setSize([w, node.computeSize()[1]])`.

- The Vue node is `min-h-(--node-height)`, so its DOM height is the larger of `node.size` and its
  content, and `computeSize()` can disagree with the rendered node.
- `fitNode` zeroes the variable for one reflow, measures the content, and sets `node.size` to that.
- A node is sized to its content. Surplus from a manual drag stays at the bottom of the node,
  because dragging routes through litegraph.

### `requireVueNodes(node)`

`if (!requireVueNodes(this)) return;` at the top of `onNodeCreated`. When Nodes 2.0 is off it
returns `false`, suffixes the node title once, and adds two full-width buttons:

- the sentence naming the setting to turn on,
- one line saying the lists on the node do not update on the classic canvas.

Both buttons open Settings. The setting is not changed here: it applies to the operator's editor,
not to this node.

## `web/sg_panel.js`

`addPanel(node, title, onLayout)` adds two rows. The second row sets `advancedWidget`.

| where | what is in it |
|---|---|
| head | the Version's name, its status pill, the state pill |
| body | an error; `d.alert`; why nothing resolved and the Versions that do exist; `d.provenance`, `d.format`, `d.image_label`, `d.video_label`, `d.frames`, `d.colour_space`, `d.facts`, `d.generated_from`; the last run's log |
| the fold | `d.why`, `d.sources`, `d.fields`, `d.uploads` |

- A fact a widget on the node already states is not in the readout. `d.facts` is what the site
  records about this Version.
- A field with no value is dimmed in the fold, not dropped.
- A value mapped to a field this site does not have is noted as going into the description.
- The fold does not say how to create a field. That is the site's job, not a node's.

`d.format` is one plain line under the image and video rows, from `/sg/resolve`: what the file the
Load node will read is. Nothing is drawn when the answer has none.

`d.alert` is one amber line in the body, outside the fold: the name above it is not the name a Run
would write. `/sg/preview_code` answers it.

`show(d)` honours an explicit `d.state` of `"ok" | "warn" | "loading"`, which overrides the state
derived from `d.error` and `d.id`. `d.why` is in the fold, so the state pill is what states a
publish that cannot read its provenance, or one that would drop a value mapped to a field this site
does not have.

Both readout boxes are separate widgets and so separate grids. Their label columns are floored to
the same 10ch. One grid across both would align them, and a DOM widget cannot span two rows of the
node's own grid.

## `/sg/projects`

- An item has `label`, `id`, `code` and `image`.
- The answer also has `default`, the project a graph that picked none opens on.
- `image` is a presigned S3 URL, re-signed on each read and good for about 900s
  (`field_types/image`).
- A thumbnail still transcoding is returned as `""` rather than as a placeholder.
- `site.projects()` returns `(name, id)` pairs. `site.project_cards()` returns
  `{name, id, code, image}`.

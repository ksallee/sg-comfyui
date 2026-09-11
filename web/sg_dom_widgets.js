/* DOM controls placed in a node's widget grid, plus the escaping, colour and stylesheet helpers
 * the other files here import.
 *
 * A control writes into the node's declared widget rather than replacing it. Serialization, the
 * prompt and widgets_values are unchanged. The declared widget is hidden.
 *
 * Nodes 2.0 only. An extension cannot register a Vue widget: coreWidgetDefinitions is
 * module-private, and an unregistered widget type falls back to WidgetLegacy, which draws the old
 * canvas widget inside the new node. The classic canvas has no widget grid. `requireVueNodes`
 * writes that on the node.
 */
import { app } from "../../scripts/app.js";

// Verbatim from the frontend's widget markup, so a picker inherits the theme. Light mode, hover
// and focus rings need no colour of our own.
const NATIVE = {
  label: "content-center-safe truncate",
  field: "not-disabled:bg-component-node-widget-background not-disabled:text-component-node-foreground" +
         " border-none rounded-md flex w-full min-w-0 items-center overflow-hidden h-6" +
         " hover:bg-component-node-widget-background-hovered",
  ring: "min-w-0 cursor-default rounded-md transition-all focus-within:ring" +
        " focus-within:ring-component-node-widget-background-highlighted",
  trigger: "flex min-w-0 flex-1 cursor-pointer items-center overflow-hidden border-none" +
           " bg-transparent p-0 outline-none",
  chev: "flex h-full w-6 shrink-0 cursor-pointer items-center justify-center border-none" +
        " bg-transparent outline-none",
  pop: "z-3000 overflow-hidden rounded-lg border border-solid border-border-default" +
       " bg-base-background p-0 text-base-foreground shadow-md",
  viewport: "flex max-h-56 min-w-full scrollbar-thin scrollbar-thumb-alpha-smoke-500-50" +
            " scrollbar-track-transparent scrollbar-gutter-stable flex-col gap-1 overflow-y-auto p-1 text-xs",
  item: "relative flex min-h-7 cursor-pointer items-center justify-between gap-3 rounded-sm p-2" +
        " outline-none select-none hover:bg-secondary-background data-highlighted:bg-secondary-background",
};

const CSS = `
/* Under Nodes 2.0 each widget is wrapped in "flex flex-col *:flex-1 col-span-2", one item of the
   node's "grid-cols-subgrid" row. Making that wrapper a subgrid puts our label and our control in
   the node's label and control columns. display:contents also removes .sg-dom from the flow, so
   "*:flex-1" cannot stretch it, and it has no box to measure. */
.lg-node-widget > :has(> .sg-dom) { display: grid; grid-template-columns: subgrid;
  align-items: start; gap: 0 8px; }
.lg-node-widget > :has(> .sg-dom) > .sg-dom { display: contents; }
.sg-dom > .sg-lab { min-height: 24px; display: flex; align-items: center; }
/* A row with nothing to label (the panel) takes both tracks. */
.sg-dom.sg-wide > .sg-ctl { grid-column: 1 / -1; }
/* A column, so the one child fills a row given more than its content. */
.sg-dom > .sg-ctl { min-width: 0; display: flex; flex-direction: column; }
.sg-dom > .sg-ctl > * { flex: 1 1 auto; min-height: 0; }

/* Surplus height goes to the bottom rather than between rows. Each DOM widget gets an "auto" grid
   track (hasLayoutSize), and align-content:normal would stretch all of them. */
.lg-node:has(.sg-dom) .lg-node-widgets { align-content: start; }

.sg-val { min-width: 4ch; flex: 1; padding: 0 4px 0 8px; text-align: left; font-size: 12px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sg-val.is-empty { opacity: .55; font-style: italic; }
.sg-thumb { width: 18px; height: 18px; border-radius: 3px; object-fit: cover; flex: none;
  margin-left: 6px; background: rgba(128,128,128,.15); }
/* The status icon is drawn on the trigger, the way SG draws it (recipe 010). A row without one
   gets no box. */
.sg-lead-ico { display: inline-flex; align-items: center; flex: none; margin-left: 8px; }
.sg-lead-ico:empty { display: none; }

/* The popup is appended to <body>. A node is inside a transformed, clipping ancestor, where a
   fixed position resolves against the transform and an overflowing menu is cut off. The frontend's
   combo teleports for the same reason. */
.sg-pop { position: fixed; }
.sg-pop-head { display: flex; align-items: center; gap: 6px; padding: 6px 8px;
  border-bottom: 1px solid var(--color-border-default, rgba(128,128,128,.3)); }
.sg-pop-input { flex: 1; min-width: 0; border: none; background: transparent; outline: none;
  font: 12px Inter, ui-sans-serif, system-ui, sans-serif; color: inherit; }
.sg-pop-note { padding: 8px; opacity: .6; font-size: 11px; }
/* The thumbnail slot is reserved on each row and tinted where there is a picture. Names stay
   aligned, and a project without a picture shows no grey tile. */
.sg-pop-thumb { width: 22px; height: 22px; border-radius: 3px; flex: none;
  background: none center/cover no-repeat; }
.sg-pop-thumb.on { background-color: rgba(128,128,128,.15); }
.sg-pop-name { display: flex; align-items: center; gap: 8px; min-width: 0; }
.sg-pop-meta { opacity: .55; flex: none; font-size: 10px; }

/* A neutral chip. Selection is shown by the tick, not by a brighter colour. The status colour
   stays a dot. */
.sg-chips { display: flex; flex-wrap: wrap; gap: 4px; align-content: flex-start;
  padding: 2px 0; font: 11px Inter, ui-sans-serif, system-ui, sans-serif; }
.sg-more { font-style: italic; opacity: .75; }
.sg-more .sg-tick { display: none; }
.sg-chip { display: inline-flex; align-items: center; gap: 4px; padding: 1px 6px; cursor: pointer;
  font-size: 11px;
  border-radius: 9px; font-size: 10px; color: var(--color-node-component-slot-text, #b9c0c8);
  background: var(--color-component-node-widget-background, #23272d);
  border: 1px solid transparent; }
.sg-chip:hover { border-color: currentColor; }
/* No font-weight. A bolder label is a wider chip, so picking one reflows the row under the
   cursor. text-shadow thickens the same glyphs at the same metrics. */
.sg-chip.on { color: #10131a; background: #cfd6de;
  text-shadow: 0 0 .3px currentColor, 0 0 .3px currentColor; }
.sg-dot { width: 7px; height: 7px; border-radius: 50%; flex: none;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.35); }
/* The stock icons are one sheet cropped by background-position (recipe 010). Scaled to the chip's
   line, not stretched: the sheet is served at 1x and a fractional crop blurs. */
.sg-ico { flex: none; display: inline-block; background-repeat: no-repeat; }
.sg-ico-img { flex: none; height: 11px; width: auto; display: inline-block; }
.sg-ico-txt { flex: none; font-size: 9px; opacity: .85; }
.sg-pop-busy { flex: none; font-size: 11px; opacity: .7; white-space: nowrap; margin-left: 6px; }
.sg-pop-list.is-busy { opacity: .5; transition: opacity .15s; }
.sg-tick { width: 8px; flex: none; opacity: 0; }
.sg-chip.on .sg-tick { opacity: 1; }

/* A completion row: the token, then the sentence about it. The sentence gives up its width first,
   so a long field path is read in full. */
.sg-tok-name { flex: none; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px; }
.sg-tok-note { min-width: 0; flex: 0 1 auto; opacity: .55; font-size: 10px; text-align: right;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* The row travels one hop further. It is the last thing on the row, where the arrow points. */
.sg-tok-more { flex: none; display: inline-flex; align-items: center; margin-left: -4px; }
/* The Settings template is the last row and is not one of the tokens above it. */
.sg-tok-default { border-top: 1px solid var(--color-border-default, rgba(128,128,128,.3));
  border-radius: 0; }
`;

const styled = new Set();

/** Add a stylesheet to the page once, however many nodes ask for it. */
export function styleOnce(key, css) {
  if (styled.has(key)) return;
  styled.add(key);
  const el = document.createElement("style");
  el.textContent = css;
  document.head.appendChild(el);
}

const ensureCss = () => styleOnce("sg-widgets", CSS);

/** Text safe to interpolate into markup, quotes included. Each string here comes off the site. */
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/** SG's `bg_color` ("179,179,179") as three numbers, or null (probe 010). */
export function rgbParts(rgb) {
  const s = String(rgb ?? "");
  return /^\d+,\d+,\d+$/.test(s) ? s.split(",").map(Number) : null;
}

/** That colour as CSS, or `fallback` when the site sent something else. */
export const rgbCss = (rgb, fallback) => (rgbParts(rgb) ? `rgb(${rgb})` : fallback);

/** A remote URL fit for an `src`, or "". http, https and embedded images only, so nothing the site
 *  sends can put a `javascript:` scheme into the DOM. */
function safeUrl(u) {
  const s = String(u ?? "").replace(/[\t\n\r]/g, "").trim();
  return /^(?:https?:\/\/|data:image\/)/i.test(s) ? s : "";
}

// encodeURIComponent leaves ' ( ) alone, and those are what close a CSS url('…').
const CSS_ESCAPES = { '"': "%22", "'": "%27", "(": "%28", ")": "%29", "\\": "%5C",
                      "<": "%3C", ">": "%3E" };

/** The same URL fit for a CSS `url('…')`. Each character that could close the string or the
 *  attribute is percent-encoded, which HTML unescaping cannot undo. */
const cssUrl = (u) => safeUrl(u).replace(/["'()\\<>\s]/g,
  (c) => CSS_ESCAPES[c] || encodeURIComponent(c));

const ICON_TAGS = new Set(["span", "b", "i", "em", "strong", "small", "sub", "sup", "br"]);
const ICON_ATTRS = new Set(["class", "title"]);

/** Site-authored markup with the executable parts removed. A status icon's `html` is markup by
 *  design (recipe 010) and renders inside ComfyUI's origin. Unknown elements are unwrapped and each
 *  attribute but class and title is dropped, `style` included. A `<template>` is inert: parsing it
 *  runs no script and loads no image. */
function safeHtml(html) {
  const t = document.createElement("template");
  t.innerHTML = String(html ?? "");
  for (const el of t.content.querySelectorAll("*")) {
    if (!ICON_TAGS.has(el.tagName.toLowerCase())) {
      el.replaceWith(...el.childNodes);
      continue;
    }
    for (const a of [...el.attributes]) {
      if (!ICON_ATTRS.has(a.name.toLowerCase())) el.removeAttribute(a.name);
    }
  }
  return t.innerHTML;
}

/** Hide a declared widget. Nodes 2.0 reads `options.hidden` (isWidgetVisible) and litegraph reads
 *  `hidden`, so both are set. */
export function hideWidget(widget) {
  if (!widget) return;
  widget.hidden = true;
  widget.options = widget.options || {};
  widget.options.hidden = true;
}

/** Put a widget inside ComfyUI's "Show advanced inputs" fold.
 *
 *  `isWidgetVisible` reads `options.advanced` as it reads `options.hidden`, and the node's footer
 *  button appears once a widget sets it. `LGraphNode.isWidgetVisible` tests the `advanced`
 *  property. Both are set, as in `hideWidget`. */
export function advancedWidget(widget) {
  if (!widget) return widget;
  widget.advanced = true;
  widget.options = widget.options || {};
  widget.options.advanced = true;
  return widget;
}

/** How many lines a multiline widget shows.
 *
 * `rows` in INPUT_TYPES does not reach it: Nodes 2.0 builds a `customtext` with its own options
 * object and copies nothing from the spec. Set here it reaches it: WidgetTextarea v-binds each
 * option it is not told to drop onto the `<textarea>`, whose height is `auto` against an
 * auto-height row. `getMinHeight` has no effect: BaseDOMWidget.computeLayoutSize reads it, and
 * Nodes 2.0 does not call that for a widget it renders itself.
 */
export function textRows(widget, rows) {
  if (!widget) return widget;
  widget.options = widget.options || {};
  widget.options.rows = rows;
  return widget;
}

/** Restore a saved value onto a declared widget, and leave the editor able to recognise it.
 *
 * `WidgetSelectDefault.isInvalid` is "there is a value and nothing in the list matches it", and it
 * draws a red ring that stays for the session: the Vue component reads the options when it builds,
 * so a later `options.values = […]` does not reach it. A combo here is seeded for the default
 * project and repopulated per project one round trip later, so a saved graph's value arrives before
 * its list. VALIDATE_INPUTS widens the same list on the server.
 */
export function restoreValue(widget, value) {
  if (!widget) return;
  widget.value = value;
  const vals = widget.options?.values;
  if (Array.isArray(vals) && !vals.includes(value)) widget.options.values = vals.concat([value]);
}

/** Keep a widget of ours out of `widgets_values`.
 *
 * `addDOMWidget(…, {serialize: false})` does not do this: the option is never copied onto the
 * widget, and both the save and the restore test `widget.serialize`, the property
 * (LGraphNode.serialize / .configure). So `widget.serialize` reads undefined on a DOM widget and
 * filtering on it excludes nothing. An injected widget that serializes takes a slot in a positional
 * array and shifts each declared value after it.
 */
export function dontSerialize(widget) {
  if (widget) widget.serialize = false;
  return widget;
}

/** Re-apply a saved graph's widget values, by name, after litegraph has configured the node.
 * `declared` is the node's widget names in INPUT_TYPES order, which is the order of
 * widgets_values.
 *
 * dontSerialize is not enough on its own, because the frontend's save and its restore disagree:
 * `serialize()` writes `widgets_values[i]` at the index over all widgets, leaving a null hole where
 * it skipped one, while `configure()` reads with a counter that advances on serialized widgets
 * alone, so each value after our first injected row comes back off by one. Filtering on
 * `widget.serialize !== false` does not rescue it either: addDOMWidget takes `serialize` in its
 * options object and never copies it onto the widget, so a picker's `widget.serialize` is undefined
 * and it still counts.
 *
 * Two shapes are read. `widgets_values_named` is what the editor writes
 * (`Comfy.Workflow.NamedValuesRestore` is off by default). Everything else this repo produces,
 * instrument.py, tools/workflows/ and a hand-edited graph, is `declared` order and the same length.
 * A third shape is left to the frontend.
 */
export function restoreDeclaredWidgets(nodeType, declared) {
  const prev = nodeType.prototype.onConfigure;
  nodeType.prototype.onConfigure = function (info) {
    prev?.apply(this, arguments);
    const named = info?.widgets_values_named;
    const vals = info?.widgets_values || [];
    const byName = (named && typeof named === "object" && !Array.isArray(named)) ? named
      : vals.length === declared.length
        ? Object.fromEntries(vals.map((v, i) => [declared[i], v]))
        : null;
    if (!byName) return;
    for (const name of declared) {
      const v = byName[name];
      if (v === undefined || v === null) continue;   // a hole is not a value
      restoreValue(this.widgets?.find((y) => y.name === name), v);
    }
  };
}

const RESTART = "The running ComfyUI predates this version of the pack. Restart ComfyUI, then "
  + "reload this page.";

/** One route, decoded, for the pickers, the panels and the Settings rows.
 *
 * A failure returns `{items: [], error}`, the shape a picker reads. Three failures are told apart:
 * a server that did not answer, a 404, and a body that is not JSON. The routes register when
 * ComfyUI imports the pack, so a 404 means a server started before this version was installed. An
 * aborted request returns `{aborted: true}` and no sentence.
 *
 * `body` makes it a POST. `signal` comes from a cascade token or a picker.
 */
export async function call(url, { body, signal } = {}) {
  let r;
  try {
    r = await fetch(url, body === undefined ? { signal } : {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body), signal,
    });
  } catch (e) {
    if (e?.name === "AbortError") return { aborted: true, items: [] };
    return { items: [], error: `The ComfyUI server did not answer. ${e}` };
  }
  if (r.status === 404) return { items: [], error: RESTART };
  try {
    return await r.json();
  } catch (e) {
    return { items: [],
             error: `The ComfyUI server answered ${r.status} instead of JSON. ${RESTART}` };
  }
}

/** One cascade of reads at a time.
 *
 * `begin()` aborts what the previous cascade still has in flight and returns a token. A token's
 * `live` is false from the moment a later `begin()` runs, so an answer that arrives after a second
 * project was picked writes nothing. The links of one project beside the statuses of another is a
 * publish filed against the wrong show. Each step of one cascade is passed the same token, and
 * checks `live` after each await before it writes.
 */
export function cascade() {
  let current = null;
  return {
    begin() {
      current?.abort();
      const ctl = new AbortController();
      current = ctl;
      return { signal: ctl.signal, get live() { return ctl === current; } };
    },
  };
}

/** True when Nodes 2.0 is on. It is opt-in and per user directory, so it is off by default. */
export function vueNodesEnabled() {
  for (const read of [() => app.extensionManager.setting.get("Comfy.VueNodes.Enabled"),
                      () => app.ui.settings.getSettingValue("Comfy.VueNodes.Enabled")]) {
    try {
      const v = read();
      if (v !== undefined && v !== null) return !!v;
    } catch (e) { /* one of the two APIs is always present; try the other */ }
  }
  return false;
}

const NEEDS_VUE = " (needs Nodes 2.0)";

/** Write a sentence on the node when Nodes 2.0 is off, and return false. The setting is not
 *  changed here: it applies to the operator's editor, not to this node. */
export function requireVueNodes(node) {
  if (vueNodesEnabled()) return true;
  // Two buttons. On the classic canvas a button's text is drawn full width and legibly. A markdown
  // widget renders as the frontend's "Markdown: Node 2.0 only" placeholder, which names the widget
  // type rather than the action. Both buttons open Settings.
  const settings = () => app.extensionManager.command.execute("Comfy.ShowSettingsDialog");
  // The classic canvas centres a button's text and does not wrap it, so the node is widened to the
  // sentence rather than the sentence shortened to the node.
  node.size[0] = Math.max(node.size[0], 520);
  dontSerialize(node.addWidget("button", "Nodes 2.0 is off. Click to open Settings, then "
    + "Nodes 2.0, and turn on Modern Node Design.", null, settings));
  dontSerialize(node.addWidget(
    "button", "The lists on this node do not update on the classic canvas.", null, settings));
  // Copying a node copies its title and runs onNodeCreated again, so the suffix is applied once.
  if (!node.title.endsWith(NEEDS_VUE)) node.title = `${node.title}${NEEDS_VUE}`;
  return false;
}

// A litegraph id, safe to put in an attribute selector.
const ID = /^[\w-]+$/;

/** The node's own element.
 *
 * Nodes 2.0 stamps the id on it. The rows this file adds are not a way in: the frontend rebuilds a
 * DOM widget and the node keeps the detached copy, so `__sgRoots` holds elements that are in no
 * document. They are the fallback for a frontend that does not stamp the id.
 */
function nodeElement(node) {
  const id = String(node?.id ?? "");
  if (ID.test(id)) {
    const el = document.querySelector(`.lg-node[data-node-id="${id}"]`);
    if (el) return el;
  }
  for (const root of node?.__sgRoots || []) {
    const el = root.closest?.(".lg-node");
    if (el) return el;
  }
  return null;
}

/** Grey text inside an empty text widget of `node`.
 *
 * The frontend drops `placeholder` from a single-line STRING spec when it builds the widget
 * (useStringWidget, 1.51.9), and the input's own attribute is not one the Vue component manages,
 * so it is set on the input and survives a redraw. Call it again after each preview: that is also
 * what covers a rebuilt input. */
export function setPlaceholder(node, name, text) {
  const el = nodeElement(node)?.querySelector(`input[aria-label="${name}"]`);
  if (el) el.placeholder = text || "";
}

const READS = {};

/** One read per URL, however many fields ask for it. Neither the token list nor a type's fields
 *  change while the editor is open. */
const once = (url) => (READS[url] = READS[url] || call(url).then((d) => d.items || []));

/** Every field on one type. probe 002: the expensive call, so it is read one type at a time and
 *  only once the caret reaches that hop. */
const schemaFields = (type) => once(`/sg/schema_fields?type=${encodeURIComponent(type)}`);

// The unclosed brace the caret is inside, with what has been typed after it.
const OPEN_BRACE = /\{[^{}]*$/;
// `entity.Shot.code`: two hops is as deep as a template is offered.
const MAX_HOPS = 2;

/** The token path as it is typed, so `{sg_task}` is matched and inserted as `sg_task`. */
const tokenPath = (token) => token.replace(/^\{/, "").replace(/\}$/, "");

/** The types a field may be descended into from here.
 *
 * A single `entity` field only: a dotted path through a `multi_entity` field reads back nothing,
 * 200 with the key absent (probe 016). The middle segment has to be one the field accepts, or the
 * key is dropped the same way (probe 059). A type already on the path is left out, so a path
 * cannot loop back into itself.
 */
const hopTargets = (field, seen) =>
  (field && field.data_type === "entity" ? field.valid_types || [] : [])
    .filter((t) => !seen.includes(t));

/** Token completion inside a template field.
 *
 * `target` is a text input, or a node whose template widget is named by `name`. On a node the input
 * is a Vue component that is replaced on a redraw, so the listeners are on the document and each
 * event is filtered to that node's own input.
 *
 * The rows after `{` are the tokens `/sg/tokens` documents for `kind`, which is root, name,
 * sequence or movie. A token that names an entity descends: the rows after `{sg_task.` are the
 * Task's own fields, and after `{sg_task.Task.step.` the Step's. Enter or a click inserts the
 * token and closes. The right arrow, or the chevron on the row, travels one hop further and keeps
 * the popup open.
 *
 * `defaultTemplate` returns the template Settings has in force for this field. It is the last row,
 * labelled Default, whatever is typed, and picking it replaces the value with that template.
 * `project` names the project whose link type `{entity}` descends into.
 */
export function templateCompletion(target, {
  name = "", kind = "", defaultTemplate = () => "", project = () => "",
}) {
  ensureCss();
  const node = target instanceof HTMLElement ? null : target;
  const tokens = () => once(`/sg/tokens?kind=${encodeURIComponent(kind)}`
    + `&project=${encodeURIComponent(project())}`);

  const pop = document.createElement("div");
  pop.className = `sg-pop ${NATIVE.pop}`;
  pop.setAttribute("role", "listbox");
  pop.innerHTML = `<div class="sg-pop-list ${NATIVE.viewport}"></div>`;
  const list = pop.querySelector(".sg-pop-list");
  // The caret stays in the field while a row is clicked, so the token lands where it was.
  pop.addEventListener("pointerdown", (e) => e.preventDefault());

  let rows = [], at = -1, open = false, el = null, writing = false, seq = 0;

  const place = () => {
    const r = el.getBoundingClientRect();
    pop.style.left = `${Math.max(4, Math.min(r.left, innerWidth - 340))}px`;
    pop.style.width = `${Math.max(r.width, 340)}px`;
    const h = pop.offsetHeight || 220;
    pop.style.top = (r.bottom + 4 + h > innerHeight && r.top - 4 - h > 0)
      ? `${r.top - 4 - h}px` : `${r.bottom + 4}px`;
  };

  const highlight = (i) => {
    at = i;
    [...list.children].forEach((row, n) => {
      row.toggleAttribute("data-highlighted", n === at);
      if (n === at) row.scrollIntoView({ block: "nearest" });
    });
  };

  const onDown = (e) => { if (!pop.contains(e.target) && e.target !== el) close(); };
  // A wheel over the list scrolls the list and goes no further: the canvas under it would zoom.
  const onWheel = (e) => { if (pop.contains(e.target)) e.stopPropagation(); else close(); };

  function close() {
    if (!open) return;
    open = false;
    pop.remove();
    document.removeEventListener("pointerdown", onDown, true);
    window.removeEventListener("wheel", onWheel, true);
    window.removeEventListener("resize", close);
  }

  /** What follows the unclosed brace the caret is inside, or null when it is not inside one. */
  const partial = () => {
    const before = el.value.slice(0, el.selectionStart ?? el.value.length);
    const m = before.match(OPEN_BRACE);
    return m ? m[0].slice(1) : null;
  };

  /**
   * The type the segments before the caret land on, with the path that reaches it spelled in full.
   *
   * A path is `name(.Type.name)*`. A segment equal to the type just reached is that type's own
   * segment, and anything else is a field name whose type the schema names, so `{sg_task.` and
   * `{sg_task.Task.` list the same fields and the insertion spells the hop out either way. `types`
   * comes back instead where a link accepts several and which one it travels through is next.
   */
  const locate = async (segs) => {
    let type = "", seen = [], hops = 0, canon = "";
    for (let i = 0; i < segs.length; i++) {
      const seg = segs[i];
      if (!type) {
        const token = (await tokens()).find((t) => tokenPath(t.token) === seg);
        if (!token || !token.type) return null;
        type = token.type;
        seen = [type];
        hops = 1;
        canon = `${seg}.${type}.`;
        continue;
      }
      if (seg === type) continue;
      if (hops >= MAX_HOPS) return null;
      const targets = hopTargets((await schemaFields(type)).find((f) => f.name === seg), seen);
      if (!targets.length) return null;
      const next = segs[i + 1];
      if (targets.length > 1 && !targets.includes(next)) {
        return i === segs.length - 1 ? { types: targets, canon: `${canon}${seg}.` } : null;
      }
      type = targets.includes(next) ? next : targets[0];
      seen = seen.concat(type);
      hops += 1;
      canon = `${canon}${seg}.${type}.`;
    }
    return { type, seen, hops, canon };
  };

  /** The rows for what has been typed after the brace. Empty where the path names nothing. */
  const rowsFor = async (typed) => {
    const segs = typed.split(".");
    const last = segs.pop();
    const q = last.toLowerCase();
    if (!segs.length) {
      return (await tokens()).filter((t) => tokenPath(t.token).toLowerCase().includes(q))
        .map((t) => ({ label: t.token, note: t.note, text: t.token,
                       into: t.type ? `{${tokenPath(t.token)}.${t.type}.` : "" }));
    }
    const at2 = await locate(segs);
    if (!at2) return [];
    if (at2.types) {
      return at2.types.filter((t) => t.toLowerCase().includes(q))
        .map((t) => ({ label: t, note: "entity type", text: "", into: `{${at2.canon}${t}.` }));
    }
    // Every whitespace-free word of the query is matched against the display name and the code,
    // so `short` finds Short Name and `sg_` finds the fields a studio added.
    return (await schemaFields(at2.type))
      .filter((f) => `${f.display_name} ${f.name}`.toLowerCase().includes(q))
      .map((f) => {
        const targets = at2.hops < MAX_HOPS ? hopTargets(f, at2.seen) : [];
        return {
          label: f.name,
          note: `${f.display_name} · ${f.data_type}`,
          text: `{${at2.canon}${f.name}}`,
          into: targets.length === 1 ? `{${at2.canon}${f.name}.${targets[0]}.`
            : targets.length ? `{${at2.canon}${f.name}.` : "",
        };
      });
  };

  const draw = (found) => {
    rows = found;
    list.innerHTML = found.map((r, i) => `<div class="${NATIVE.item}${r.whole ? " sg-tok-default" : ""}"
      role="option" data-i="${i}"><span class="sg-tok-name">${esc(r.label)}</span>
      <span class="sg-tok-note">${esc(r.note)}</span>${r.into
        ? `<span class="sg-tok-more" data-into="1" title="Open (right arrow)">${RIGHT}</span>` : ""
      }</div>`).join("");
    [...list.children].forEach((row, i) => {
      row.onmouseenter = () => highlight(i);
      row.onclick = (e) => insert(i, !!e.target.closest?.("[data-into]"));
    });
    if (!open) {
      open = true;
      document.body.appendChild(pop);
      document.addEventListener("pointerdown", onDown, true);
      window.addEventListener("wheel", onWheel, true);
      window.addEventListener("resize", close);
    }
    place();
    highlight(0);
  };

  const sync = async () => {
    const mine = ++seq;
    if (!el || !el.isConnected) return close();
    const typed = partial();
    if (typed === null) return close();
    const found = await rowsFor(typed);
    if (mine !== seq) return;            // a later keystroke asked a newer question
    const fallback = String(defaultTemplate() || "");
    const all = found.concat(fallback
      ? [{ label: "Default", note: fallback, text: fallback, into: "", whole: true }] : []);
    if (!all.length) return close();
    draw(all);
  };

  /** Write a value the way the operator would have typed it. The node's widget reads `input`, and
   *  the Settings row saves on `change`. */
  const write = (value, caret) => {
    writing = true;
    el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    writing = false;
    el.focus();
    el.setSelectionRange(caret, caret);
  };

  /** Put the highlighted row in the field. `descend` travels one hop instead of picking. */
  const insert = (i, descend) => {
    const row = rows[i];
    if (!row || !el) return;
    const text = descend ? row.into : row.text;
    if (!text) return;
    if (row.whole) {
      close();
      return write(text, text.length);
    }
    const caret = el.selectionStart ?? el.value.length;
    const before = el.value.slice(0, caret);
    const start = before.length - before.match(OPEN_BRACE)[0].length;
    // A brace the operator has already closed is not doubled. A hop leaves it where it is.
    const rest = descend ? el.value.slice(caret) : el.value.slice(caret).replace(/^\}/, "");
    if (!descend) close();
    write(before.slice(0, start) + text + rest, start + text.length);
    if (descend) sync();
  };

  const mine = (t) => (node
    ? t?.matches?.(`input[aria-label="${name}"]`) && nodeElement(node)?.contains(t)
    : t === target);

  const onInput = (e) => { if (!writing && mine(e.target)) { el = e.target; sync(); } };
  const onFocus = (e) => { if (mine(e.target)) { el = e.target; sync(); } };
  const onKey = (e) => {
    if (!mine(e.target)) return;
    el = e.target;
    if (!open) return;                   // a closed popup leaves every key to the editor
    if (e.key === "Escape") close();
    else if (e.key === "Enter") insert(at, false);
    else if (e.key === "ArrowRight" && rows[at] && rows[at].into) insert(at, true);
    else if (e.key === "ArrowDown") highlight(Math.min(at + 1, rows.length - 1));
    else if (e.key === "ArrowUp") highlight(Math.max(at - 1, 0));
    else { setTimeout(sync, 0); return; }    // a caret moved out of the brace closes the popup
    e.preventDefault();
    e.stopPropagation();
  };

  // Capture, so Enter picks a row before the editor reads it as a key of its own.
  const on = node ? document : target;
  const listeners = [["input", onInput], ["focusin", onFocus], ["keydown", onKey]];
  for (const [event, fn] of listeners) on.addEventListener(event, fn, true);
  // A node removed with the popup open would leave it on screen and its listeners on the document.
  if (node) {
    const prev = node.onRemoved;
    node.onRemoved = function () {
      close();
      for (const [event, fn] of listeners) document.removeEventListener(event, fn, true);
      return prev?.apply(this, arguments);
    };
  }
  return { close };
}

/** Set node.size from the height the node renders.
 *
 * The Vue node is `min-h-(--node-height)`, so its DOM height is the larger of node.size and its
 * content, and computeSize() can disagree with it. Zeroing the variable for one reflow measures the
 * content. Surplus from a manual drag stays at the bottom of the node: dragging routes through
 * litegraph, not here.
 */
export function fitNode(node) {
  const el = nodeElement(node);
  if (!el) return;
  const prev = el.style.getPropertyValue("--node-height");
  el.style.setProperty("--node-height", "0px");
  const natural = el.offsetHeight;
  el.style.setProperty("--node-height", prev);
  const title = window.LiteGraph?.NODE_TITLE_HEIGHT ?? 30;
  if (Math.abs(node.size[1] + title - natural) > 2) node.setSize([node.size[0], natural - title]);
  app.graph.setDirtyCanvas(true, true);
}

/** One `label | control` row in the node's own widget grid.
 *
 * Omit `label` for a row that spans both columns. `target` is the declared widget this replaces.
 * addDOMWidget appends, which would put each picker below the plain widgets, so the row is spliced
 * back to the index of its widget.
 */
export function domRow(node, name, { label, control, target }) {
  ensureCss();
  const root = document.createElement("div");
  root.className = label ? "sg-dom" : "sg-dom sg-wide";
  if (label) {
    const lab = document.createElement("div");
    lab.className = `sg-lab ${NATIVE.label}`;
    lab.textContent = label;
    root.appendChild(lab);
  }
  const ctl = document.createElement("div");
  ctl.className = "sg-ctl";
  ctl.appendChild(control);
  root.appendChild(ctl);

  (node.__sgRoots = node.__sgRoots || []).push(root);

  const widget = node.addDOMWidget(name, name, root, {
    // .sg-dom is display:contents and has no box. The control block has the height, and it is not
    // stretched (align-items: start).
    getMinHeight: () => Math.max(ctl.offsetHeight, 24),
  });
  dontSerialize(widget);
  if (target) {
    const at = node.widgets.indexOf(target);
    const me = node.widgets.indexOf(widget);
    if (at >= 0 && me >= 0) {
      node.widgets.splice(me, 1);
      node.widgets.splice(at + (me > at ? 1 : 0), 0, widget);
    }
  }
  return { widget, root, ctl, relayout: () => requestAnimationFrame(() => fitNode(node)) };
}

/** One status icon, in whichever of the three renderings it has (recipe 010). The colour dot is
 *  the fallback, and what a sprite rule the stylesheet did not yield falls back to. */
export function iconHtml(icon, rgb) {
  // A sprite needs both pairs of numbers. Without them the redraw would stop on one status whose
  // rule the stylesheet did not yield, so the colour dot is drawn instead.
  const pair = (v) => (Array.isArray(v) && v.length === 2 ? v.map((n) => Number(n) || 0) : null);
  const offset = icon && pair(icon.offset), size = icon && pair(icon.size);
  if (icon && icon.kind === "sprite" && cssUrl(icon.url) && offset && size) {
    const [ox, oy] = offset, [w, h] = size;
    return `<span class="sg-ico" style="width:${w}px;height:${h}px;
      background-image:url('${esc(cssUrl(icon.url))}');
      background-position:${ox}px ${oy}px"></span>`;
  }
  if (icon && icon.kind === "data_uri" && safeUrl(icon.url)) {
    return `<img class="sg-ico-img" src="${esc(safeUrl(icon.url))}" alt="">`;
  }
  if (icon && icon.kind === "text" && icon.html) {
    return `<span class="sg-ico-txt">${safeHtml(icon.html)}</span>`;
  }
  return `<span class="sg-dot" style="background:${rgbCss(rgb, "#5a626b")}"></span>`;
}

const svg = (paths) => `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"
  stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
  opacity=".6" aria-hidden="true" style="flex:none">${paths}</svg>`;
const CHEVRON = svg(`<path d="m6 9 6 6 6-6"/>`);
// On a completion row that travels one hop further.
const RIGHT = svg(`<path d="m9 18 6-6-6-6"/>`);
const MAGNIFIER = svg(`<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/>`);

/** A select-shaped trigger with the search in its popup.
 *
 * `search(q, {live, signal})` is async and returns items: `{value, name, type, code, image, icon,
 * rgb}`. `value` and `name` are required. `icon` and `rgb` draw a status the way SG draws it
 * (recipe 010), on the row and on the trigger. A multi-word query goes to the site, where
 * site.entities ANDs a `contains` per word, so `gir rul` finds `giraffe_ruler`. Filtering here
 * would see the page the server sent and no more. `signal` aborts the request when a newer keystroke
 * supersedes it. `live()` is false for a superseded search, and what the search records goes behind
 * that check.
 *
 * Returns `{refresh, relayout}`. Pass the current item to `refresh` to put its thumbnail on the
 * trigger.
 */
export function searchPicker(node, target, {
  search, placeholder = "search…", onPick, label, empty = "Nothing matches those words.",
}) {
  ensureCss();
  const field = document.createElement("div");
  field.className = NATIVE.ring;
  field.innerHTML = `<div class="${NATIVE.field}">
      <button type="button" class="${NATIVE.trigger}" aria-haspopup="listbox" aria-expanded="false">
        <img class="sg-thumb" alt="" hidden>
        <span class="sg-lead-ico"></span>
        <span class="sg-val"></span>
      </button>
      <button type="button" tabindex="-1" aria-hidden="true" class="${NATIVE.chev}">${CHEVRON}</button>
    </div>`;
  const trigger = field.querySelector("button");
  const chevron = field.querySelectorAll("button")[1];
  const valEl = field.querySelector(".sg-val");
  const thumbEl = field.querySelector(".sg-thumb");
  const icoEl = field.querySelector(".sg-lead-ico");
  const { relayout } = domRow(node, `${target.name}_pick`, { label, control: field, target });

  // "None" rather than blank: an empty line does not say whether it is unset or still loading.
  const showCurrent = (item) => {
    const v = target.value;
    const set = v && v !== "(none)";
    valEl.textContent = set ? v : "None";
    valEl.classList.toggle("is-empty", !set);
    const src = set && item ? safeUrl(item.image) : "";
    thumbEl.hidden = !src;
    if (src) thumbEl.src = src;
    icoEl.innerHTML = set && item && (item.icon || item.rgb) ? iconHtml(item.icon, item.rgb) : "";
  };
  showCurrent();

  const pop = document.createElement("div");
  pop.className = `sg-pop ${NATIVE.pop}`;
  pop.setAttribute("role", "listbox");
  pop.innerHTML = `<div class="sg-pop-head">${MAGNIFIER}
      <input class="sg-pop-input" spellcheck="false" autocomplete="off">
      <span class="sg-pop-busy" hidden>Searching…</span></div>
    <div class="sg-pop-list ${NATIVE.viewport}"></div>`;
  const input = pop.querySelector(".sg-pop-input");
  const list = pop.querySelector(".sg-pop-list");
  const busyEl = pop.querySelector(".sg-pop-busy");
  input.placeholder = placeholder;
  // A search against the site takes as long as the site takes. The rows already shown dim and the
  // head reads "Searching…", rather than the list going blank on each keystroke.
  const busy = (on) => { busyEl.hidden = !on; list.classList.toggle("is-busy", on); };

  // `stale` is set from the keystroke until the answer for it is drawn. The rows on screen are the
  // previous search's, so Enter would pick one nobody typed for.
  let items = [], at = -1, seq = 0, timer, open = false, inflight = null, stale = false;

  const place = () => {
    const r = trigger.getBoundingClientRect();
    pop.style.left = `${Math.max(4, Math.min(r.left, innerWidth - 300))}px`;
    pop.style.width = `${Math.max(r.width + 40, 280)}px`;
    // Below the trigger by default, above it when there is no room below.
    const h = pop.offsetHeight || 260;
    pop.style.top = (r.bottom + 4 + h > innerHeight && r.top - 4 - h > 0)
      ? `${r.top - 4 - h}px` : `${r.bottom + 4}px`;
  };

  const highlight = (i) => {
    at = i;
    [...list.children].forEach((el, n) => {
      el.toggleAttribute("data-highlighted", n === at);
      if (n === at) el.scrollIntoView({ block: "nearest" });
    });
  };

  const render = (rows) => {
    items = rows;
    stale = false;
    if (!rows.length) {
      list.innerHTML = `<div class="sg-pop-note">${esc(empty)}</div>`;
      at = -1;
      return;
    }
    // A fixed thumbnail slot on each row once one row has a picture, so the names line up.
    const thumbs = rows.some((it) => it.image);
    list.innerHTML = rows.map((it, i) => {
      const img = cssUrl(it.image);
      return `<div class="${NATIVE.item}" role="option" data-i="${i}">
        <span class="sg-pop-name">${thumbs
          ? `<span class="sg-pop-thumb${img ? " on" : ""}"${img
              ? ` style="background-image:url('${esc(img)}')"` : ""}></span>` : ""
        }${it.icon || it.rgb ? iconHtml(it.icon, it.rgb) : ""
        }<span class="truncate">${esc(it.name)}</span></span>
        <span class="sg-pop-meta">${esc(it.code || it.type || "")}</span></div>`;
    }).join("");
    [...list.children].forEach((el, i) => {
      el.onmouseenter = () => highlight(i);
      el.onclick = () => choose(i);
    });
    highlight(0);
  };

  const choose = (i) => {
    const it = items[i];
    if (!it) return;
    target.value = it.value;
    target.callback?.(it.value);
    close();
    showCurrent(it);
    onPick?.(it);
    relayout();
  };

  // `live` is passed to `search` as well as read here. A search that records what it read, the ids
  // a picked label is turned back into, must not record an older answer's rows.
  const run = () => {
    const mine = ++seq;
    clearTimeout(timer);
    inflight?.abort();
    const ctl = new AbortController();
    inflight = ctl;
    stale = true;
    busy(true);
    timer = setTimeout(async () => {
      const live = () => mine === seq && open;
      const rows = await search(input.value.trim(), { live, signal: ctl.signal });
      if (!live()) return;                 // an older answer must never replace a newer one
      render(rows || []);
      busy(false);
    }, 180);
  };

  const onDocDown = (e) => { if (!pop.contains(e.target) && !field.contains(e.target)) close(); };
  // A wheel over the list scrolls the list and goes no further: the canvas under it would zoom.
  // A wheel anywhere else closes the popup, which is about to be scrolled off screen.
  const onWheel = (e) => { if (pop.contains(e.target)) e.stopPropagation(); else close(); };
  const close = () => {
    if (!open) return;
    open = false;
    clearTimeout(timer);
    inflight?.abort();
    pop.remove();
    trigger.setAttribute("aria-expanded", "false");
    document.removeEventListener("pointerdown", onDocDown, true);
    window.removeEventListener("wheel", onWheel, true);
    window.removeEventListener("resize", close);
  };
  const show = () => {
    if (open) return;
    open = true;
    document.body.appendChild(pop);
    place();
    trigger.setAttribute("aria-expanded", "true");
    input.value = "";
    list.innerHTML = "";
    input.focus();
    run();
    document.addEventListener("pointerdown", onDocDown, true);
    window.addEventListener("wheel", onWheel, true);
    window.addEventListener("resize", close);
  };

  trigger.onclick = (e) => { e.stopPropagation(); open ? close() : show(); };
  chevron.onclick = trigger.onclick;
  input.addEventListener("input", run);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { close(); trigger.focus(); }
    else if (e.key === "Enter") { if (!stale) choose(at); }
    else if (e.key === "ArrowDown") highlight(Math.min(at + 1, items.length - 1));
    else if (e.key === "ArrowUp") highlight(Math.max(at - 1, 0));
    else return;
    e.preventDefault();
    e.stopPropagation();
  });

  return { refresh: showCurrent, relayout };
}

/** Several statuses, any of which will do. One chip each, in the status's colour (probe 010), so
 *  no code is typed. `load()` is async and returns status items. */
export function chipSelect(node, target,
                           { load, label, empty = "This project has no statuses." }) {
  ensureCss();
  const root = document.createElement("div");
  root.className = "sg-chips";
  const { relayout } = domRow(node, `${target.name}_chips`, { label, control: root, target });

  const chosen = () => new Set(String(target.value || "").split(",").map((s) => s.trim()).filter(Boolean));

  // A show allows twenty statuses and uses two. `/sg/statuses` returns them most-used-first
  // (probe 020), so the first few are the ones the show uses.
  const KEEP = 4;
  let expanded = false;

  const draw = (items) => {
    const on = chosen();
    // A selected status is shown however far down the list it is. A fold that hides part of the
    // current value would be wrong.
    const head = items.filter((it, i) => i < KEEP || on.has(it.label));
    const shown = expanded ? items : head;
    const hidden = items.length - shown.length;
    const chip = (it) =>
      `<span class="sg-chip${on.has(it.label) ? " on" : ""}" data-label="${esc(it.label)}">
        <span class="sg-tick">✓</span>
        ${iconHtml(it.icon, it.rgb)}${esc(it.label)}</span>`;
    root.innerHTML = (shown.map(chip).join("")
      + (hidden > 0 ? `<span class="sg-chip sg-more" data-more="1">+${hidden} more</span>` : "")
      + (expanded && items.length > head.length
         ? `<span class="sg-chip sg-more" data-more="0">less</span>` : ""))
      || `<span class="sg-pop-note">${esc(empty)}</span>`;
    root.querySelectorAll(".sg-chip").forEach((el) => {
      el.onclick = () => {
        if (el.dataset.more !== undefined) { expanded = el.dataset.more === "1"; return draw(items); }
        const set = chosen();
        const l = el.dataset.label;
        set.has(l) ? set.delete(l) : set.add(l);
        const v = [...set].join(", ");
        target.value = v;
        target.callback?.(v);
        draw(items);
      };
    });
    relayout();
  };
  // Nothing is read here. The chips are for one project, and which project that is arrives one
  // round trip later. The caller reloads them then.
  return { reload: () => load().then((items) => draw(items || [])) };
}

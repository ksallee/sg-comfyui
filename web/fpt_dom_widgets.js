/* The shared widget layer: DOM controls that sit in a node's own widget grid, plus the escaping,
 * colour and stylesheet helpers every file here uses.
 *
 * A control writes into the node's *declared* widget rather than replacing it, so serialization,
 * the prompt and widgets_values are untouched — the declared widget is only hidden.
 *
 * Nodes 2.0 only. A Vue widget cannot be registered by an extension (coreWidgetDefinitions is
 * module-private), and an unregistered widget type falls back to WidgetLegacy, which draws the old
 * canvas widget inside the new node. The classic canvas has no widget grid and is not supported;
 * `requireVueNodes` says so on the node rather than degrading quietly.
 */
import { app } from "../../scripts/app.js";

// Verbatim from the frontend's own widget markup, so a picker inherits the theme instead of
// guessing at it: light mode, hover and focus rings come free, with no colour of our own.
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
/* Under Nodes 2.0 each widget is wrapped in "flex flex-col *:flex-1 col-span-2", itself one item of
   the node's own "grid-cols-subgrid" row. Turning that wrapper into a subgrid hands our label and
   our control straight to the node's label and control columns, so our rows line up with the native
   ones because they are in the same two tracks. display:contents also takes .fpt-dom out of the
   flow, so "*:flex-1" can no longer stretch it — and leaves it with no box to measure. */
.lg-node-widget > :has(> .fpt-dom) { display: grid; grid-template-columns: subgrid;
  align-items: start; gap: 0 8px; }
.lg-node-widget > :has(> .fpt-dom) > .fpt-dom { display: contents; }
.fpt-dom > .fpt-lab { min-height: 24px; display: flex; align-items: center; }
/* A row with nothing to label (the panel) takes both tracks. */
.fpt-dom.fpt-wide > .fpt-ctl { grid-column: 1 / -1; }
/* A column, so the one child fills a row given more than its content. */
.fpt-dom > .fpt-ctl { min-width: 0; display: flex; flex-direction: column; }
.fpt-dom > .fpt-ctl > * { flex: 1 1 auto; min-height: 0; }

/* Surplus height pools at the bottom rather than between rows: every DOM widget gets an "auto" grid
   track (hasLayoutSize), and align-content:normal would stretch all of them. */
.lg-node:has(.fpt-dom) .lg-node-widgets { align-content: start; }

.fpt-val { min-width: 4ch; flex: 1; padding: 0 4px 0 8px; text-align: left; font-size: 12px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fpt-val.is-empty { opacity: .55; font-style: italic; }
.fpt-thumb { width: 18px; height: 18px; border-radius: 3px; object-fit: cover; flex: none;
  margin-left: 6px; background: rgba(128,128,128,.15); }

/* The popup lives on <body>: a node sits inside a transformed, clipping ancestor, where a fixed
   position resolves against the transform and an overflowing menu is cut off. The frontend's own
   combo teleports for the same reason. */
.fpt-pop { position: fixed; }
.fpt-pop-head { display: flex; align-items: center; gap: 6px; padding: 6px 8px;
  border-bottom: 1px solid var(--color-border-default, rgba(128,128,128,.3)); }
.fpt-pop-input { flex: 1; min-width: 0; border: none; background: transparent; outline: none;
  font: 12px Inter, ui-sans-serif, system-ui, sans-serif; color: inherit; }
.fpt-pop-note { padding: 8px; opacity: .6; font-size: 11px; }
/* The thumbnail slot is reserved on every row and tinted only where there is a picture, so names
   stay aligned without an empty grey tile on every project that has none. */
.fpt-pop-thumb { width: 22px; height: 22px; border-radius: 3px; flex: none;
  background: none center/cover no-repeat; }
.fpt-pop-thumb.on { background-color: rgba(128,128,128,.15); }
.fpt-pop-name { display: flex; align-items: center; gap: 8px; min-width: 0; }
.fpt-pop-meta { opacity: .55; flex: none; font-size: 10px; }

/* One neutral chip: "chosen" reads as chosen rather than as a slightly brighter colour, and the
   status colour stays a dot to recognise. */
.fpt-chips { display: flex; flex-wrap: wrap; gap: 4px; align-content: flex-start;
  padding: 2px 0; font: 11px Inter, ui-sans-serif, system-ui, sans-serif; }
.fpt-more { font-style: italic; opacity: .75; }
.fpt-more .fpt-tick { display: none; }
.fpt-chip { display: inline-flex; align-items: center; gap: 4px; padding: 1px 6px; cursor: pointer;
  font-size: 11px;
  border-radius: 9px; font-size: 10px; color: var(--color-node-component-slot-text, #b9c0c8);
  background: var(--color-component-node-widget-background, #23272d);
  border: 1px solid transparent; }
.fpt-chip:hover { border-color: currentColor; }
/* Never font-weight: a bolder label is a wider chip, so picking one reflows the row under the
   cursor. text-shadow thickens the same glyphs at the same metrics. */
.fpt-chip.on { color: #10131a; background: #cfd6de;
  text-shadow: 0 0 .3px currentColor, 0 0 .3px currentColor; }
.fpt-dot { width: 7px; height: 7px; border-radius: 50%; flex: none;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.35); }
/* The stock icons are one sheet cropped by background-position (recipe 010). Scaled to the chip's
   line, never stretched: the sheet is served at 1x and a fractional crop blurs. */
.fpt-ico { flex: none; display: inline-block; background-repeat: no-repeat; }
.fpt-ico-img { flex: none; height: 11px; width: auto; display: inline-block; }
.fpt-ico-txt { flex: none; font-size: 9px; opacity: .85; }
.fpt-pop-busy { flex: none; font-size: 11px; opacity: .7; white-space: nowrap; margin-left: 6px; }
.fpt-pop-list.is-busy { opacity: .5; transition: opacity .15s; }
.fpt-tick { width: 8px; flex: none; opacity: 0; }
.fpt-chip.on .fpt-tick { opacity: 1; }
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

const ensureCss = () => styleOnce("fpt-widgets", CSS);

/** Text safe to interpolate into markup, quotes included: every string here comes off the site. */
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/** Flow PT's `bg_color` ("179,179,179") as three numbers, or null (probe 010). */
export function rgbParts(rgb) {
  const s = String(rgb ?? "");
  return /^\d+,\d+,\d+$/.test(s) ? s.split(",").map(Number) : null;
}

/** That colour as CSS, or `fallback` when the site sent something else. */
export const rgbCss = (rgb, fallback) => (rgbParts(rgb) ? `rgb(${rgb})` : fallback);

/** A remote URL fit for an `src`, or "". http, https and embedded images only, so nothing the site
 *  sends can carry a `javascript:` scheme into the DOM. */
function safeUrl(u) {
  const s = String(u ?? "").replace(/[\t\n\r]/g, "").trim();
  return /^(?:https?:\/\/|data:image\/)/i.test(s) ? s : "";
}

// encodeURIComponent leaves ' ( ) alone, and those are what close a CSS url('…').
const CSS_ESCAPES = { '"': "%22", "'": "%27", "(": "%28", ")": "%29", "\\": "%5C",
                      "<": "%3C", ">": "%3E" };

/** The same URL fit for a CSS `url('…')`: every character that could close the string or the
 *  attribute is percent-encoded, which HTML unescaping cannot undo. */
const cssUrl = (u) => safeUrl(u).replace(/["'()\\<>\s]/g,
  (c) => CSS_ESCAPES[c] || encodeURIComponent(c));

const ICON_TAGS = new Set(["span", "b", "i", "em", "strong", "small", "sub", "sup", "br"]);
const ICON_ATTRS = new Set(["class", "style", "title"]);

/** Site-authored markup with everything executable taken out. A status icon's `html` is markup by
 *  design (recipe 010) and it renders inside ComfyUI's own origin, so unknown elements are unwrapped
 *  and every attribute but class, style and title is dropped. A `<template>` is inert: parsing it
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

/** Put a widget inside ComfyUI's own "Show advanced inputs" fold.
 *
 *  `isWidgetVisible` reads `options.advanced` exactly as it reads `options.hidden`, and the node's
 *  footer button appears as soon as any widget carries it; `advanced`, the property, is what
 *  litegraph's own `LGraphNode.isWidgetVisible` tests. The same pair `hideWidget` sets. */
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
 * object and copies nothing from the spec. Set here it does, because WidgetTextarea v-binds every
 * option it is not told to drop onto the `<textarea>`, whose height is `auto` against an auto-height
 * row. `getMinHeight` is not the lever: it is read by BaseDOMWidget.computeLayoutSize, which
 * Nodes 2.0 never calls for a widget it renders itself.
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
 * so a later `options.values = […]` never reaches it. Every combo here is seeded for the default
 * project and repopulated per project one round trip later, so a saved graph's `task` arrives before
 * its list does. Widening the list is what VALIDATE_INPUTS already does on the server.
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
 * filtering on it excludes nothing. An injected widget that serializes eats a slot in a POSITIONAL
 * array and shifts every declared value after it.
 */
export function dontSerialize(widget) {
  if (widget) widget.serialize = false;
  return widget;
}

/** Re-apply a saved graph's widget values after litegraph has configured the node.
 *
 * dontSerialize is not enough on its own, because the frontend's save and its restore disagree:
 * `serialize()` writes `widgets_values[i]` at the index over ALL widgets, leaving a null hole where
 * it skipped one, while `configure()` reads with a counter that only advances on serialized
 * widgets, so every value after our first injected row comes back off by one. `widgets_values_named`
 * is always written by the editor and `Comfy.Workflow.NamedValuesRestore` is off by default, so that
 * name map is the reliable answer; the fallback walks the array with the counter the save used.
 */
export function restoreDeclaredWidgets(nodeType) {
  const prev = nodeType.prototype.onConfigure;
  nodeType.prototype.onConfigure = function (info) {
    prev?.apply(this, arguments);
    const widgets = this.widgets || [];
    const named = info && info.widgets_values_named;
    if (named) {
      for (const w of widgets) {
        if (w.serialize !== false && w.name in named) restoreValue(w, named[w.name]);
      }
      return;
    }
    const vals = info && info.widgets_values;
    if (!Array.isArray(vals)) return;
    let k = 0;
    for (const w of widgets) {
      if (w.serialize === false) continue;
      if (k < vals.length) restoreValue(w, vals[k]);
      k += 1;
    }
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

/** Say so on the node when Nodes 2.0 is off, and answer false. Never flips the setting: that
 *  changes the operator's whole editor, so it is their call. */
export function requireVueNodes(node) {
  if (vueNodesEnabled()) return true;
  // A button, because on the classic canvas it is the one widget whose text is drawn full width and
  // legibly: a markdown widget there renders as the frontend's "Markdown: Node 2.0 only"
  // placeholder, which names the widget type rather than what the operator has to do.
  dontSerialize(node.addWidget(
    "button", "⚠ Nodes 2.0 is off. Click to open Settings › Lite Graph.", null,
    () => app.extensionManager.command.execute("Comfy.ShowSettingsDialog")));
  node.title = `${node.title} (needs Nodes 2.0)`;
  return false;
}

function nodeElement(node) {
  for (const root of node.__fptRoots || []) {
    const el = root.closest?.(".lg-node");
    if (el) return el;
  }
  return null;
}

/** Set node.size from what the node actually renders.
 *
 * The Vue node is `min-h-(--node-height)`, so its DOM height is the larger of node.size and its
 * content and computeSize() can disagree with the picture unnoticed. Zeroing the variable for one
 * reflow asks the content what it wants, which is the only number that is never a guess. Surplus
 * from a manual drag stays at the bottom of the node: dragging routes through litegraph, not here.
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
 * Omit `label` for a row that spans both columns. `target` is the declared widget this replaces:
 * addDOMWidget appends, which would float every picker below every plain widget, so the row is
 * spliced back to where its widget sat.
 */
export function domRow(node, name, { label, control, target }) {
  ensureCss();
  const root = document.createElement("div");
  root.className = label ? "fpt-dom" : "fpt-dom fpt-wide";
  if (label) {
    const lab = document.createElement("div");
    lab.className = `fpt-lab ${NATIVE.label}`;
    lab.textContent = label;
    root.appendChild(lab);
  }
  const ctl = document.createElement("div");
  ctl.className = "fpt-ctl";
  ctl.appendChild(control);
  root.appendChild(ctl);

  (node.__fptRoots = node.__fptRoots || []).push(root);

  const widget = node.addDOMWidget(name, name, root, {
    // .fpt-dom is display:contents and has no box; the control block is what has a height, and it
    // is never stretched (align-items: start).
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

/** One status icon, whichever of the three renderings it has (recipe 010). The colour dot is the
 *  fallback, which is also what a sprite rule the stylesheet did not yield comes back as. */
export function iconHtml(icon, rgb) {
  if (icon && icon.kind === "sprite" && cssUrl(icon.url)) {
    const [ox, oy] = icon.offset, [w, h] = icon.size;
    return `<span class="fpt-ico" style="width:${Number(w)}px;height:${Number(h)}px;
      background-image:url('${esc(cssUrl(icon.url))}');
      background-position:${Number(ox)}px ${Number(oy)}px"></span>`;
  }
  if (icon && icon.kind === "data_uri" && safeUrl(icon.url)) {
    return `<img class="fpt-ico-img" src="${esc(safeUrl(icon.url))}" alt="">`;
  }
  if (icon && icon.kind === "text" && icon.html) {
    return `<span class="fpt-ico-txt">${safeHtml(icon.html)}</span>`;
  }
  return `<span class="fpt-dot" style="background:${rgbCss(rgb, "#5a626b")}"></span>`;
}

const svg = (paths) => `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"
  stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
  opacity=".6" aria-hidden="true" style="flex:none">${paths}</svg>`;
const CHEVRON = svg(`<path d="m6 9 6 6 6-6"/>`);
const MAGNIFIER = svg(`<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/>`);

/** A select-shaped trigger whose popup holds the search.
 *
 * `search(q)` is async and answers with items — `{value, name, type, code, image}`, of which only
 * `value` and `name` are required. Multi-word queries go straight to the site (site.entities ANDs a
 * `contains` per word), which is the search an artist expects: `gir rul` finds `giraffe_ruler`.
 * Filtering here would only ever see the page the server already sent.
 *
 * Returns `{refresh, relayout, close}`; pass the current item to `refresh` to put its thumbnail on
 * the trigger.
 */
export function searchPicker(node, target, {
  search, placeholder = "search…", onPick, label, empty = "Nothing matches those words.",
}) {
  ensureCss();
  const field = document.createElement("div");
  field.className = NATIVE.ring;
  field.innerHTML = `<div class="${NATIVE.field}">
      <button type="button" class="${NATIVE.trigger}" aria-haspopup="listbox" aria-expanded="false">
        <img class="fpt-thumb" alt="" hidden>
        <span class="fpt-val"></span>
      </button>
      <button type="button" tabindex="-1" aria-hidden="true" class="${NATIVE.chev}">${CHEVRON}</button>
    </div>`;
  const trigger = field.querySelector("button");
  const chevron = field.querySelectorAll("button")[1];
  const valEl = field.querySelector(".fpt-val");
  const thumbEl = field.querySelector(".fpt-thumb");
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
  };
  showCurrent();

  const pop = document.createElement("div");
  pop.className = `fpt-pop ${NATIVE.pop}`;
  pop.setAttribute("role", "listbox");
  pop.innerHTML = `<div class="fpt-pop-head">${MAGNIFIER}
      <input class="fpt-pop-input" spellcheck="false" autocomplete="off">
      <span class="fpt-pop-busy" hidden>Searching…</span></div>
    <div class="fpt-pop-list ${NATIVE.viewport}"></div>`;
  const input = pop.querySelector(".fpt-pop-input");
  const list = pop.querySelector(".fpt-pop-list");
  const busyEl = pop.querySelector(".fpt-pop-busy");
  input.placeholder = placeholder;
  // Every search runs on the site, so it takes as long as the site takes: the rows already shown
  // dim and the head says so, rather than the list going blank on each keystroke.
  const busy = (on) => { busyEl.hidden = !on; list.classList.toggle("is-busy", on); };

  let items = [], at = -1, seq = 0, timer, open = false;

  const place = () => {
    const r = trigger.getBoundingClientRect();
    pop.style.left = `${Math.max(4, Math.min(r.left, innerWidth - 300))}px`;
    pop.style.width = `${Math.max(r.width + 40, 280)}px`;
    // Below by default, above when the room is not there — a node near the bottom of the canvas is
    // the ordinary case, not the edge case.
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
    if (!rows.length) {
      list.innerHTML = `<div class="fpt-pop-note">${esc(empty)}</div>`;
      at = -1;
      return;
    }
    // One fixed thumbnail slot as soon as ANY row has a picture, so the names still line up: a list
    // where half the rows indent themselves reads as two lists.
    const thumbs = rows.some((it) => it.image);
    list.innerHTML = rows.map((it, i) => {
      const img = cssUrl(it.image);
      return `<div class="${NATIVE.item}" role="option" data-i="${i}">
        <span class="fpt-pop-name">${thumbs
          ? `<span class="fpt-pop-thumb${img ? " on" : ""}"${img
              ? ` style="background-image:url('${esc(img)}')"` : ""}></span>` : ""
        }<span class="truncate">${esc(it.name)}</span></span>
        <span class="fpt-pop-meta">${esc(it.code || it.type || "")}</span></div>`;
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

  const run = () => {
    const mine = ++seq;
    clearTimeout(timer);
    busy(true);
    timer = setTimeout(async () => {
      const rows = await search(input.value.trim());
      if (mine !== seq || !open) return;   // an older answer must never replace a newer one
      render(rows || []);
      busy(false);
    }, 180);
  };

  const onDocDown = (e) => { if (!pop.contains(e.target) && !field.contains(e.target)) close(); };
  // A wheel over the list scrolls the list and goes no further: the canvas under it would zoom.
  // A wheel anywhere else closes the popup, since it is about to be scrolled out from under.
  const onWheel = (e) => { if (pop.contains(e.target)) e.stopPropagation(); else close(); };
  const close = () => {
    if (!open) return;
    open = false;
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
    else if (e.key === "Enter") choose(at);
    else if (e.key === "ArrowDown") highlight(Math.min(at + 1, items.length - 1));
    else if (e.key === "ArrowUp") highlight(Math.max(at - 1, 0));
    else return;
    e.preventDefault();
    e.stopPropagation();
  });

  return { refresh: showCurrent, relayout, close };
}

/** Several statuses, any of which will do: one chip each, in the status's own colour (probe 010),
 *  so nothing has to be typed exactly right. `load()` is async and answers with status items. */
export function chipSelect(node, target,
                           { load, label, empty = "This project has no statuses." }) {
  ensureCss();
  const root = document.createElement("div");
  root.className = "fpt-chips";
  const { relayout } = domRow(node, `${target.name}_chips`, { label, control: root, target });

  const chosen = () => new Set(String(target.value || "").split(",").map((s) => s.trim()).filter(Boolean));

  // A show allows twenty statuses and uses two. `/fpt/statuses` returns them most-used-first
  // (probe 020), so the first few are the answer and the rest are the long tail.
  const KEEP = 4;
  let expanded = false;

  const draw = (items) => {
    const on = chosen();
    // A selected status is never hidden, however far down the tail it sits: a fold that swallows
    // part of the current answer is worse than a long row.
    const head = items.filter((it, i) => i < KEEP || on.has(it.label));
    const shown = expanded ? items : head;
    const hidden = items.length - shown.length;
    const chip = (it) =>
      `<span class="fpt-chip${on.has(it.label) ? " on" : ""}" data-label="${esc(it.label)}">
        <span class="fpt-tick">✓</span>
        ${iconHtml(it.icon, it.rgb)}${esc(it.label)}</span>`;
    root.innerHTML = (shown.map(chip).join("")
      + (hidden > 0 ? `<span class="fpt-chip fpt-more" data-more="1">+${hidden} more</span>` : "")
      + (expanded && items.length > head.length
         ? `<span class="fpt-chip fpt-more" data-more="0">less</span>` : ""))
      || `<span class="fpt-pop-note">${esc(empty)}</span>`;
    root.querySelectorAll(".fpt-chip").forEach((el) => {
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
  const reload = () => load().then((items) => draw(items || []));
  reload();
  return { relayout, reload };
}

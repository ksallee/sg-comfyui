/* Controls the canvas widgets could not give us.
 *
 * Both write into the node's *declared* widget rather than replacing it, so serialization, the
 * prompt and widgets_values are untouched — the declared widget is only hidden. That also means the
 * value need not be one the class declared, which VALIDATE_INPUTS now allows.
 *
 * These are DOM widgets on purpose. A Vue component cannot be registered by an extension
 * (coreWidgetDefinitions is module-private, there is no registerWidget), and an unregistered widget
 * type falls back to WidgetLegacy, which draws the old canvas widget inside the new node.
 *
 * Nodes 2.0 only. Every row here is `label | control` in the node's OWN widget grid, so a picker is
 * indistinguishable from the native `task` combo beside it; the classic canvas has no such grid and
 * is not supported (requireVueNodes says so on the node rather than degrading quietly).
 */
import { app } from "../../scripts/app.js";

// Verbatim from the frontend's own widget markup, so a picker inherits the theme instead of
// guessing at it. Copying the class strings is what keeps light mode, hover and focus rings right
// without a single colour of our own.
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
   our control straight to the node's label and control columns — which is the whole trick: our rows
   line up with task because they are in the same two tracks, not because we guessed its width.
   display:contents also takes .fpt-dom out of the flow, so "*:flex-1" can no longer stretch it. */
.lg-node-widget > :has(> .fpt-dom) { display: grid; grid-template-columns: subgrid;
  align-items: start; gap: 0 8px; }
.lg-node-widget > :has(> .fpt-dom) > .fpt-dom { display: contents; }
.fpt-dom > .fpt-lab { min-height: 24px; display: flex; align-items: center; }
/* A row with nothing to label (the panel) takes both tracks. */
.fpt-dom.fpt-wide > .fpt-ctl { grid-column: 1 / -1; }
/* A column, so the one child fills the row when the row is given more than its content — which is
   how the readout takes the slack from a node the operator dragged taller. */
.fpt-dom > .fpt-ctl { min-width: 0; display: flex; flex-direction: column; }
.fpt-dom > .fpt-ctl > * { flex: 1 1 auto; min-height: 0; }

/* Surplus height is pooled at the bottom rather than sprinkled between rows: every DOM widget gets
   an "auto" grid track (hasLayoutSize), and align-content:normal would stretch all of them. */
.lg-node:has(.fpt-dom) .lg-node-widgets { align-content: start; }

.fpt-val { min-width: 4ch; flex: 1; padding: 0 4px 0 8px; text-align: left; font-size: 12px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fpt-val.is-empty { opacity: .55; font-style: italic; }
.fpt-thumb { width: 18px; height: 18px; border-radius: 3px; object-fit: cover; flex: none;
  margin-left: 6px; background: rgba(128,128,128,.15); }

/* The popup lives on <body>: a node is inside a transformed, clipping ancestor, where a fixed
   position resolves against the transform and an overflowing menu is cut off. The frontend's own
   combo teleports for the same reason. */
.fpt-pop { position: fixed; }
.fpt-pop-head { display: flex; align-items: center; gap: 6px; padding: 6px 8px;
  border-bottom: 1px solid var(--color-border-default, rgba(128,128,128,.3)); }
.fpt-pop-input { flex: 1; min-width: 0; border: none; background: transparent; outline: none;
  font: 12px Inter, ui-sans-serif, system-ui, sans-serif; color: inherit; }
.fpt-pop-note { padding: 8px; opacity: .6; font-size: 11px; }
/* The slot is reserved on every row and tinted only where there is a picture: an empty grey tile
   on every project without one is more noise than the alignment is worth. */
.fpt-pop-thumb { width: 22px; height: 22px; border-radius: 3px; flex: none;
  background: none center/cover no-repeat; }
.fpt-pop-thumb.on { background-color: rgba(128,128,128,.15); }
.fpt-pop-name { display: flex; align-items: center; gap: 8px; min-width: 0; }
.fpt-pop-meta { opacity: .55; flex: none; font-size: 10px; }

/* One neutral chip, so "chosen" reads as chosen rather than as a slightly brighter colour. The
   status colour is a dot: still there to recognise, no longer carrying the selected state too. */
.fpt-chips { display: flex; flex-wrap: wrap; gap: 4px; align-content: flex-start;
  padding: 2px 0; font: 11px Inter, ui-sans-serif, system-ui, sans-serif; }
.fpt-chip { display: inline-flex; align-items: center; gap: 5px; padding: 2px 8px; cursor: pointer;
  border-radius: 9px; font-size: 10px; color: var(--color-node-component-slot-text, #b9c0c8);
  background: var(--color-component-node-widget-background, #23272d);
  border: 1px solid transparent; }
.fpt-chip:hover { border-color: currentColor; }
.fpt-chip.on { color: #10131a; background: #cfd6de; font-weight: 600; }
.fpt-dot { width: 7px; height: 7px; border-radius: 50%; flex: none;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.35); }
/* The stock icons are one sheet cropped by background-position (recipe 010). Scaled to the chip's
   line, never stretched: the sheet is served at 1x and a fractional crop blurs. */
.fpt-ico { flex: none; display: inline-block; background-repeat: no-repeat; }
.fpt-ico-img { flex: none; height: 11px; width: auto; display: inline-block; }
.fpt-ico-txt { flex: none; font-size: 9px; opacity: .85; }
.fpt-tick { width: 8px; flex: none; opacity: 0; }
.fpt-chip.on .fpt-tick { opacity: 1; }
`;
let injected = false;
function ensureCss() {
  if (injected) return;
  injected = true;
  const el = document.createElement("style");
  el.textContent = CSS;
  document.head.appendChild(el);
}

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/** Hide a declared widget. Nodes 2.0 reads `options.hidden` (isWidgetVisible); `hidden` is one more
 *  line and keeps litegraph's own layout in step, so it stays. */
export function hideWidget(widget) {
  if (!widget) return;
  widget.hidden = true;
  widget.options = widget.options || {};
  widget.options.hidden = true;
}

/** Put a widget inside ComfyUI's OWN "Show advanced inputs" fold, beside `code_template` and the
 *  rest of the fine print.
 *
 *  `isWidgetVisible` reads `options.advanced` exactly as it reads `options.hidden`
 *  (useProcessedWidgets.ts), and the node's footer button appears as soon as any widget carries it
 *  (`widgets.some(w => w.options?.advanced)`). `advanced`, the property, is what litegraph's own
 *  `LGraphNode.isWidgetVisible` tests — the same pair `hideWidget` sets. */
export function advancedWidget(widget) {
  if (!widget) return widget;
  widget.advanced = true;
  widget.options = widget.options || {};
  widget.options.advanced = true;
  return widget;
}

/** Keep a widget of ours out of `widgets_values`.
 *
 * `addDOMWidget(…, {serialize: false})` does NOT do this: both the save and the restore test
 * `widget.serialize`, the property, and never the option (LGraphNode.serialize / .configure). An
 * injected widget that serializes eats a slot in a POSITIONAL array, which silently shifts every
 * declared value after it — the Load node restored `statuses = "version number in the name"`, and
 * the Publish node put `attach_workflow`'s `true` into `source_versions`.
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
 * widgets. Every value after our first injected row therefore comes back off by one. Since
 * `widgets_values_named` is always written and `Comfy.Workflow.NamedValuesRestore` is off by
 * default, that name map is the reliable answer; the fallback aligns on the index the save used.
 */
export function restoreDeclaredWidgets(nodeType) {
  const prev = nodeType.prototype.onConfigure;
  nodeType.prototype.onConfigure = function (info) {
    prev?.apply(this, arguments);
    const widgets = this.widgets || [];
    const named = info && info.widgets_values_named;
    if (named) {
      for (const w of widgets) {
        if (w.serialize !== false && w.name in named) w.value = named[w.name];
      }
      return;
    }
    const vals = info && info.widgets_values;
    if (!Array.isArray(vals)) return;
    widgets.forEach((w, i) => { if (w.serialize !== false && i < vals.length) w.value = vals[i]; });
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

/** Say so on the node when Nodes 2.0 is off, and answer false. Never flips the setting: it changes
 *  the operator's whole editor, so it is their call. */
export function requireVueNodes(node) {
  if (vueNodesEnabled()) return true;
  // A button, because on the classic canvas it is the one widget whose text is drawn full width and
  // legibly: a markdown widget there renders as the frontend's own "Markdown: Node 2.0 only"
  // placeholder, which names the widget type rather than what the operator has to do.
  dontSerialize(node.addWidget(
    "button", "⚠ needs Nodes 2.0 — click to open Settings › Lite Graph", null,
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
 * content — which means computeSize() can disagree with the picture and nothing notices. Zeroing
 * the variable for one reflow asks the content what it wants, which is the only number that is
 * never a guess.
 *
 * There is no "grow" row any more. The readout used to pool a taller node's surplus, which sounded
 * generous and in practice put an empty band under two lines of text every time the CONTENT shrank
 * — a node widened until the status chips needed one row fewer, a fold shut. It never even served
 * the case it was for: dragging a node taller routes through litegraph, not through here.
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
 * `target` is the declared widget this replaces: addDOMWidget appends, which would float every
 * picker below every plain widget, so the row is spliced back to where its widget sat.
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
    // .fpt-dom is display:contents under Nodes 2.0 and has no box; the control block is what has a
    // height, and it is never stretched (align-items: start).
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

/** One status icon, whichever of the three renderings it has (recipe 010). Falls back to the
 *  colour dot when the sheet rule was not found, which is what `sprite()` returning null means. */
export function iconHtml(icon, rgb) {
  if (icon && icon.kind === "sprite") {
    const [ox, oy] = icon.offset, [w, h] = icon.size;
    return `<span class="fpt-ico" style="width:${w}px;height:${h}px;
      background-image:url('${icon.url}');background-position:${ox}px ${oy}px"></span>`;
  }
  if (icon && icon.kind === "data_uri" && icon.url) {
    return `<img class="fpt-ico-img" src="${icon.url}" alt="">`;
  }
  if (icon && icon.kind === "text" && icon.html) {
    return `<span class="fpt-ico-txt">${icon.html}</span>`;
  }
  const dot = /^\d+,\d+,\d+$/.test(rgb || "") ? `rgb(${rgb})` : "#5a626b";
  return `<span class="fpt-dot" style="background:${dot}"></span>`;
}

const svg = (paths) => `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"
  stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
  opacity=".6" aria-hidden="true" style="flex:none">${paths}</svg>`;
const CHEVRON = svg(`<path d="m6 9 6 6 6-6"/>`);
const MAGNIFIER = svg(`<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/>`);

/** A select-shaped trigger whose popup holds the search.
 *
 * Multi-word goes straight to Flow PT (site.entities splits on whitespace and ANDs a `contains` per
 * word), which is the search an artist expects: `gir rul` finds `giraffe_ruler`. Filtering here
 * would only ever see the page the server already sent.
 *
 * Items are `{value, name, type, code, image}`; only `value` and `name` are required.
 */
export function searchPicker(node, target, {
  search, placeholder = "search…", onPick, label, empty = "nothing matches that",
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
    const src = set && item && item.image;
    thumbEl.hidden = !src;
    if (src) thumbEl.src = src;
  };
  showCurrent();

  // --- the popup, on <body>
  const pop = document.createElement("div");
  pop.className = `fpt-pop ${NATIVE.pop}`;
  pop.setAttribute("role", "listbox");
  pop.innerHTML = `<div class="fpt-pop-head">${MAGNIFIER}
      <input class="fpt-pop-input" spellcheck="false" autocomplete="off"></div>
    <div class="fpt-pop-list ${NATIVE.viewport}"></div>`;
  const input = pop.querySelector(".fpt-pop-input");
  const list = pop.querySelector(".fpt-pop-list");
  input.placeholder = placeholder;

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
    // One fixed slot for the thumbnail as soon as ANY row has one, so the names still line up: a
    // list where half the rows indent themselves reads as two lists.
    const thumbs = rows.some((it) => it.image);
    list.innerHTML = rows.map((it, i) => `<div class="${NATIVE.item}" role="option" data-i="${i}">
        <span class="fpt-pop-name">${thumbs
          ? `<span class="fpt-pop-thumb${it.image ? " on" : ""}"${it.image
              ? ` style="background-image:url('${esc(it.image)}')"` : ""}></span>` : ""
        }<span class="truncate">${esc(it.name)}</span></span>
        <span class="fpt-pop-meta">${esc(it.code || it.type || "")}</span></div>`).join("");
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
    timer = setTimeout(async () => {
      const rows = await search(input.value.trim());
      if (mine !== seq || !open) return;   // an older answer must never replace a newer one
      render(rows || []);
    }, 180);
  };

  const onDocDown = (e) => { if (!pop.contains(e.target) && !field.contains(e.target)) close(); };
  const close = () => {
    if (!open) return;
    open = false;
    pop.remove();
    trigger.setAttribute("aria-expanded", "false");
    document.removeEventListener("pointerdown", onDocDown, true);
    window.removeEventListener("wheel", close, true);
    window.removeEventListener("resize", close);
  };
  const show = () => {
    if (open) return;
    open = true;
    document.body.appendChild(pop);
    place();
    trigger.setAttribute("aria-expanded", "true");
    input.value = "";
    list.innerHTML = `<div class="fpt-pop-note">searching…</div>`;
    input.focus();
    run();
    document.addEventListener("pointerdown", onDocDown, true);
    window.addEventListener("wheel", close, true);
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

/** Several statuses, any of which will do. This was a comma-separated text field because ComfyUI's
 *  MultiCombo rendered at 16px inside an 82px slot; as chips it shows each status in its own colour
 *  (probe 010) and says what is selected without the operator typing a label exactly right. */
export function chipSelect(node, target, { load, label, empty = "this project offers no statuses" }) {
  ensureCss();
  const root = document.createElement("div");
  root.className = "fpt-chips";
  const { relayout } = domRow(node, `${target.name}_chips`, { label, control: root, target });

  const chosen = () => new Set(String(target.value || "").split(",").map((s) => s.trim()).filter(Boolean));

  const draw = (items) => {
    const on = chosen();
    root.innerHTML = items.map((it) => (
      `<span class="fpt-chip${on.has(it.label) ? " on" : ""}" data-label="${esc(it.label)}">
        <span class="fpt-tick">✓</span>
        ${iconHtml(it.icon, it.rgb)}${esc(it.label)}</span>`
    )).join("") || `<span class="fpt-pop-note">${esc(empty)}</span>`;
    root.querySelectorAll(".fpt-chip").forEach((el) => {
      el.onclick = () => {
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

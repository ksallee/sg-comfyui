/* Controls the canvas widgets could not give us.
 *
 * Both write into the node's *declared* widget rather than replacing it, so serialization, the
 * prompt and widgets_values are untouched — the declared widget is only hidden. That also means the
 * value need not be one the class declared, which VALIDATE_INPUTS now allows.
 *
 * These are DOM widgets on purpose. A Vue component cannot be registered by an extension
 * (coreWidgetDefinitions is module-private, there is no registerWidget), and an unregistered widget
 * type falls back to WidgetLegacy, which draws the old canvas widget inside the new node. DOM
 * widgets render correctly under both renderers, so this is the only thing that works in both.
 */
const CSS = `
/* The Vue node wraps each widget in "flex flex-col *:flex-1", which STRETCHES our element to the
   height it was given. Measuring that element then reports the allocated height, not the content
   height, so the widget could only ever grow — the gaps, and the chips changing height when the
   node is resized. The inner block is not stretched, so it is what we measure. */
/* flex: none beats the wrapper's "*:flex-1", which otherwise stretches this to the row height and
   leaves the content floating in the middle of it. Content height, top aligned, slack below. */
.fpt-dom { display: block; overflow: hidden; flex: 0 0 auto; align-self: start; }
.fpt-inner { display: block; }
.fpt-pick { display: flex; flex-direction: column; gap: 4px; font: 11px ui-sans-serif, system-ui, sans-serif; }
.fpt-pick-input { width: 100%; box-sizing: border-box; padding: 4px 6px; color: #cfd3d8;
  background: #1a1d21; border: 1px solid #3a4048; border-radius: 4px; outline: none; }
.fpt-pick-input:focus { border-color: #4a5563; }
.fpt-pick-list { max-height: 150px; overflow-y: auto; border: 1px solid #35393f; border-radius: 4px;
  background: #17191d; display: none; }
.fpt-pick.open .fpt-pick-list { display: block; }
.fpt-pick-row { display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 4px 6px; cursor: pointer; }
.fpt-pick-row:hover, .fpt-pick-row.on { background: #23272d; }
.fpt-pick-name { color: #e8ebee; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fpt-pick-type { color: #8b939c; font-size: 10px; flex: none; }
.fpt-pick-empty { padding: 5px 6px; color: #8b939c; }
/* max-height, or the chips reflow as the node is resized and the measured height chases the width */
.fpt-chips { display: flex; flex-wrap: wrap; gap: 4px; max-height: 88px; overflow-y: auto;
  align-content: flex-start; }
/* One neutral chip, so "chosen" reads as chosen rather than as a slightly brighter colour. The
   status colour is a dot: still there to recognise, no longer carrying the selected state too. */
.fpt-chip { display: inline-flex; align-items: center; gap: 5px; padding: 2px 8px; cursor: pointer;
  border-radius: 9px; font-size: 10px; color: #b9c0c8; background: #23272d;
  border: 1px solid #33383f; }
.fpt-chip:hover { border-color: #4a5563; }
.fpt-chip.on { color: #10131a; background: #cfd6de; border-color: #cfd6de; font-weight: 600; }
.fpt-dot { width: 7px; height: 7px; border-radius: 50%; flex: none;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.35); }
/* The stock icons are one sheet cropped by background-position (recipe 010). Scaled to the chip's
   line, never stretched: the sheet is served at 1x and a fractional crop blurs. */
.fpt-ico { flex: none; display: inline-block; background-repeat: no-repeat; }
.fpt-ico-img { flex: none; height: 11px; width: auto; display: inline-block; }
.fpt-ico-txt { flex: none; font-size: 9px; opacity: .85; }
.fpt-tick { width: 8px; flex: none; opacity: 0; }
.fpt-chip.on .fpt-tick { opacity: 1; }
.fpt-pick-current { color: #8b939c; }
.fpt-pick-current b { color: #e8ebee; font-weight: 600; }
.fpt-pick-current i { color: #8b939c; font-style: normal; }
`;
let injected = false;
function ensureCss() {
  if (injected) return;
  injected = true;
  const el = document.createElement("style");
  el.textContent = CSS;
  document.head.appendChild(el);
}

/** Hide a declared widget in both renderers.
 *
 * The canvas renderer reads `widget.hidden`; Vue nodes read `widget.options.hidden`
 * (processedWidgetRenderModel.isWidgetVisible). Setting one leaves the control visible in the other,
 * which shows the operator two controls for the same value.
 */
export function hideWidget(widget) {
  if (!widget) return;
  widget.hidden = true;
  widget.options = widget.options || {};
  widget.options.hidden = true;
}


function mount(node, name, content, onLayout, target) {
  const root = document.createElement("div");
  root.className = "fpt-dom";
  const inner = document.createElement("div");
  inner.className = "fpt-inner";
  inner.appendChild(content);
  root.appendChild(inner);
  const w = node.addDOMWidget(name, name, root, {
    serialize: false,
    // The inner block, never the root: see the note by .fpt-dom.
    getMinHeight: () => Math.min(Math.max(inner.offsetHeight + 4, 22), 420),
  });
  // addDOMWidget appends, which puts every picker below every plain widget and floats whatever is
  // left visible to the top. Sit where the declared widget the picker replaces actually sits.
  if (target) {
    const at = node.widgets.indexOf(target);
    const me = node.widgets.indexOf(w);
    if (at >= 0 && me >= 0) {
      node.widgets.splice(me, 1);
      node.widgets.splice(at + (me > at ? 1 : 0), 0, w);
    }
  }
  const relayout = () => {
    requestAnimationFrame(() => {
      node.setSize([node.size[0], node.computeSize()[1]]);
      onLayout?.();
    });
  };
  return { widget: w, relayout };
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

/** Type-ahead over a server-side search. Multi-word goes straight to Flow PT (site.entities splits
 *  on whitespace and ANDs a `contains` per word), which is the search an artist expects: `gir rul`
 *  finds `giraffe_ruler`. Filtering here would only ever see the page the server already sent. */
export function searchPicker(node, target, { search, placeholder = "search…", onPick, label }) {
  ensureCss();
  const root = document.createElement("div");
  root.className = "fpt-pick";
  root.innerHTML = `<div class="fpt-pick-current"></div>
    <input class="fpt-pick-input" spellcheck="false">
    <div class="fpt-pick-list"></div>`;
  const cur = root.querySelector(".fpt-pick-current");
  const input = root.querySelector(".fpt-pick-input");
  const list = root.querySelector(".fpt-pick-list");
  input.placeholder = placeholder;
  const { relayout } = mount(node, `${target.name}_pick`, root, null, target);

  // The declared widget carried the label; it is hidden now, so the picker has to say what it is.
  // "None" rather than blank: an empty line does not tell you whether it is unset or still loading.
  const showCurrent = () => {
    const v = target.value;
    const set = v && v !== "(none)";
    cur.innerHTML = `${label ? `${label}: ` : ""}${set ? `<b>${v}</b>` : "<i>None</i>"}`;
  };
  showCurrent();

  let seq = 0, timer;
  const render = (items) => {
    list.innerHTML = items.length
      ? items.map((it, i) => `<div class="fpt-pick-row" data-i="${i}">
           <span class="fpt-pick-name">${it.name}</span>
           <span class="fpt-pick-type">${it.type || ""}</span></div>`).join("")
      : `<div class="fpt-pick-empty">nothing matches</div>`;
    list.querySelectorAll(".fpt-pick-row").forEach((el) => {
      el.onclick = () => {
        const it = items[Number(el.dataset.i)];
        target.value = it.value;
        target.callback?.(it.value);
        root.classList.remove("open");
        input.value = "";
        showCurrent();
        onPick?.(it);
        relayout();
      };
    });
    root.classList.add("open");
    relayout();
  };

  const run = () => {
    const mine = ++seq;
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const items = await search(input.value.trim());
      if (mine !== seq) return;      // an older answer must never replace a newer one
      render(items || []);
    }, 180);
  };
  input.addEventListener("input", run);
  input.addEventListener("focus", run);
  input.addEventListener("blur", () => setTimeout(() => {
    root.classList.remove("open");
    relayout();
  }, 180));
  return { refresh: showCurrent, relayout };
}

/** Several statuses, any of which will do. This was a comma-separated text field because ComfyUI's
 *  MultiCombo rendered at 16px inside an 82px slot; as chips it shows each status in its own colour
 *  (probe 010) and says what is selected without the operator typing a label exactly right. */
export function chipSelect(node, target, { load }) {
  ensureCss();
  const root = document.createElement("div");
  root.className = "fpt-chips";
  const { relayout } = mount(node, `${target.name}_chips`, root, null, target);

  const chosen = () => new Set(String(target.value || "").split(",").map((s) => s.trim()).filter(Boolean));

  const draw = (items) => {
    const on = chosen();
    root.innerHTML = items.map((it) => (
      `<span class="fpt-chip${on.has(it.label) ? " on" : ""}" data-label="${it.label}">
        <span class="fpt-tick">\u2713</span>
        ${iconHtml(it.icon, it.rgb)}${it.label}</span>`
    )).join("") || `<span class="fpt-pick-empty">no statuses on this project</span>`;
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

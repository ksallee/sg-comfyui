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
.fpt-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.fpt-chip { padding: 2px 7px; border-radius: 9px; cursor: pointer; opacity: .38;
  border: 1px solid transparent; font-size: 10px; }
.fpt-chip.on { opacity: 1; }
.fpt-pick-current { color: #8b939c; }
.fpt-pick-current b { color: #e8ebee; font-weight: 600; }
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

function fg(rgb) {
  if (!/^\d+,\d+,\d+$/.test(rgb || "")) return "#e8ebee";
  const [r, g, b] = rgb.split(",").map(Number);
  return (0.299 * r + 0.587 * g + 0.114 * b) > 150 ? "#1b1d21" : "#e8ebee";
}

function mount(node, name, root, onLayout) {
  const w = node.addDOMWidget(name, name, root, {
    serialize: false,
    // The framework sizes Vue widgets; a DOM widget has to say how tall it is, and it must be
    // measured after layout or it reports the height it had before the content arrived.
    getMinHeight: () => Math.min(Math.max(root.scrollHeight + 8, 26), 400),
  });
  const relayout = () => {
    requestAnimationFrame(() => {
      node.setSize([node.size[0], node.computeSize()[1]]);
      onLayout?.();
    });
  };
  return { widget: w, relayout };
}

/** Type-ahead over a server-side search. Multi-word goes straight to Flow PT (site.entities splits
 *  on whitespace and ANDs a `contains` per word), which is the search an artist expects: `gir rul`
 *  finds `giraffe_ruler`. Filtering here would only ever see the page the server already sent. */
export function searchPicker(node, target, { search, placeholder = "search…", onPick }) {
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
  const { relayout } = mount(node, `${target.name}_pick`, root);

  const showCurrent = () => {
    const v = target.value;
    cur.innerHTML = v && v !== "(none)" ? `<b>${v}</b>` : "nothing picked";
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
  const { relayout } = mount(node, `${target.name}_chips`, root);

  const chosen = () => new Set(String(target.value || "").split(",").map((s) => s.trim()).filter(Boolean));

  const draw = (items) => {
    const on = chosen();
    root.innerHTML = items.map((it) => {
      const bg = /^\d+,\d+,\d+$/.test(it.rgb || "") ? `rgb(${it.rgb})` : "#3a4048";
      return `<span class="fpt-chip${on.has(it.label) ? " on" : ""}" data-label="${it.label}"
        style="background:${bg};color:${fg(it.rgb)}">${it.label}</span>`;
    }).join("") || `<span class="fpt-pick-empty">no statuses on this project</span>`;
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

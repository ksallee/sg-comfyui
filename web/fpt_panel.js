// A small readout both nodes share: what the node is pointing at, and what it last did.
//
// A DOM widget rather than a read-only textarea, because the useful parts here are a status — which
// Flow PT already gives a colour (probe 010, bg_color is comma-separated RGB) — and a run log that
// wants to be distinguishable at a glance. Collapsible, because once a graph is set up this is
// reference material, not something to keep reading.

const CSS = `
/* box-sizing and a full-width block: the DOM widget's container is sized by the node, and without
   these the panel keeps its content width and sits narrow inside it. */
.fpt-panel { font: 11px ui-monospace, SFMono-Regular, Menlo, monospace; color: #cfd3d8;
             background: #23262b; border: 1px solid #35393f; border-radius: 6px;
             overflow: hidden; display: flex; flex-direction: column;
             box-sizing: border-box; width: 100%; height: 100%; }
.fpt-panel * { box-sizing: border-box; }
.fpt-head { display: flex; align-items: center; gap: 6px; padding: 4px 8px; cursor: pointer;
            background: #2b2f35; border-bottom: 1px solid #35393f; user-select: none; }
.fpt-head:hover { background: #313640; }
.fpt-caret { width: 9px; opacity: .6; transition: transform .12s; }
.fpt-panel.collapsed .fpt-caret { transform: rotate(-90deg); }
.fpt-panel.collapsed .fpt-body { display: none; }
.fpt-title { font-weight: 600; color: #e8ebee; white-space: nowrap; overflow: hidden;
             text-overflow: ellipsis; flex: 1; }
.fpt-icon { width: 11px; height: 11px; vertical-align: -1px; margin-right: 3px; }
.fpt-pill { padding: 1px 7px; border-radius: 9px; font-size: 10px; font-weight: 600;
            white-space: nowrap; }
.fpt-body { padding: 6px 8px; overflow: auto; display: flex; flex-direction: column; gap: 5px; }
.fpt-row { display: flex; gap: 6px; }
.fpt-k { color: #7f868f; min-width: 62px; flex: none; }
.fpt-v { color: #cfd3d8; word-break: break-word; }
.fpt-why { color: #7f868f; font-style: italic; }
.fpt-toggle { cursor: pointer; }
.fpt-toggle:hover { color: #cfd3d8; }
.fpt-sec { color: #7f868f; text-transform: uppercase; letter-spacing: .06em; font-size: 9px;
           border-top: 1px solid #35393f; padding-top: 5px; margin-top: 1px; }
.fpt-ok { color: #7fd18b; }
.fpt-err { color: #f08a8a; white-space: pre-wrap; }
.fpt-dim { color: #7f868f; }
/* The editor lives here, below the readout, rather than as a node widget: a declared widget renders
   above this panel and cannot be moved below it, because widgets_values is positional. */
.fpt-editor { display: none; border-top: 1px solid #35393f; padding: 6px 8px; flex: none; }
.fpt-panel.editing .fpt-editor { display: block; }
.fpt-panel.collapsed .fpt-editor { display: none; }
.fpt-editor textarea { width: 100%; height: 144px; box-sizing: border-box; resize: none;
    font: 10px ui-monospace, SFMono-Regular, Menlo, monospace; color: #cfd3d8;
    background: #1a1d21; border: 1px solid #3a4048; border-radius: 4px; padding: 5px 6px; }
.fpt-editor textarea:focus { outline: none; border-color: #4a5563; }
`;

let injected = false;
function ensureCss() {
  if (injected) return;
  injected = true;
  const el = document.createElement("style");
  el.textContent = CSS;
  document.head.appendChild(el);
}

// Flow PT gives "179,179,179". Pick readable text for it rather than guessing a fixed pair.
// A real icon where Flow PT has one that can be drawn; the colour badge otherwise. probe 010 found
// 23 of 25 icons here are sprite-addressed with no locatable sprite, so the badge is the main path.
function badge(status) {
  const ic = status.icon || {};
  if (ic.kind === "image" && ic.url) {
    return `<img class="fpt-icon" src="${ic.url}" alt="">` + pill(esc(status.label), status.rgb);
  }
  return pill(esc(status.label), status.rgb);
}

function pill(label, rgb) {
  const bg = rgb && /^\d+,\d+,\d+$/.test(rgb) ? `rgb(${rgb})` : "#3a4048";
  let fg = "#e8ebee";
  if (rgb && /^\d+,\d+,\d+$/.test(rgb)) {
    const [r, g, b] = rgb.split(",").map(Number);
    fg = (0.299 * r + 0.587 * g + 0.114 * b) > 150 ? "#1b1d21" : "#e8ebee";
  }
  return `<span class="fpt-pill" style="background:${bg};color:${fg}">${label}</span>`;
}

// The query in Flow PT's own language, so it can be read, copied, and pasted into `filters`.
function filterBlock(d) {
  if (!d || !d.filters) return "";
  // Only the heading: the filter itself is in the editable box below, and showing it twice was just
  // two copies of the same thing.
  return `<div class="fpt-sec fpt-toggle" title="Show or hide the SG Filters box">` +
    `SG Filters <span class="fpt-dim">— click to edit</span></div>`;
}

const esc = (s) => String(s ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

export function addPanel(node, title = "Flow PT", onLayout = null) {
  ensureCss();
  const root = document.createElement("div");
  root.className = "fpt-panel";
  root.innerHTML = `<div class="fpt-head">
      <svg class="fpt-caret" viewBox="0 0 10 10"><path d="M1 3l4 4 4-4" stroke="currentColor"
        fill="none" stroke-width="1.6"/></svg>
      <span class="fpt-title">${esc(title)}</span></div>
    <div class="fpt-body"></div>
    <div class="fpt-editor"><textarea spellcheck="false"></textarea></div>`;
  const head = root.querySelector(".fpt-head");
  const body = root.querySelector(".fpt-body");
  // Kept outside the body so redrawing the readout cannot destroy it mid-edit.
  const editor = root.querySelector(".fpt-editor");
  const area = editor.querySelector("textarea");
  // Every fold has to re-measure the node: hiding the content without that leaves the widget
  // holding its old height and the box looks unchanged.
  head.addEventListener("click", () => {
    root.classList.toggle("collapsed");
    if (onLayout) onLayout();
  });
  // The SG Filters textarea is a declared widget and sits immediately above this panel, so its fold
  // control belongs here rather than in a button appended somewhere else on the node.
  body.addEventListener("click", (e) => {
    if (!e.target.closest(".fpt-toggle")) return;
    root.classList.toggle("editing");
    if (root.classList.contains("editing")) area.focus();
    if (onLayout) onLayout();
  });

  const widget = node.addDOMWidget("fpt_panel", "fpt_panel", root, {
    serialize: false,
    getMinHeight: () => (root.classList.contains("collapsed") ? 26
                         : root.classList.contains("editing") ? 300 : 132),
  });

  return {
    widget,
    /** The editable filter, below the readout. `onEdit` receives the raw text. */
    editor(onEdit) {
      let pending;
      area.addEventListener("input", () => {
        clearTimeout(pending);
        pending = setTimeout(() => onEdit(area.value), 400);
      });
    },
    setFilterText(text) {
      if (document.activeElement !== area) area.value = text;
    },
    /** What the node is pointing at. */
    show(d) {
      const t = root.querySelector(".fpt-title");
      if (d && d.error) {
        t.innerHTML = esc(title);
        body.innerHTML = `<div class="fpt-err">${esc(d.error)}</div>`;
        return;
      }
      if (!d || !d.id) {
        t.innerHTML = esc(title);
        const near = (d && d.candidates) || [];
        body.innerHTML =
          `<div class="fpt-dim">${esc((d && d.why) || "nothing resolved yet")}</div>` +
          (near.length
            ? `<div class="fpt-sec">what is there</div>` + near.map((v) =>
                `<div class="fpt-row"><span class="fpt-v" style="flex:1">${esc(v.code)}</span>
                 ${v.status && v.status.label ? badge(v.status) : ""}</div>`).join("")
            : "") + filterBlock(d);
        return;
      }
      t.innerHTML = `${esc(d.code)} ${d.status && d.status.label ? badge(d.status) : ""}`;
      const rows = [];
      if (d.link) rows.push(["link", d.link]);
      if (d.task) rows.push(["task", d.task]);
      for (const f of d.facts || []) rows.push([f.label, f.value]);
      if ((d.generated_from || []).length) rows.push(["from", d.generated_from.join(", ")]);
      body.innerHTML =
        rows.map(([k, v]) => `<div class="fpt-row"><span class="fpt-k">${esc(k)}</span>
          <span class="fpt-v">${esc(v)}</span></div>`).join("") +
        (d.why ? `<div class="fpt-why">${esc(d.why)}</div>` : "") + filterBlock(d);
    },
    /** What the node last did. Appended under the description, not instead of it. */
    log(lines, ok = true) {
      const cls = ok ? "fpt-ok" : "fpt-err";
      body.insertAdjacentHTML("beforeend",
        `<div class="fpt-sec">last run</div>` +
        [].concat(lines).map((l) => `<div class="${cls}">${esc(l)}</div>`).join(""));
      root.classList.remove("collapsed");
    },
    clearLog() {
      body.querySelectorAll(".fpt-sec, .fpt-ok, .fpt-err").forEach((e) => e.remove());
    },
  };
}

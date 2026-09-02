// A small readout both nodes share: what the node is pointing at, and what it last did.
//
// A DOM widget rather than a read-only textarea, because the useful parts here are a status — which
// Flow PT already gives a colour (probe 010, bg_color is comma-separated RGB) — and a run log that
// wants to be distinguishable at a glance. Collapsible, because once a graph is set up this is
// reference material, not something to keep reading.

const CSS = `
.fpt-panel { font: 11px ui-monospace, SFMono-Regular, Menlo, monospace; color: #cfd3d8;
             background: #23262b; border: 1px solid #35393f; border-radius: 6px;
             overflow: hidden; display: flex; flex-direction: column; }
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
.fpt-sec { color: #7f868f; text-transform: uppercase; letter-spacing: .06em; font-size: 9px;
           border-top: 1px solid #35393f; padding-top: 5px; margin-top: 1px; }
.fpt-ok { color: #7fd18b; }
.fpt-err { color: #f08a8a; white-space: pre-wrap; }
.fpt-dim { color: #7f868f; }
.fpt-filter { color: #9aa7b8; background: #1d2024; border: 1px solid #313640; border-radius: 4px;
              padding: 4px 6px; white-space: pre-wrap; word-break: break-all; font-size: 10px; }
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
  return `<div class="fpt-sec">filter</div><div class="fpt-filter">${
    esc(JSON.stringify(d.filters))}</div>`;
}

const esc = (s) => String(s ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

export function addPanel(node, title = "Flow PT") {
  ensureCss();
  const root = document.createElement("div");
  root.className = "fpt-panel";
  root.innerHTML = `<div class="fpt-head">
      <svg class="fpt-caret" viewBox="0 0 10 10"><path d="M1 3l4 4 4-4" stroke="currentColor"
        fill="none" stroke-width="1.6"/></svg>
      <span class="fpt-title">${esc(title)}</span></div>
    <div class="fpt-body"></div>`;
  const head = root.querySelector(".fpt-head");
  const body = root.querySelector(".fpt-body");
  head.addEventListener("click", () => root.classList.toggle("collapsed"));

  const widget = node.addDOMWidget("fpt_panel", "fpt_panel", root, {
    serialize: false,
    getMinHeight: () => (root.classList.contains("collapsed") ? 26 : 132),
  });

  return {
    widget,
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

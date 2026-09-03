import { iconHtml } from "./fpt_dom_widgets.js";
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
/* The panel does not collapse. Folding it meant measuring the content mid-transition, which was the
   root of three separate sizing bugs; the box simply sizes to what it holds. */
.fpt-head { display: flex; align-items: center; gap: 6px; padding: 4px 8px;
            background: #2b2f35; border-bottom: 1px solid #35393f; user-select: none; }
.fpt-title { font-weight: 600; color: #e8ebee; overflow: hidden; text-overflow: ellipsis;
             flex: 1; min-width: 0; }
.fpt-lead { color: #7f868f; font-weight: 400; }
.fpt-icon { width: 11px; height: 11px; vertical-align: -1px; margin-right: 3px; }
.fpt-pill { padding: 1px 7px; border-radius: 9px; font-size: 10px; font-weight: 600;
            white-space: nowrap; }
/* A two-column grid, so every label gets exactly the width the LONGEST one needs and the values all
   line up. A fixed label width cannot work here: negative_prompt is ~100px at this size and a 62px
   box let it run underneath its own value. */
/* fit-content, not max-content: labels take the width they need but never more than 45% of the box,
   so a narrow node still leaves the values somewhere to go. max-content stayed at 146px whatever the
   node width, which on a 260px node was 61% of it. */
.fpt-body { padding: 6px 8px; display: grid; gap: 4px 8px; min-width: 0;
            grid-template-columns: fit-content(45%) minmax(0, 1fr); align-items: baseline; }
/* The row wrapper stays in the markup but hands its children to the grid. */
.fpt-row { display: contents; }
.fpt-body > .fpt-sec, .fpt-body > .fpt-why, .fpt-body > .fpt-filter,
.fpt-body > .fpt-dim, .fpt-body > .fpt-err, .fpt-body > .fpt-ok,
.fpt-body > .fpt-v:only-child { grid-column: 1 / -1; }
/* Wrap rather than nowrap: once the column is capped a long name has to fold, and folding loses
   nothing where truncating would. */
.fpt-k { color: #7f868f; overflow-wrap: anywhere; }
.fpt-v { color: #cfd3d8; overflow-wrap: anywhere; min-width: 0; }
.fpt-why { color: #7f868f; font-style: italic; }
.fpt-sec { color: #7f868f; text-transform: uppercase; letter-spacing: .06em; font-size: 9px;
           border-top: 1px solid #35393f; padding-top: 5px; margin-top: 1px; }
.fpt-ok { color: #7fd18b; }
.fpt-err { color: #f08a8a; white-space: pre-wrap; }
.fpt-dim { color: #7f868f; }
.fpt-gone { text-decoration: line-through; opacity: .5; }
.fpt-state { display: inline-flex; align-items: center; gap: 4px; margin-left: auto;
  font-size: 9px; text-transform: uppercase; letter-spacing: .04em; color: #8b939c; }
.fpt-state i { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.fpt-head { display: flex; align-items: center; }
.fpt-panel.is-loading { opacity: .72; }
`;

/* Three states, because "nothing showing" reads the same as "still asking". The panel already
   branched three ways internally — error, resolved nothing, resolved something — this only makes
   that visible, and adds the one it could not know: a request still in flight. */
const STATE = {
  loading: ["#8b939c", "loading"],
  ok:      ["#7fc98b", "valid"],
  warn:    ["#e0b155", "check this"],
};

let injected = false;
const PROVENANCE = {
  generated: "AI generated",
  derived: "derived from a Version, generator not recorded",
  unrecorded: "no generation record",
};

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
  // Same renderer as the chips, so a status looks the same wherever it is drawn (recipe 010).
  return iconHtml(status.icon, status.rgb) + pill(esc(status.label), status.rgb);
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

// What the run would record, so a publish is not a leap of faith. Fields the site does not have are
// shown struck through rather than hidden: knowing a value was computed and dropped is the point.
function writesBlock(d) {
  const f = d && d.fields;
  if (!f || !f.length) return "";
  // Everything, including what will be left empty and why. A field with no value is dimmed, not
  // hidden: an absent seed on a graph with no sampler is worth knowing before you publish.
  const row = (x) => {
    const dead = !x.present;
    const empty = !x.value;
    return `<div class="fpt-row"><span class="fpt-k${dead ? " fpt-gone" : ""}">${
      esc(x.name.replace(/^ai_/, ""))}</span><span class="fpt-v${
      dead ? " fpt-gone" : empty ? " fpt-dim" : ""}">${
      esc(x.value || x.note || "—")}</span></div>`;
  };
  return `<div class="fpt-sec">will write</div>` + f.map(row).join("") +
    ((d.uploads || []).length
      ? `<div class="fpt-sec">uploads</div>` + d.uploads.map((u) =>
          `<div class="fpt-row"><span class="fpt-v fpt-dim">${esc(u)}</span></div>`).join("") : "") +
    ((d.missing_fields || []).length
      ? `<div class="fpt-why">${d.missing_fields.length} provenance field(s) missing on this site` +
        ` — run: python -m comfyui_fpt.fields</div>` : "");
}

function sourcesBlock(d) {
  const s2 = d && d.sources;
  if (!s2 || !s2.length) return "";
  // The reason goes under the name, not beside it: side by side, a narrow node squeezed the code
  // into one character per line.
  return `<div class="fpt-sec">from</div>` + s2.map((x) =>
    `<div class="fpt-v">${esc(x.code || ("Version " + x.id))}</div>` +
    (x.why ? `<div class="fpt-why">${esc(x.why)}</div>` : "")).join("");
}

const esc = (s) => String(s ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

export function addPanel(node, title = "Flow PT", onLayout = null) {
  ensureCss();
  const root = document.createElement("div");
  root.className = "fpt-panel";
  root.innerHTML = `<div class="fpt-head"><span class="fpt-title">${esc(title)}</span>
      <span class="fpt-state"></span></div>
    <div class="fpt-body"></div>
`;
  const head = root.querySelector(".fpt-head");
  const stateEl = root.querySelector(".fpt-state");
  const setState = (kind) => {
    const [color, word] = STATE[kind] || STATE.warn;
    stateEl.innerHTML = `<i style="background:${color}"></i>${word}`;
    root.classList.toggle("is-loading", kind === "loading");
  };
  const body = root.querySelector(".fpt-body");
  // Kept outside the body so redrawing the readout cannot destroy it mid-edit.

  // Height follows the content. A fixed number was fine when the readout was three lines and wrong
  // as soon as it listed every field a publish writes — the box stayed small and the content scrolled
  // inside it, which no amount of widening the node could fix.
  const measure = () => {
    const head_h = head.getBoundingClientRect().height || 26;
    const body_h = body.scrollHeight || 0;
    // +16 covers the border and the rounding between layout and canvas pixels; at +8 the last row
    // was clipped by a few pixels.
    return Math.min(Math.max(head_h + body_h + 16, 60), 900);
  };
  const widget = node.addDOMWidget("fpt_panel", "fpt_panel", root, {
    serialize: false,
    getMinHeight: measure,
  });

  // Re-measure when the content changes, once the browser has laid it out.
  //
  // Two traps. `computedHeight` is only refreshed during the frontend's own layout pass, so resizing
  // before that pass sizes the node from the previous content. And a measurement taken while the
  // panel is still at its old size is wrong the other way: expanding measured 674px of content that
  // settles at 449, because every label wraps while the box is still 14px wide.
  //
  // So it re-measures until the number stops moving, and a ResizeObserver catches any late reflow
  // without a fixed delay to guess at.
  let applied = -1, passes = 0;
  const apply = () => {
    const h = measure();
    if (Math.abs(h - applied) < 2) return;      // converged; stop before this becomes a loop
    applied = h;
    widget.computedHeight = h;
    if (onLayout) onLayout();
    if (passes++ < 4) requestAnimationFrame(apply);
  };
  let settling;
  const relayout = () => {
    clearTimeout(settling);
    settling = setTimeout(() => { passes = 0; applied = -1; requestAnimationFrame(apply); }, 30);
  };
  try {
    new ResizeObserver(() => {
      if (Math.abs(measure() - applied) >= 2) relayout();
    }).observe(body);
  } catch (e) { /* no ResizeObserver: the explicit relayout calls still cover every fold */ }

  return {
    widget,
    /** The editable filter, below the readout. `onEdit` receives the raw text. */
    /** What the node is pointing at. */
    /** A request is in flight. Called before the await, so the readout below is visibly stale
     *  rather than silently stale. */
    loading() {
      setState("loading");
    },
    show(d) {
      const t = root.querySelector(".fpt-title");
      setState(d && d.error ? "warn" : (d && d.id) ? "ok" : "warn");
      if (d && d.error) {
        t.innerHTML = esc(title);
        body.innerHTML = `<div class="fpt-err">${esc(d.error)}</div>`;
        relayout();
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
            : "");
        relayout();
        return;
      }
      // Say what the name IS. On the publish node it is the Version about to be created, and an
      // unlabelled string in a header does not tell you that.
      t.innerHTML = `<span class="fpt-lead">Version Name:</span> ${esc(d.code)} ${
        d.status && d.status.label ? badge(d.status) : ""}`;
      const rows = [];
      if (d.link) rows.push(["link", d.link]);
      if (d.task) rows.push(["task", d.task]);
      // First, because it is the thing an artist wants to know before building on someone else's
      // Version. "unrecorded" never reads as "not AI" — it says only that this Version does not
      // carry a record of how it was made, which is all the data supports.
      if (PROVENANCE[d.provenance]) rows.push(["provenance", PROVENANCE[d.provenance]]);
      for (const f of d.facts || []) rows.push([f.label, f.value]);
      if ((d.generated_from || []).length) rows.push(["from", d.generated_from.join(", ")]);
      body.innerHTML =
        rows.map(([k, v]) => `<div class="fpt-row"><span class="fpt-k">${esc(k)}</span>
          <span class="fpt-v">${esc(v)}</span></div>`).join("") +
        (d.why ? `<div class="fpt-why">${esc(d.why)}</div>` : "") +
        sourcesBlock(d) + writesBlock(d);
      relayout();
    },
    /** What the node last did. Appended under the description, not instead of it. */
    log(lines, ok = true) {
      const cls = ok ? "fpt-ok" : "fpt-err";
      body.insertAdjacentHTML("beforeend",
        `<div class="fpt-sec">last run</div>` +
        [].concat(lines).map((l) => `<div class="${cls}">${esc(l)}</div>`).join(""));
      relayout();
    },
    clearLog() {
      body.querySelectorAll(".fpt-sec, .fpt-ok, .fpt-err").forEach((e) => e.remove());
    },
  };
}

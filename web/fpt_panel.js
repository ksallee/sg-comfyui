import { iconHtml, domRow, advancedWidget } from "./fpt_dom_widgets.js";
// A small readout both nodes share: what the node is pointing at, and what it last did.
//
// A DOM widget rather than a read-only textarea, because the useful parts here are a status — which
// Flow PT already gives a colour (probe 010, bg_color is comma-separated RGB) — and a run log that
// wants to be distinguishable at a glance.
//
// TWO rows, not one. The readout's job is to answer, before every Run, "which Version, and is this
// valid" — so the name, its status and the state pill are always on screen. Anything a widget three
// rows higher already says, and anything an operator reads while CONFIGURING rather than before a
// run, goes in the second row, which carries `options.advanced` and therefore lives inside
// ComfyUI's own "Show advanced inputs" fold. A <details> of ours would be a second fold beside the
// editor's, in the same node, remembering its own state — one fold per node is the whole point.

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
/* The name, its status and the state are three siblings here, so a narrow node wraps BETWEEN them.
   space-between rather than a margin on the last: when they wrap they line up under the name
   instead of hugging the far edge on a line of their own. */
.fpt-head { display: flex; align-items: center; gap: 6px; padding: 4px 8px; flex-wrap: wrap;
            justify-content: space-between;
            background: #2b2f35; border-bottom: 1px solid #35393f; user-select: none; }
/* Its own flex row, wrapping between the lead and the name: as one text run a long name broke
   "Version Name" across two lines and the label read as part of the answer. Flex 0 1 auto, never 1:
   a title that grows to the full width pushes the status and the state onto a line of their own
   even when both would have fitted beside it. */
.fpt-title { font-weight: 600; color: #e8ebee; flex: 0 1 auto; min-width: 0;
             display: flex; align-items: baseline; flex-wrap: wrap; gap: 2px 6px; }
.fpt-lead { color: #7f868f; font-weight: 400; white-space: nowrap; }
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
/* With everything but the name behind the fold the body is usually empty, and its padding read as a
   second, blank line under the answer. */
.fpt-body:empty { display: none; }
/* The row wrapper stays in the markup but hands its children to the grid. */
.fpt-row { display: contents; }
.fpt-body > .fpt-sec, .fpt-body > .fpt-why, .fpt-body > .fpt-filter,
.fpt-body > .fpt-dim, .fpt-body > .fpt-err, .fpt-body > .fpt-ok,
.fpt-body > .fpt-full, .fpt-body > .fpt-v:only-child { grid-column: 1 / -1; }
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
.fpt-code { font: 600 13px ui-monospace, SFMono-Regular, Menlo, monospace; color: #f2f5f8;
  letter-spacing: .01em; overflow-wrap: anywhere; min-width: 0; }
.fpt-badge { display: inline-flex; align-items: center; gap: 3px; }
.fpt-badge:empty { display: none; }
/* Status and state travel together, so a narrow node drops both to the next line rather than
   stranding "valid" under a pill that stayed up. */
.fpt-mark { display: inline-flex; align-items: center; gap: 6px; flex: none; }
/* .fpt-panel sets display:flex, which beats the UA rule for [hidden]. Said again so an empty fold
   is gone rather than an empty box. */
.fpt-panel[hidden] { display: none; }
.fpt-state { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap;
  font-size: 9px; text-transform: uppercase; letter-spacing: .04em; color: #8b939c; }
.fpt-state i { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
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
  // No fold of its own any more: the whole block already sits behind the editor's advanced fold, and
  // two nested folds meant two clicks to see a list the operator opened the fold to read.
  return `<div class="fpt-sec">metadata captured</div>` + f.map(row).join("") +
    ((d.uploads || []).length
      // fpt-full, not a .fpt-row with one child: `>` reads the DOM tree, so a lone .fpt-v inside a
      // display:contents row never matched the span rule and two filenames sat side by side across
      // the label and value columns.
      ? `<div class="fpt-sec">uploads</div>` + d.uploads.map((u) =>
          `<div class="fpt-full fpt-dim">${esc(u)}</div>`).join("") : "") +
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
    `<div class="fpt-full fpt-v">${esc(x.code || ("Version " + x.id))}</div>` +
    (x.why ? `<div class="fpt-why">${esc(x.why)}</div>` : "")).join("");
}

const esc = (s) => String(s ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

export function addPanel(node, title = "Flow PT", onLayout = null) {
  ensureCss();
  const root = document.createElement("div");
  root.className = "fpt-panel";
  root.innerHTML = `<div class="fpt-head"><span class="fpt-title">${esc(title)}</span>
      <span class="fpt-mark"><span class="fpt-badge"></span><span class="fpt-state"></span></span>
    </div>
    <div class="fpt-body"></div>
`;
  // The fine print. Same box, no head of its own — it is the continuation of the readout above, and
  // a second title would read as a second panel.
  const more = document.createElement("div");
  more.className = "fpt-panel fpt-more";
  more.innerHTML = `<div class="fpt-body"></div>`;
  const stateEl = root.querySelector(".fpt-state");
  const badgeEl = root.querySelector(".fpt-badge");
  // There is no LGraphBadge here any more. It was meant to mark a troubled node where the editor
  // already trains a person to look, and on Nodes 2.0 — the only canvas these nodes support — it
  // drew nothing: usePartitionedBadges reads the `badges` array captured when VueNodeData was
  // built, then renders it from index 1, so a badge pushed after the first resolve answered was in
  // node.badges and on no screen (frontend 1.51.9, measured). The state pill is the mechanism that
  // works.
  const setState = (kind) => {
    const [color, word] = STATE[kind] || STATE.warn;
    stateEl.innerHTML = `<i style="background:${color}"></i>${word}`;
    root.classList.toggle("is-loading", kind === "loading");
  };
  const body = root.querySelector(".fpt-body");
  const detail = more.querySelector(".fpt-body");

  // Both rows span the node's widget grid.
  //
  // No convergence loop any more. It existed because the panel had to guess its own height before
  // the frontend's layout pass — "expanding measured 674px of content that settles at 449, because
  // every label wraps while the box is still 14px wide". fitNode measures the node's rendered DOM
  // instead of predicting it, so one pass after the browser has laid out is the answer.
  const { widget, relayout: fit } = domRow(node, "fpt_panel", { control: root });
  advancedWidget(domRow(node, "fpt_panel_detail", { control: more }).widget);
  const relayout = () => { fit(); onLayout?.(); };
  try {
    // Both boxes: unfolding the advanced inputs changes the node's rendered height and nothing else
    // would tell fitNode to measure again.
    const ro = new ResizeObserver(relayout);
    ro.observe(body);
    ro.observe(detail);
  } catch (e) { /* no ResizeObserver: the explicit relayout calls still cover every redraw */ }

  return {
    widget,
    /** The editable filter, below the readout. `onEdit` receives the raw text. */
    /** What the node is pointing at. */
    /** A request is in flight. Called before the await, so the readout below is visibly stale
     *  rather than silently stale. */
    loading() {
      setState("loading");
    },
    /** `d.state` ("ok" | "warn" | "loading") overrides the guess, because a caller knows things the
     *  readout cannot: a provenance field mapped to a name this site does not have still resolves a
     *  Version, so `id` alone read as valid while the publish would silently drop a value.
     *
     *  `d.echo` is `[{label, value}]` the node's own widgets already answer. It goes in the fold
     *  with `link` and `task`, and `d.facts` — what only the site knows about this Version — does
     *  not. */
    show(d) {
      const t = root.querySelector(".fpt-title");
      setState((d && d.state) || (d && d.error ? "warn" : (d && d.id) ? "ok" : "warn"));
      // The head carries the whole answer, so it is rebuilt on every path, empty ones included.
      const plain = (rows) => rows.map(([k, v]) =>
        `<div class="fpt-row"><span class="fpt-k">${esc(k)}</span>
          <span class="fpt-v">${esc(v)}</span></div>`).join("");
      const fold = (html) => {
        detail.innerHTML = html;
        more.hidden = !html;   // an empty box inside the fold is worse than no row at all
      };
      if (d && d.error) {
        t.innerHTML = esc(title);
        badgeEl.innerHTML = "";
        body.innerHTML = `<div class="fpt-err">${esc(d.error)}</div>`;
        fold("");
        relayout();
        return;
      }
      if (!d || !d.id) {
        t.innerHTML = esc(title);
        badgeEl.innerHTML = "";
        const near = (d && d.candidates) || [];
        // Why nothing resolved, and what IS there, stay in front of the operator: that is the state
        // pill's explanation, not fine print.
        body.innerHTML =
          `<div class="fpt-dim">${esc((d && d.why) || "nothing resolved yet")}</div>` +
          (near.length
            ? `<div class="fpt-sec">what is there</div>` + near.map((v) =>
                `<div class="fpt-row"><span class="fpt-v" style="flex:1">${esc(v.code)}</span>
                 ${v.status && v.status.label ? badge(v.status) : ""}</div>`).join("")
            : "");
        fold("");
        relayout();
        return;
      }
      // Say what the name IS. On the publish node it is the Version about to be created, and an
      // unlabelled string in a header does not tell you that.
      // The name is the answer. It was the same size as its own label, which buried the one thing
      // worth checking before a run.
      t.innerHTML = `<span class="fpt-lead">Version Name</span>` +
        `<span class="fpt-code">${esc(d.code)}</span>`;
      badgeEl.innerHTML = d.status && d.status.label ? badge(d.status) : "";
      const rows = [];
      // What only the site knows about this Version. "unrecorded" never reads as "not AI" — it says
      // only that this Version does not carry a record of how it was made, which is all the data
      // supports.
      if (PROVENANCE[d.provenance]) rows.push(["provenance", PROVENANCE[d.provenance]]);
      for (const f of d.facts || []) rows.push([f.label, f.value]);
      if ((d.generated_from || []).length) rows.push(["from", d.generated_from.join(", ")]);
      body.innerHTML = plain(rows);
      // `link` and `task` are the node's own combos read back. So is everything in `d.echo`. `why`
      // is the reasoning behind a name the operator can already see, and the writes block is the
      // nine concepts that are the same every publish — all of it configuration-time reading.
      const echoed = [];
      if (d.link) echoed.push(["link", d.link]);
      if (d.task) echoed.push(["task", d.task]);
      for (const f of d.echo || []) echoed.push([f.label, f.value]);
      fold(plain(echoed) + (d.why ? `<div class="fpt-why">${esc(d.why)}</div>` : "") +
        sourcesBlock(d) + writesBlock(d));
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

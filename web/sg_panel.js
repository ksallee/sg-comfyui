/* The readout both nodes carry: which Version they are pointing at, and what the last run did.
 *
 * A DOM widget rather than a read-only textarea, because the useful parts are a status — which SG
 * gives a colour and an icon (probe 010) — and a run log that has to be readable at a glance.
 *
 * TWO rows. The name, its status and the state pill are always on screen, because the readout's job
 * is to answer "which Version, and is this valid" before every Run. Anything a widget three rows
 * higher already says, and anything read while CONFIGURING rather than before a run, goes in the
 * second row, which carries `options.advanced` and so lives inside ComfyUI's own "Show advanced
 * inputs" fold — one fold per node, the editor's own.
 */
import { iconHtml, domRow, advancedWidget, styleOnce, esc, rgbParts, rgbCss }
  from "./sg_dom_widgets.js";

const CSS = `
/* box-sizing and a full-width block: the DOM widget's container is sized by the node, and without
   these the panel keeps its content width and sits narrow inside it. */
.sg-panel { font: 11px ui-monospace, SFMono-Regular, Menlo, monospace; color: #cfd3d8;
             background: #23262b; border: 1px solid #35393f; border-radius: 6px;
             overflow: hidden; display: flex; flex-direction: column;
             box-sizing: border-box; width: 100%; height: 100%; }
.sg-panel * { box-sizing: border-box; }
/* The name, its status and the state are three siblings, so a narrow node wraps BETWEEN them.
   space-between rather than a margin on the last: wrapped, they line up under the name instead of
   hugging the far edge on a line of their own. */
.sg-head { display: flex; align-items: center; gap: 6px; padding: 4px 8px; flex-wrap: wrap;
            justify-content: space-between;
            background: #2b2f35; border-bottom: 1px solid #35393f; user-select: none; }
/* Its own flex row, wrapping between the lead and the name, so a long name does not break "Version
   Name" across two lines. Flex 0 1 auto, never 1: a title that grows to the full width pushes the
   status and the state onto a line of their own even when both would have fitted beside it. */
.sg-title { font-weight: 600; color: #e8ebee; flex: 0 1 auto; min-width: 0;
             display: flex; align-items: baseline; flex-wrap: wrap; gap: 2px 6px; }
.sg-lead { color: #7f868f; font-weight: 400; white-space: nowrap; }
.sg-icon { width: 11px; height: 11px; vertical-align: -1px; margin-right: 3px; }
.sg-pill { padding: 1px 7px; border-radius: 9px; font-size: 10px; font-weight: 600;
            white-space: nowrap; }
/* A two-column grid, so every label gets exactly the width the longest one needs and the values
   line up. fit-content, not max-content: a label never takes more than 45% of the box, so a narrow
   node still leaves the values somewhere to go. */
.sg-body { padding: 6px 8px; display: grid; gap: 4px 8px; min-width: 0;
            grid-template-columns: fit-content(45%) minmax(0, 1fr); align-items: baseline; }
/* With everything but the name behind the fold the body is usually empty, and its padding would
   read as a second, blank line under the answer. */
.sg-body:empty { display: none; }
/* The row wrapper stays in the markup but hands its children to the grid. */
.sg-row { display: contents; }
/* A candidate is one line: what it is called, then what state it is in. */
.sg-cand { display: flex; align-items: center; gap: 6px; min-width: 0; }
.sg-cand-st { display: inline-flex; align-items: center; gap: 4px; margin-left: auto;
  color: #b9c0c8; white-space: nowrap; }
.sg-body > .sg-sec, .sg-body > .sg-why, .sg-body > .sg-filter,
.sg-body > .sg-dim, .sg-body > .sg-err, .sg-body > .sg-ok, .sg-body > .sg-alert,
.sg-body > .sg-full, .sg-body > .sg-v:only-child { grid-column: 1 / -1; }
/* 10ch is the longest label the readout writes itself ("provenance"), and it is a floor rather than
   a width so a site's own field names still widen the column. The two boxes are two widgets and so
   two grids; the shared floor is what keeps them from sitting six characters apart. */
.sg-k { color: #7f868f; overflow-wrap: anywhere; min-width: 10ch; }
.sg-v { color: #cfd3d8; overflow-wrap: anywhere; min-width: 0; }
.sg-why { color: #7f868f; font-style: italic; }
/* A published Version and the files it wrote are the two things an operator opens next. */
.sg-a { color: #7fb2e5; text-decoration: none; cursor: pointer; overflow-wrap: anywhere; }
.sg-a:hover { text-decoration: underline; }
/* Not grey: this one says the name above it is not the name a Run would write. */
.sg-alert { color: #e0b155; }
.sg-sec { color: #7f868f; text-transform: uppercase; letter-spacing: .06em; font-size: 9px;
           border-top: 1px solid #35393f; padding-top: 5px; margin-top: 1px; }
.sg-ok { color: #7fd18b; }
.sg-err { color: #f08a8a; white-space: pre-wrap; }
.sg-dim { color: #7f868f; }
.sg-code { font: 600 13px ui-monospace, SFMono-Regular, Menlo, monospace; color: #f2f5f8;
  letter-spacing: .01em; overflow-wrap: anywhere; min-width: 0; }
.sg-badge { display: inline-flex; align-items: center; gap: 3px; }
.sg-badge:empty { display: none; }
/* Status and state travel together, so a narrow node drops both to the next line rather than
   stranding "valid" under a pill that stayed up. */
.sg-mark { display: inline-flex; align-items: center; gap: 6px; flex: none; }
/* .sg-panel sets display:flex, which beats the UA rule for [hidden]. */
.sg-panel[hidden] { display: none; }
.sg-state { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap;
  font-size: 9px; text-transform: uppercase; letter-spacing: .04em; color: #8b939c; }
.sg-state i { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.sg-panel.is-loading { opacity: .72; }
`;

/* Three states, because "nothing showing" reads the same as "still asking". */
const STATE = {
  loading: ["#8b939c", "loading"],
  ok:      ["#7fc98b", "valid"],
  warn:    ["#e0b155", "check this"],
};

const PROVENANCE = {
  generated: "AI generated",
  derived: "derived from a Version, generator not recorded",
  unrecorded: "no generation record",
};

/** A destination this panel will link to. Everything else is drawn as plain text, so a path or a
 *  URL that came off the site cannot carry a `javascript:` scheme into an href. */
const linkable = (u) => /^(?:https?|file):/i.test(String(u ?? "").replace(/[\t\n\r]/g, "").trim());

/** A status the way SG draws it: its icon, then its label on its own colour (recipe 010). */
const badge = (status) => iconHtml(status.icon, status.rgb) + pill(esc(status.label), status.rgb);

/** One coloured pill. `label` is already escaped; the text colour is picked for readability against
 *  the site's own background colour rather than fixed. */
function pill(label, rgb) {
  const parts = rgbParts(rgb);
  const fg = parts && (0.299 * parts[0] + 0.587 * parts[1] + 0.114 * parts[2]) > 150
    ? "#1b1d21" : "#e8ebee";
  return `<span class="sg-pill" style="background:${rgbCss(rgb, "#3a4048")};color:${fg}">` +
    `${label}</span>`;
}

/** What the run would record, field by field. A field with no value is dimmed rather than dropped:
 *  an absent seed on a graph with no sampler is worth knowing before you publish. Where a value
 *  lands is said beside it, because a fact in the description is not a fact in a field. */
function writesBlock(d) {
  const f = d && d.fields;
  if (!f || !f.length) return "";
  const row = (x) => {
    const empty = !x.value;
    const where = x.into_description && !empty
      ? ` <span class="sg-dim">into the description</span>` : "";
    return `<div class="sg-row"><span class="sg-k">${
      esc(x.name.replace(/^ai_/, ""))}</span><span class="sg-v${empty ? " sg-dim" : ""}">${
      esc(x.value || x.note || "—")}${where}</span></div>`;
  };
  // sg-full, not a .sg-row with one child: the grid rule reads the DOM tree, so a lone .sg-v
  // inside a display:contents row does not match it and two filenames sit side by side.
  const list = (head, items) => ((items || []).length
    ? `<div class="sg-sec">${head}</div>` + items.map((u) =>
        `<div class="sg-full sg-dim">${esc(u)}</div>`).join("") : "");
  // The heading names what the rows ARE: this panel says what a Run WOULD do, never what was done.
  return `<div class="sg-sec">fields that will populate</div>` + f.map(row).join("") +
    list("uploads", d.uploads) +
    // Copies onto a shared volume are not uploads, and are the ones worth reading twice.
    list("copied to", d.writes);
}

/** The Versions this publish would say it came from. The reason goes under the name, not beside it:
 *  side by side, a narrow node squeezes the code into one character per line. */
function sourcesBlock(d) {
  const rows = d && d.sources;
  if (!rows || !rows.length) return "";
  return `<div class="sg-sec">from</div>` + rows.map((x) =>
    `<div class="sg-full sg-v">${esc(x.code || ("Version " + x.id))}</div>` +
    (x.why ? `<div class="sg-why">${esc(x.why)}</div>` : "")).join("");
}

/** Add the readout to a node. `onLayout` runs after every redraw that changes the node's height. */
export function addPanel(node, title = "SG", onLayout = null) {
  styleOnce("sg-panel", CSS);
  const root = document.createElement("div");
  root.className = "sg-panel";
  root.innerHTML = `<div class="sg-head"><span class="sg-title">${esc(title)}</span>
      <span class="sg-mark"><span class="sg-badge"></span><span class="sg-state"></span></span>
    </div>
    <div class="sg-body"></div>
`;
  // The fine print. Same box, no head of its own — it is the continuation of the readout above, and
  // a second title would read as a second panel.
  const more = document.createElement("div");
  more.className = "sg-panel sg-more";
  more.innerHTML = `<div class="sg-body"></div>`;
  const stateEl = root.querySelector(".sg-state");
  const badgeEl = root.querySelector(".sg-badge");
  // The state pill is the only mechanism that works here: an LGraphBadge is read off the `badges`
  // array captured when VueNodeData was built and rendered from index 1, so a badge pushed after
  // the first resolve is in node.badges and on no screen (frontend 1.51.9).
  const setState = (kind) => {
    const [color, word] = STATE[kind] || STATE.warn;
    stateEl.innerHTML = `<i style="background:${color}"></i>${word}`;
    root.classList.toggle("is-loading", kind === "loading");
  };
  const body = root.querySelector(".sg-body");
  const detail = more.querySelector(".sg-body");
  // What the last run did, kept rather than drawn once: every redraw of the readout rewrites the
  // body, and a run's Version id and file paths are the one thing on this panel that is nowhere
  // else. It goes when the next Run starts, or when a widget on the node changes.
  let lastRun = null;
  const drawLog = () => {
    if (!lastRun) return;
    const cls = lastRun.ok ? "sg-ok" : "sg-err";
    body.insertAdjacentHTML("beforeend",
      `<div class="sg-sec">last run</div>` +
      lastRun.lines.map((l) => `<div class="${cls}">${esc(l)}</div>`).join(""));
  };
  /** Replace the readout, keeping the run log under it. */
  const setBody = (html) => { body.innerHTML = html; drawLog(); };

  // Both rows span the node's widget grid. fitNode measures the node's rendered DOM, so one pass
  // after the browser has laid out is the answer and nothing predicts a height.
  const { widget, relayout: fit } = domRow(node, "sg_panel", { control: root });
  advancedWidget(domRow(node, "sg_panel_detail", { control: more }).widget);
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
    /** A request is in flight. Called before the await, so the readout is visibly stale rather than
     *  silently stale. */
    loading() {
      setState("loading");
    },
    /** Draw one answer.
     *
     *  `d.state` ("ok" | "warn" | "loading") overrides the guess made from `d.error` and `d.id`,
     *  because a caller knows things the readout cannot: a provenance field mapped to a name this
     *  site does not have still resolves a Version. `d.facts` is what only the site knows about
     *  this Version; nothing the node's own widgets already answer belongs in it. */
    show(d) {
      const t = root.querySelector(".sg-title");
      setState((d && d.state) || (d && d.error ? "warn" : (d && d.id) ? "ok" : "warn"));
      const plain = (rows) => rows.map(([k, v, href]) =>
        `<div class="sg-row"><span class="sg-k">${esc(k)}</span>
          <span class="sg-v">${linkable(href)
            ? `<a class="sg-a" href="${esc(href)}" target="_blank" rel="noreferrer">${esc(v)}</a>`
            : esc(v)}</span></div>`).join("");
      const fold = (html) => {
        detail.innerHTML = html;
        more.hidden = !html;   // an empty box inside the fold is worse than no row at all
      };
      // The head carries the whole answer, so it is rebuilt on every path, empty ones included.
      if (d && d.error) {
        t.innerHTML = esc(title);
        badgeEl.innerHTML = "";
        setBody(`<div class="sg-err">${esc(d.error)}</div>`);
        fold("");
        relayout();
        return;
      }
      if (!d || !d.id) {
        t.innerHTML = esc(title);
        badgeEl.innerHTML = "";
        const near = (d && d.candidates) || [];
        // Why nothing resolved, and what IS there, stay in front of the operator: that is the state
        // pill's explanation, not fine print. One full-width row per candidate, name then status —
        // the icon identifies the status (recipe 010) and a column of coloured pills would compete
        // with the names, which are what is being read.
        setBody(
          `<div class="sg-dim">${esc((d && d.why) || "No Version matches these fields yet.")}</div>` +
          (near.length
            ? `<div class="sg-sec">versions on this link</div>` + near.map((v) =>
                `<div class="sg-full sg-cand">${esc(v.code)}` +
                (v.status && v.status.label
                  ? `<span class="sg-cand-st">${iconHtml(v.status.icon, v.status.rgb)}` +
                    `${esc(v.status.label)}</span>` : "") + `</div>`).join("")
            : ""));
        fold("");
        relayout();
        return;
      }
      // Say what the name IS, and say it larger than its own label: on the publish node it is the
      // Version about to be created, and it is the one thing worth checking before a run.
      t.innerHTML = `<span class="sg-lead">Version Name</span>` +
        `<span class="sg-code">${esc(d.code)}</span>`;
      badgeEl.innerHTML = d.status && d.status.label ? badge(d.status) : "";
      const rows = [];
      let over = "";
      // "unrecorded" never reads as "not AI": it says only that this Version carries no record of
      // how it was made, which is all the data supports.
      if (PROVENANCE[d.provenance]) rows.push(["provenance", PROVENANCE[d.provenance]]);
      // What each output will take, and what it claims to be. `source` is a combo holding a key, so
      // the type, the filename and the frame count exist only here, and a colour space is what an
      // artist about to comp must see before the pixels reach a node that assumes sRGB.
      if (d.image_label) rows.push(["image", d.image_label]);
      if (d.video_label) rows.push(["video", d.video_label]);
      // What the file this will read IS, in the site's own words: bit depth, channels and size are
      // what decide whether these pixels reach a comp untouched.
      if (typeof d.format === "string" && d.format) rows.push(["format", d.format]);
      // The frame numbers this source has: `frame` is a number in a filename, and 0 means "wherever
      // the sequence starts", so the range belongs beside the widgets that ask for it.
      if (d.frames) {
        // `?? 0`, not `|| 0`: 0 is the value that means "all of them", and it is also the
        // declared default, so an absent widget and an explicit 0 have to read the same.
        const f = d.frames, ask = Number(d.frame_ask || 0), n = Number(d.count_ask ?? 0);
        const span = f.first === f.last ? `${f.first}` : `${f.first}-${f.last}`;
        let note = `${span}, ${f.count} frame${f.count === 1 ? "" : "s"}.`;
        if (ask && (ask < f.first || ask > f.last)) {
          note += ` Frame ${ask} is not in the sequence. Pick one between ${f.first} and ${f.last}.`;
        } else {
          const at = ask || f.first;
          const got = n <= 0 ? f.last - at + 1 : Math.min(n, f.last - at + 1);
          note += got === 1 ? ` Reads frame ${at}.` : ` Reads ${got} frames from ${at}.`;
          // Said before the Run, not after it: one batch is a single tensor, and a plate too big
          // to hold is a refusal the operator can avoid by setting frame_count or raising the
          // budget. The same numbers the run would use.
          if (d.batch && got > d.batch.fits) {
            over = `Set frame_count to ${d.batch.fits} or less, or raise batch_budget_gib in `
              + `profile.local.json above ${d.batch.gib} GiB. `
              + `${got} frames of ${d.batch.width}×${d.batch.height} do not fit in one batch.`;
          }
        }
        rows.push(["frames", note]);
      }
      if (d.colour_space) rows.push(
        ["colour space", `${d.colour_space}. Declared on the file, not converted.`]);
      for (const f of d.facts || []) rows.push([f.label, f.value, f.href]);
      if ((d.generated_from || []).length) rows.push(["from", d.generated_from.join(", ")]);
      // The one line that never folds: what is wrong with the name directly above it. A notice
      // about how this Version was resolved is not that line, and never takes its place — a pinned
      // id and a batch too big to read are both true at once, and only one of them needs acting on.
      const alert = over || d.alert || "";
      const notice = over ? (d.alert || "") : "";
      if (over) setState("warn");
      setBody((alert ? `<div class="sg-alert">${esc(alert)}</div>` : "") +
        (notice ? `<div class="sg-dim">${esc(notice)}</div>` : "") + plain(rows));
      // The fold takes the reasoning behind a name the operator can already see, and the concepts
      // that are the same every publish: configuration-time reading, not pre-Run reading.
      fold((d.why ? `<div class="sg-why">${esc(d.why)}</div>` : "") +
        sourcesBlock(d) + writesBlock(d));
      relayout();
    },
    /** What the node last did. Appended under the readout, and kept there through every later
     *  redraw until `clearLog`. */
    log(lines, ok = true) {
      lastRun = { lines: [].concat(lines), ok };
      drawLog();
      relayout();
    },
    clearLog() {
      lastRun = null;
      body.querySelectorAll(".sg-sec, .sg-ok, .sg-err").forEach((e) => e.remove());
    },
  };
}

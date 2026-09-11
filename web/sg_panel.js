/* The readout on both nodes. Names the Version the node points at, and what the last run did.
 *
 * A DOM widget, not a read-only textarea. SG gives a status a colour and an icon (probe 010), and
 * the run log is scanned.
 *
 * Two rows. Row one has the name, its status and the state pill, and is on screen before every Run.
 * Row two sets `options.advanced`, so ComfyUI's own "Show advanced inputs" fold contains it. Row two
 * has what a widget above the readout already states, and what is read while configuring the node
 * rather than before a run.
 */
import { iconHtml, domRow, advancedWidget, styleOnce, esc, rgbParts, rgbCss }
  from "./sg_dom_widgets.js";

const CSS = `
/* The node sizes the DOM widget's container. Without box-sizing and the full width, the panel is
   drawn at its content width inside that container. */
.sg-panel { font: 11px ui-monospace, SFMono-Regular, Menlo, monospace; color: #cfd3d8;
             background: #23262b; border: 1px solid #35393f; border-radius: 6px;
             overflow: hidden; display: flex; flex-direction: column;
             box-sizing: border-box; width: 100%; height: 100%; }
.sg-panel * { box-sizing: border-box; }
/* The name, its status and the state are three siblings, so a narrow node wraps between them.
   space-between, not a margin on the last child. Wrapped, they align under the name rather than at
   the far edge of a line of their own. */
.sg-head { display: flex; align-items: center; gap: 6px; padding: 4px 8px; flex-wrap: wrap;
            justify-content: space-between;
            background: #2b2f35; border-bottom: 1px solid #35393f; user-select: none; }
/* Its own flex row. It wraps between the lead and the name, so a long name does not break "Version
   Name" across two lines. flex is 0 1 auto, not 1: a title grown to the container width pushes the
   status and the state onto a line of their own even when both would have fitted beside it. */
.sg-title { font-weight: 600; color: #e8ebee; flex: 0 1 auto; min-width: 0;
             display: flex; align-items: baseline; flex-wrap: wrap; gap: 2px 6px; }
.sg-lead { color: #7f868f; font-weight: 400; white-space: nowrap; }
.sg-icon { width: 11px; height: 11px; vertical-align: -1px; margin-right: 3px; }
.sg-pill { padding: 1px 7px; border-radius: 9px; font-size: 10px; font-weight: 600;
            white-space: nowrap; }
/* A two-column grid. The label column takes the width of the longest label, so the values align.
   fit-content, not max-content: a label takes at most 45% of the box, which leaves room for the
   values on a narrow node. */
.sg-body { padding: 6px 8px; display: grid; gap: 4px 8px; min-width: 0;
            grid-template-columns: fit-content(45%) minmax(0, 1fr); align-items: baseline; }
/* With everything but the name behind the fold the body is often empty. An empty body still draws
   its padding, which reads as a blank line under the answer. */
.sg-body:empty { display: none; }
/* display:contents keeps the row wrapper in the markup and puts its children on the grid. */
.sg-row { display: contents; }
/* A candidate is one line: its name, then its status. */
.sg-cand { display: flex; align-items: center; gap: 6px; min-width: 0; }
.sg-cand-st { display: inline-flex; align-items: center; gap: 4px; margin-left: auto;
  color: #b9c0c8; white-space: nowrap; }
.sg-body > .sg-sec, .sg-body > .sg-why, .sg-body > .sg-filter,
.sg-body > .sg-dim, .sg-body > .sg-err, .sg-body > .sg-ok, .sg-body > .sg-alert,
.sg-body > .sg-full, .sg-body > .sg-v:only-child,
.sg-run > .sg-sec, .sg-run > .sg-dim, .sg-run > .sg-err, .sg-run > .sg-ok, .sg-run > .sg-full
  { grid-column: 1 / -1; }
/* The run block is one removable DOM node and no box in the grid, so its rows use the same two
   columns as the readout above them. */
.sg-run { display: contents; }
/* "provenance" is the longest label the readout writes itself, at 10ch. min-width, not width, so a
   site's own field names widen the column. The two boxes are two widgets and so two grids. The
   shared minimum aligns their label columns. */
.sg-k { color: #7f868f; overflow-wrap: anywhere; min-width: 10ch; }
.sg-v { color: #cfd3d8; overflow-wrap: anywhere; min-width: 0; }
.sg-why { color: #7f868f; font-style: italic; }
/* Links: a published Version, and the files it wrote. */
.sg-a { color: #7fb2e5; text-decoration: none; cursor: pointer; overflow-wrap: anywhere; }
.sg-a:hover { text-decoration: underline; }
/* Amber, not grey. This line states that the name above it is not the name a Run would write. */
.sg-alert { color: #e0b155; }
.sg-sec { color: #7f868f; text-transform: uppercase; letter-spacing: .06em; font-size: 9px;
           border-top: 1px solid #35393f; padding-top: 5px; margin-top: 1px; }
.sg-ok { color: #7fd18b; }
.sg-err { color: #f08a8a; white-space: pre-wrap; }
.sg-dim { color: #7f868f; }
/* The head is not selectable, so the node drags from it. The name is: it is read off to be typed
   elsewhere, and a click copies it. */
.sg-code { font: 600 13px ui-monospace, SFMono-Regular, Menlo, monospace; color: #f2f5f8;
  letter-spacing: .01em; overflow-wrap: anywhere; min-width: 0; user-select: text; cursor: copy; }
.sg-code.is-copied { color: #7fd18b; }
.sg-badge { display: inline-flex; align-items: center; gap: 3px; }
.sg-badge:empty { display: none; }
/* One flex item for the status and the state, so a narrow node moves both to the next line
   together. */
.sg-mark { display: inline-flex; align-items: center; gap: 6px; flex: none; }
/* .sg-panel sets display:flex, which overrides the user agent rule for [hidden]. */
.sg-panel[hidden] { display: none; }
.sg-state { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap;
  font-size: 9px; text-transform: uppercase; letter-spacing: .04em; color: #8b939c; }
.sg-state i { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.sg-panel.is-loading { opacity: .72; }
`;

/* Three states. An empty readout and a request still in flight would otherwise look the same. */
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

/** Bytes as GiB to three significant digits, the format the node's own refusal prints. A value
 *  under a tenth of a GiB keeps its digits. */
const gib = (bytes) => String(Number((bytes / 2 ** 30).toPrecision(3)));

/** The refusal the run would raise, drawn before the Run. States what to set, then why. A batch is
 *  one float32 RGB tensor, so N frames of W×H need N·W·H·12 bytes to build. */
const budgetSentence = (b, frames) =>
  `Set frame_count to ${b.fits} or less at this resolution. ${frames} frames of `
  + `${b.width}×${b.height} would need ${gib(frames * b.width * b.height * 12)} GiB as one batch. `
  + `The limit is ${b.gib} GiB, batch_budget_gib in profile.local.json.`;

/** True for a destination this panel links to. Anything else is drawn as plain text, so a path or a
 *  URL from the site cannot put a `javascript:` scheme into an href. */
const linkable = (u) => /^(?:https?|file):/i.test(String(u ?? "").replace(/[\t\n\r]/g, "").trim());

/** A status the way SG draws it: its icon, then its label on its own colour (recipe 010). */
const badge = (status) => iconHtml(status.icon, status.rgb) + pill(esc(status.label), status.rgb);

/** One coloured pill. `label` is already escaped. The text colour is picked for contrast against
 *  the site's own background colour. */
function pill(label, rgb) {
  const parts = rgbParts(rgb);
  const fg = parts && (0.299 * parts[0] + 0.587 * parts[1] + 0.114 * parts[2]) > 150
    ? "#1b1d21" : "#e8ebee";
  return `<span class="sg-pill" style="background:${rgbCss(rgb, "#3a4048")};color:${fg}">` +
    `${label}</span>`;
}

/** Label and value rows on the panel's grid. A value with a linkable href is drawn as a link. */
const rowsHtml = (rows) => rows.map(([k, v, href]) =>
  `<div class="sg-row"><span class="sg-k">${esc(k)}</span>` +
  `<span class="sg-v">${linkable(href)
    ? `<a class="sg-a" href="${esc(href)}" target="_blank" rel="noreferrer">${esc(v)}</a>`
    : esc(v)}</span></div>`).join("");

/** What the run would record, field by field. A field with no value is dimmed, not dropped: an
 *  absent seed on a graph with no sampler is worth knowing before a publish. The destination of a
 *  value is named beside it. A fact in the description is not a fact in a field. */
function writesBlock(d) {
  const f = d && d.fields;
  if (!f || !f.length) return "";
  const row = (x) => {
    const empty = !x.value;
    // A note replaces an empty value, and is drawn beside a value it adds to: the destination of
    // the fact, or the part of it the Run decides.
    const where = empty ? ""
      : x.into_description ? ` <span class="sg-dim">into the description</span>`
      : x.note ? ` <span class="sg-dim">${esc(x.note)}</span>` : "";
    return `<div class="sg-row"><span class="sg-k">${
      esc(x.name.replace(/^ai_/, ""))}</span><span class="sg-v${empty ? " sg-dim" : ""}">${
      esc(x.value || x.note || "-")}${where}</span></div>`;
  };
  // sg-full, not a .sg-row with one child. The grid rule matches on the DOM tree, so a lone .sg-v
  // inside a display:contents row does not match it and two filenames share one line.
  const list = (head, items) => ((items || []).length
    ? `<div class="sg-sec">${head}</div>` + items.map((u) =>
        `<div class="sg-full sg-dim">${esc(u)}</div>`).join("") : "");
  // The heading names the rows. This panel states what a Run would do, not what a run did.
  return `<div class="sg-sec">fields that will populate</div>` + f.map(row).join("") +
    list("uploads", d.uploads);
}

/** The Versions this publish records as its sources. The reason is drawn under the name, not beside
 *  it: side by side, a narrow node wraps the code to one character per line. */
function sourcesBlock(d) {
  const rows = d && d.sources;
  if (!rows || !rows.length) return "";
  return `<div class="sg-sec">from</div>` + rows.map((x) =>
    `<div class="sg-full sg-v">${esc(x.code || ("Version " + x.id))}</div>` +
    (x.why ? `<div class="sg-why">${esc(x.why)}</div>` : "")).join("");
}

/** A click on `el` copies `text`. The canvas is not told about the press, so the node does not
 *  start dragging under a selection or a click. */
function copyOnClick(el, text) {
  if (!el) return;
  el.addEventListener("pointerdown", (e) => e.stopPropagation());
  el.addEventListener("click", async (e) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(text);
      el.classList.add("is-copied");
      setTimeout(() => el.classList.remove("is-copied"), 600);
    } catch (err) { /* no clipboard permission: the text is still selectable */ }
  });
}

/** Add the readout to a node. `onLayout` runs after a redraw that changes the node's height. */
export function addPanel(node, title = "SG", onLayout = null) {
  styleOnce("sg-panel", CSS);
  const root = document.createElement("div");
  root.className = "sg-panel";
  root.innerHTML = `<div class="sg-head"><span class="sg-title">${esc(title)}</span>
      <span class="sg-mark"><span class="sg-badge"></span><span class="sg-state"></span></span>
    </div>
    <div class="sg-body"></div>
`;
  // The fine print. The same box with no head of its own, as the continuation of the readout above
  // it. A second title would read as a second panel.
  const more = document.createElement("div");
  more.className = "sg-panel sg-more";
  more.innerHTML = `<div class="sg-body"></div>`;
  const stateEl = root.querySelector(".sg-state");
  const badgeEl = root.querySelector(".sg-badge");
  // A DOM state pill, not an LGraphBadge. The frontend reads an LGraphBadge off the `badges` array
  // captured when VueNodeData was built and renders from index 1, so a badge pushed after the first
  // resolve is in node.badges and is drawn on no screen (frontend 1.51.9).
  const setState = (kind) => {
    const [color, word] = STATE[kind] || STATE.warn;
    stateEl.innerHTML = `<i style="background:${color}"></i>${word}`;
    root.classList.toggle("is-loading", kind === "loading");
  };
  const body = root.querySelector(".sg-body");
  const detail = more.querySelector(".sg-body");
  // What the last run did, kept rather than drawn once. A redraw of the readout rewrites the body,
  // and a run's Version id and file paths are recorded nowhere else on this panel. It is cleared
  // when the next Run starts, or when a widget on the node changes.
  let lastRun = null;
  // One block, so drawing it again replaces it rather than adding a second copy of the same run.
  // A run that went through is drawn as rows, on the same grid as the readout above it. A line that
  // needs attention follows, dimmed. A refusal is the sentence in red.
  const drawLog = () => {
    body.querySelectorAll(".sg-run").forEach((e) => e.remove());
    if (!lastRun) return;
    const cls = lastRun.ok ? "sg-ok" : "sg-err";
    body.insertAdjacentHTML("beforeend",
      `<div class="sg-run"><div class="sg-sec">last run</div>` +
      rowsHtml(lastRun.rows || []) +
      (lastRun.notes || []).map((l) => `<div class="sg-full sg-dim">${esc(l)}</div>`).join("") +
      (lastRun.lines || []).map((l) => `<div class="${cls}">${esc(l)}</div>`).join("") + `</div>`);
  };
  /** Replace the readout, keeping the run log under it. */
  const setBody = (html) => { body.innerHTML = html; drawLog(); };

  // Both rows span the node's widget grid. fitNode measures the node's rendered DOM after the
  // browser has laid out, so no height is predicted.
  const { widget, relayout: fit } = domRow(node, "sg_panel", { control: root });
  advancedWidget(domRow(node, "sg_panel_detail", { control: more }).widget);
  const relayout = () => { fit(); onLayout?.(); };
  try {
    // Both boxes. Unfolding the advanced inputs changes the node's rendered height, and no other
    // event calls fitNode again.
    const ro = new ResizeObserver(relayout);
    ro.observe(body);
    ro.observe(detail);
  } catch (e) { /* no ResizeObserver: the explicit relayout calls cover each redraw */ }

  return {
    widget,
    /** Mark the readout as waiting on a request. Called before the await, so a stale readout is
     *  visible as stale. */
    loading() {
      setState("loading");
    },
    /** Draw one answer.
     *
     *  `d.state` ("ok" | "warn" | "loading") overrides the state derived from `d.error` and `d.id`.
     *  A provenance field mapped to a name this site does not have still resolves a Version, and
     *  the caller knows that. `d.facts` is what the site records about this Version. A fact a
     *  widget on the node already states does not belong in it. */
    show(d) {
      const t = root.querySelector(".sg-title");
      setState((d && d.state) || (d && d.error ? "warn" : (d && d.id) ? "ok" : "warn"));
      const fold = (html) => {
        detail.innerHTML = html;
        more.hidden = !html;   // an empty box inside the fold draws a blank row
      };
      // The head has the answer, so it is rebuilt on each path, the empty ones included.
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
        // The reason nothing resolved, and the Versions that do exist, are drawn outside the fold.
        // They explain the state pill. One full-width row per candidate, name then status. The icon
        // identifies the status (recipe 010). A column of coloured pills would compete with the
        // names, which are what is read.
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
      // The name is drawn larger than its own label. On the publish node it is the Version the Run
      // would create, and it is what is checked before a run.
      t.innerHTML = `<span class="sg-lead">Version Name</span>` +
        `<span class="sg-code" title="Click to copy">${esc(d.code)}</span>`;
      copyOnClick(t.querySelector(".sg-code"), d.code);
      badgeEl.innerHTML = d.status && d.status.label ? badge(d.status) : "";
      const rows = [];
      let over = "";
      // "unrecorded" states that this Version has no record of how it was made. It does not state
      // that the Version is not AI generated.
      if (PROVENANCE[d.provenance]) rows.push(["provenance", PROVENANCE[d.provenance]]);
      // What each output takes, and what it declares itself to be. `source` is a combo of one key,
      // so the type, the filename and the frame count are recorded here alone. A colour space is
      // read by an artist about to comp, before the pixels reach a node that assumes sRGB.
      // The file this reads, first and directly under the name. Bit depth, channels and size decide
      // whether these pixels reach a comp untouched.
      if (typeof d.format === "string" && d.format) rows.push(["format", d.format]);
      if (d.image_label) rows.push(["image", d.image_label]);
      if (d.video_label) rows.push(["video", d.video_label]);
      // The frame numbers this source has. `frame` is a number in a filename, and 0 means the first
      // frame of the sequence, so the range is drawn beside the widgets that ask for it.
      if (d.frames) {
        // `?? 0`, not `|| 0`. 0 means all of them and is also the declared default, so an absent
        // widget and an explicit 0 read the same.
        const f = d.frames, ask = Number(d.frame_ask || 0), n = Number(d.count_ask ?? 0);
        // A movie reports a count and no numbering. A sequence reports both. The arithmetic is the
        // same for each, and so is the batch the frames have to fit in.
        const first = Number(f.first ?? 1);
        const count = Number(f.count ?? 0);
        const last = Number(f.last ?? first + Math.max(count, 1) - 1);
        const span = first === last ? `${first}` : `${first}-${last}`;
        let note = `${span}, ${count} frame${count === 1 ? "" : "s"}.`;
        let got = 0;
        if (ask && (ask < first || ask > last)) {
          note += ` Frame ${ask} is not in the sequence. Pick one between ${first} and ${last}.`;
        } else {
          const at = ask || first;
          got = n <= 0 ? last - at + 1 : Math.min(n, last - at + 1);
          note += got === 1 ? ` Reads frame ${at}.` : ` Reads ${got} frames from ${at}.`;
        }
        // Drawn before the Run, not after it. One batch is a single tensor. A plate over the budget
        // is a refusal the operator avoids by setting frame_count or raising the budget. These are
        // the numbers the run would use, for frames read from a movie or from a sequence.
        if (d.batch && got > d.batch.fits) over = budgetSentence(d.batch, got);
        rows.push(["frames", note]);
      }
      if (d.colour_space) rows.push(
        ["colour space", `${d.colour_space}. Declared on the file, not converted.`]);
      for (const f of d.facts || []) rows.push([f.label, f.value, f.href]);
      if ((d.generated_from || []).length) rows.push(["from", d.generated_from.join(", ")]);
      // The line outside the fold states what is wrong with the name directly above it. A notice
      // about how this Version was resolved is drawn under that line, not in place of it. A pinned
      // id and a batch over the budget can both apply to one readout, and one of them needs acting
      // on.
      const alert = over || d.alert || "";
      const notice = over ? (d.alert || "") : "";
      if (over) setState("warn");
      setBody((alert ? `<div class="sg-alert">${esc(alert)}</div>` : "") +
        (notice ? `<div class="sg-dim">${esc(notice)}</div>` : "") + rowsHtml(rows));
      // The fold has the reasoning behind a name the operator can already see, and what is the same
      // for each publish. It is read while configuring the node, not before a Run.
      fold((d.why ? `<div class="sg-why">${esc(d.why)}</div>` : "") +
        sourcesBlock(d) + writesBlock(d));
      relayout();
    },
    /** Record what the node last did. Drawn under the readout, and kept through later redraws until
     *  `clearLog`. */
    log(lines, ok = true) {
      lastRun = { lines: [].concat(lines), ok };
      drawLog();
      relayout();
    },
    /** What the node last published, as rows, plus the lines that need attention. */
    ran(rows, notes = []) {
      lastRun = { rows, notes, ok: true };
      drawLog();
      relayout();
    },
    clearLog() {
      lastRun = null;
      drawLog();
    },
  };
}

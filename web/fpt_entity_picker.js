import { app } from "../../scripts/app.js";
import { addPanel } from "./fpt_panel.js";
import { searchPicker, chipSelect, hideWidget, requireVueNodes, fitNode, dontSerialize,
         restoreDeclaredWidgets, restoreValue, textRows } from "./fpt_dom_widgets.js";

const NONE = "(none)";        // a visible "no value"; an empty option cannot be clicked
const ALL_TYPES = "(all types)";

// Labels read `name (Type)` — the type is context, never part of what is searched.
// "(none)" and "(all types)" are labels for the operator, never values for the site.
function bare(v) {
  return (!v || v === NONE || v === ALL_TYPES) ? "" : v;
}

function typeFromLabel(label) {
  const m = /\s\(([^()]+)\)$/.exec(label || "");
  return m ? m[1] : "";
}

async function get(url) {
  try {
    const r = await fetch(url);
    return await r.json();
  } catch (e) {
    return { items: [], error: String(e) };
  }
}

// Keeps a combo's options in step with the site without touching its value unless the value is gone.
function setOptions(widget, labels, keep) {
  widget.options.values = [NONE].concat(labels);
  const wanted = keep ?? widget.value;
  widget.value = widget.options.values.includes(wanted) ? wanted : widget.options.values[0];
}

// The pickers search the SITE, not the page the site already sent. That is why neither node has a
// link_type combo any more: its only job was to shorten a list, and a list nobody scrolls does not
// need shortening. Filtering in the browser is what made a bespoke box worse than none — a plain
// substring over what is loaded, so `f` found Giraffe Ruler and `f r` did not.

app.registerExtension({
  name: "fpt.pickers",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name === "FPTLoadVersion") return loadPickers(nodeType);
    if (nodeData.name === "FPTPublishVersion") return publishPickers(nodeType);
  },
});

// Publish node. The panel is the point: a publish is remote and irreversible, so everything the run
// would do is on screen before it does it — the name it would create, where that lands, and every
// provenance concept beside the field it will be written to.
function publishPickers(nodeType) {
  // The declared widgets, in INPUT_TYPES order. This is the order a saved graph's widgets_values is
  // in, and the only order anything outside the editor (instrument.py, tools/workflows/) has to know.
  const DECLARED = ["project", "link", "task", "status", "output_name", "fps", "note",
                    "code_template", "source_versions", "attach_workflow", "link_id"];

  // The node maps its own saved values, because the frontend cannot. This node has widgets the
  // class never declared — the two pickers and the panel — and widgets_values is positional, so
  // 10 declared values are walked across 14 slots and every value after the first picker lands one
  // field early: `note` held the status, the template held the note. Silently, which is the worst
  // part: a stranger instrumenting a graph gets Versions with the wrong values and no error.
  //
  // A STOPGAP. The mechanism belongs to the shared widget layer (fpt_dom_widgets.js `mount`) and
  // this whole block should go when LAYOUT_API.md says that layer round trips. Note for whoever
  // writes it: filtering on `widget.serialize !== false` is not enough on its own — addDOMWidget
  // takes `serialize` in its OPTIONS and never copies it onto the widget, so `widget.serialize` is
  // undefined and every picker still counts. Measured on frontend 0.3.x.
  const onConfigure = nodeType.prototype.onConfigure;
  nodeType.prototype.onConfigure = function (info) {
    onConfigure?.apply(this, arguments);
    const named = info?.widgets_values_named;
    const vals = info?.widgets_values || [];
    // Two shapes, and only two. The editor writes a name for every value. Everything else we
    // produce — tools/workflows/, instrument.py, a hand-edited graph — is the declared order and exactly
    // as long. Anything else is left to the frontend rather than guessed at.
    const byName = (named && typeof named === "object" && !Array.isArray(named)) ? named
      : vals.length === DECLARED.length
        ? Object.fromEntries(vals.map((v, i) => [DECLARED[i], v]))
        : null;
    if (!byName) return;
    for (const name of DECLARED) {
      const v = byName[name];
      if (v === undefined || v === null) continue;   // a hole is not a value
      restoreValue(this.widgets?.find((y) => y.name === name), v);
    }
  };

  const onCreated = nodeType.prototype.onNodeCreated;
  nodeType.prototype.onNodeCreated = function () {
    onCreated?.apply(this, arguments);
    const node = this;

    if (!requireVueNodes(this)) return;

    const w = (n) => this.widgets?.find((x) => x.name === n);
    const project = w("project"), link = w("link"), task = w("task"), status = w("status");

    let projectId = 0, linkIds = {}, statusMeta = {}, projectRows = [];
    let linkType = "Shot";   // per project, from /fpt/profile; never assumed (probe 005)
    const typeOf = (label) => typeFromLabel(label) || linkType;

    // Same as the Load node. computeSize() answers the node's MINIMUM and disagrees with what the
    // Vue node actually renders, which is where the empty band under the readout came from; fitNode
    // measures the rendered DOM instead.
    const relayout = () => fitNode(this);

    // Prose, not a name: five lines rather than the stock two-and-a-floor.
    textRows(w("note"), 5);

    const panel = addPanel(this, "Flow PT Publish", relayout);
    // The status the operator picked, drawn the way Flow PT draws it (probe 010). The panel has
    // always known how; on this node it was simply never handed one.
    const statusOf = (label) => statusMeta[bare(label)] || null;

    // Every preview is numbered and only the newest may write. There are two round trips per
    // preview, so a widget changed twice quickly could answer out of order and leave the panel
    // describing the older graph.
    let previewing = 0;
    const preview = async () => {
      const mine = ++previewing;
      panel.loading();
      const q = new URLSearchParams({
        project: project?.value || "", link: bare(link?.value), task: bare(task?.value),
        code_template: w("code_template")?.value || "",
        output_name: w("output_name")?.value || "",
      });
      const d = await get(`/fpt/preview_code?${q}`);
      if (mine !== previewing) return;
      panel.clearLog();
      if (!d.code) {
        panel.show({ error: d.error || "the template does not resolve yet" });
        return;
      }
      // Provenance lives in the executing graph, so hand over the very thing Run would send.
      let extra = {};
      try {
        const { output } = await app.graphToPrompt();
        const r = await fetch("/fpt/preview_publish", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: output, node_id: String(node.id) }),
        });
        extra = await r.json();
      } catch (e) { /* an unbuilt graph simply has nothing to describe yet */ }
      if (mine !== previewing) return;
      // Its `error` is kept out of the spread on purpose: an `error` anywhere in what show() is
      // given replaces the whole readout, and losing the name because the provenance call failed is
      // the wrong trade. It becomes the line under the name instead.
      const { error, ...rest } = extra || {};
      const missing = (rest.missing_fields || []).length;
      // Which show this lands in and which stream it claims to be. Both are combos two rows up, so
      // they are `echo`, not `facts`: the readout repeating the node is noise where the name is
      // supposed to be the signal.
      const echo = [["project", project?.value], ["output", w("output_name")?.value]]
        .filter(([, v]) => bare(v)).map(([label, value]) => ({ label, value }));
      // What a Run does with a BATCH, in front of the operator rather than in the fold: the node
      // publishes one Version per run and the movie's frame rate is a decision, so both are read
      // before Run, not discovered after it.
      const facts = rest.movie ? [{ label: "a batch", value: rest.movie }] : [];
      panel.show({
        ...rest, facts,
        id: -1, code: d.code, task: d.task,
        // preview_code answers with the type it would use even when nothing is picked, so an unset
        // link came back as a bare "Shot" and read like a decision that had been made.
        link: bare(link?.value) ? d.link : "",
        status: statusOf(status?.value), echo,
        // Why the name is not the name a Run would write. Never folded — the name is the readout.
        alert: d.alert || "",
        // The reason lives in the fold now, so the pill has to carry it: a publish that cannot read
        // its provenance, or that would drop a mapped value, is not VALID however good the name is.
        state: (error || missing || d.alert) ? "warn" : "ok",
        why: error ? `provenance could not be read: ${error}`
          : missing ? `${missing} mapped field(s) missing on this site — struck through below`
          : "this is what the next Run will create",
      });
    };
    // `note` and the template are typed, and every keystroke would otherwise cost a graphToPrompt
    // and two requests. A combo is a decision, and answers at once.
    let pending;
    const previewSoon = () => { clearTimeout(pending); pending = setTimeout(preview, 250); };

    app.api.addEventListener("executed", ({ detail }) => {
      if (String(detail.node) !== String(node.id)) return;
      const rows = (detail.output && detail.output.published) || [];
      panel.clearLog();
      if (rows.length) {
        panel.show({
          id: rows[0].id, code: rows[0].code, link: rows[0].link,
          status: statusOf(status?.value), state: "ok",
          why: "",
          // `facts`, not `echo`: what a run actually wrote is nowhere else on the node. `movie` is
          // the frame count and the rate that was actually used — one run is one Version now, so
          // the count belongs beside the media, not in a tally of Versions.
          facts: [
            ...(rows[0].movie ? [{ label: "movie", value: rows[0].movie }] : []),
            ...(rows[0].outputs && rows[0].outputs.length
              ? [{ label: "wrote", value: rows[0].outputs.join(", ") }] : []),
          ],
        });
      }
      const text = (detail.output && detail.output.text) || [];
      if (text.length) panel.log(text, rows.length > 0);
      // What the NEXT run would create, now that this one has taken a number.
      setTimeout(preview, 1200);
    });
    if (!project || !link) return;

    // Same control for the show as for the thing in it: a studio site has hundreds of projects and
    // the combo made you scroll them. No onPick — the widget's own callback is wrapped below and
    // searchPicker fires it, so asking twice would only load the project twice.
    hideWidget(project);
    // The same rows the Load node shows: a project is easier to recognise by its thumbnail and code
    // than by a name, and both nodes drawing it differently is the inconsistency worth avoiding.
    const asCard = (x) => ({ name: x.label, code: x.code || "", image: x.image || "", value: x.label });
    const projectPick = searchPicker(this, project, {
      label: "project",
      placeholder: "search projects",
      empty: "no project here matches those words",
      search: async (q) => {
        const d = await get("/fpt/projects");
        projectRows = d.items || [];
        const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
        const hay = (x) => `${x.label} ${x.code || ""}`.toLowerCase();
        return projectRows.filter((x) => terms.every((t) => hay(x).includes(t))).map(asCard);
      },
    });
    // The picked project's own row, so the trigger carries the thumbnail the popup showed. Without
    // it `refresh()` redraws the name alone and the show you are publishing into is the one place
    // on the node with no picture.
    const projectCard = () => {
      const row = projectRows.find((x) => x.label === project.value);
      return row && asCard(row);
    };

    // The declared combo keeps the value; the picker is what the operator uses. Search is server
    // side (probe 017 `contains`), so two words find one entity out of thousands and each option
    // carries the type it will be linked as.
    hideWidget(link);
    const linkPick = searchPicker(this, link, {
      label: "link",
      placeholder: "search links — `gir rul` finds giraffe_ruler",
      empty: "nothing on this show matches those words",
      search: async (q) => {
        const d = await get(`/fpt/entities?project_id=${projectId}&q=${encodeURIComponent(q)}`);
        for (const x of d.items || []) linkIds[x.label] = x.id;
        return (d.items || []).map((x) => ({
          name: x.label.replace(/\s\([^()]+\)$/, ""), type: x.type, value: x.label,
        }));
      },
    });

    const loadTasks = async (picked) => {
      // The picked value, not the widget's: a widget's own .value is not always assigned yet when
      // its callback fires, and reading it here asked about the PREVIOUS link.
      const chosen = picked ?? link.value;
      const d = await get(`/fpt/tasks?type=${encodeURIComponent(typeOf(chosen))}` +
        `&id=${linkIds[chosen] || 0}`);
      if (task) setOptions(task, d.items.map((x) => x.label));
      await preview();
    };

    const loadLinks = async () => {
      const d = await get(`/fpt/entities?project_id=${projectId}`);
      linkIds = Object.fromEntries(d.items.map((x) => [x.label, x.id]));
      // Hidden, but it still holds the value, so its options must stay legal for a saved workflow
      // whose link this project does not have.
      setOptions(link, d.items.map((x) => x.label));
      linkPick.refresh();
      await loadTasks();
    };

    const loadProject = async (picked) => {
      const d = await get("/fpt/projects");
      projectRows = d.items || [];
      // Read AFTER the fetch: ComfyUI applies a saved workflow's widget values while this is in
      // flight, so a value captured before the await is stale and writing it back reverts the node
      // to the default project — which then needs a manual click or two to correct.
      const chosen = picked ?? project.value;
      projectId = (d.items.find((x) => x.label === chosen) || {}).id || 0;
      setOptions(project, d.items.map((x) => x.label), chosen);
      // Only the fallback for a link that carries no type of its own; a picked label decides its
      // own. Still per project, because one show hangs Versions off Shots and the next off Assets.
      const prof = await get(`/fpt/profile?project_id=${projectId}`);
      linkType = prof.link_type || "Shot";
      if (status) {
        const s = await get(`/fpt/statuses?project_id=${projectId}`);
        statusMeta = Object.fromEntries((s.items || []).map((x) => [x.label, x]));
        setOptions(status, s.items.map((x) => x.label));
      }
      projectPick.refresh(projectCard());
      await loadLinks();
    };

    const wrap = (widget, after) => {
      if (!widget) return;
      const prev = widget.callback;
      widget.callback = function (value) {
        const r = prev?.apply(this, arguments);
        after(value);
        return r;
      };
    };
    wrap(project, loadProject);
    wrap(link, loadTasks);
    // Everything the readout depends on. Nothing here is ever written back by preview(), which is
    // what stops this becoming the resolve loop the Load node had.
    ["task", "status", "attach_workflow"].forEach((n) => wrap(w(n), () => preview()));
    ["code_template", "output_name", "note", "source_versions", "fps"].forEach((n) =>
      wrap(w(n), previewSoon));

    // Every row we add is already marked by domRow; a button is the one litegraph never marks
    // itself, and an injected widget that serializes shifts every declared value after it.
    dontSerialize(this.addWidget("button", "refresh from site", null, loadProject));
    loadProject();
  };
}

// Load node. The inputs are a rule, not an id, so the panel shows which Version the rule lands on
// and what made it — resolved by the node's own code, so the preview cannot disagree with the run.
function loadPickers(nodeType) {
  restoreDeclaredWidgets(nodeType);
  const onCreated = nodeType.prototype.onNodeCreated;
  nodeType.prototype.onNodeCreated = function () {
    onCreated?.apply(this, arguments);

    if (!requireVueNodes(this)) return;

    const w = (n) => this.widgets?.find((x) => x.name === n);
    const project = w("project"), linkTypeW = w("link_type"), link = w("link"), task = w("task");
    const source = w("source"), statuses = w("statuses");
    if (!project || !link) return;

    // Wide enough for `label | control` plus the readout's two columns. The stock 210px default put
    // every provenance label on its own wrapped line.
    if (this.size[0] < 380) this.size[0] = 380;
    // The filter it mirrors is a dozen lines of JSON; the stock floor showed three and hid the rest
    // behind `overflow-hidden`. Anything longer still scrolls, which is the frontend's own answer.
    textRows(w("filters"), 10);

    let projectId = 0, linkIds = {}, projectRows = [];
    // The SG Filters box mirrors the pickers until someone edits it, then it is theirs. Comparing
    // against the last value we wrote is how we tell: no flag to keep in sync, no mode to explain.
    let mirrored = "";

    const relayout = () => fitNode(this);

    // Same control for the show as for the thing in it. A studio site has hundreds of projects and
    // the combo made you scroll them; two words narrow it the way they narrow everything else here.
    // Rows carry the project's thumbnail and code, which is how a show is recognised in Flow PT's
    // own UI — `image` is a presigned URL re-signed on every read (field_types/image).
    hideWidget(project);
    const asCard = (x) => ({ name: x.label, code: x.code || "", image: x.image || "", value: x.label });
    const projectPick = searchPicker(this, project, {
      label: "project",
      placeholder: "search projects",
      empty: "no project here matches those words",
      search: async (q) => {
        const d = await get("/fpt/projects");
        projectRows = d.items || [];
        const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
        const hay = (x) => `${x.label} ${x.code || ""}`.toLowerCase();
        return projectRows.filter((x) => terms.every((t) => hay(x).includes(t))).map(asCard);
      },
      onPick: (it) => loadProject(it.value),
    });
    const projectCard = () => {
      const row = projectRows.find((x) => x.label === project.value);
      return row && asCard(row);
    };

    // The declared combo keeps the value; the picker is what the operator actually uses. Server-side
    // search means two words match two words — the combo could only filter the page it already had.
    hideWidget(link);
    const linkPick = searchPicker(this, link, {
      label: "link",
      placeholder: "search links — `gir rul` finds giraffe_ruler",
      empty: "nothing on this project matches those words",
      search: async (q) => {
        const t = (linkTypeW && linkTypeW.value !== ALL_TYPES)
          ? `&type=${encodeURIComponent(linkTypeW.value)}` : "";
        const d = await get(`/fpt/entities?project_id=${projectId}&q=${encodeURIComponent(q)}${t}`);
        for (const x of d.items || []) linkIds[x.label] = x.id;
        return (d.items || []).map((x) => ({
          name: x.label.replace(/\s\([^()]+\)$/, ""), type: x.type, value: x.label,
        }));
      },
      onPick: () => loadTasks(),
    });
    // Chips, not a comma-separated text field: each status in its own colour (probe 010), and no
    // one has to type a label exactly right.
    hideWidget(statuses);
    const statusChips = statuses && chipSelect(this, statuses, {
      label: "statuses",
      empty: "this project offers no statuses",
      load: async () => (await get(`/fpt/statuses?project_id=${projectId}`)).items || [],
    });

    const panel = addPanel(this, "Flow PT Load", relayout);

    // Every resolve is numbered, and only the newest may write. Two requests are in flight whenever
    // a widget is changed twice quickly, they can come back in either order, and the panel used to
    // render whichever answered last — so it flickered through stale states before settling.
    let resolving = 0;

    // `over` carries the value the callback was handed. A widget's own .value is not always
    // assigned yet when its callback fires (see `wrap`), so reading it here asked the site about
    // the PREVIOUS status and rendered that answer as if it were current.
    const refresh = async (over = {}) => {
      const mine = ++resolving;
      const val = (n) => (n in over ? over[n] : w(n)?.value);
      const q = new URLSearchParams({
        project_id: projectId, project: project.value || "",
        link_type: bare(linkTypeW?.value), link: bare(link.value), task: bare(val("task")),
        name_contains: val("name_contains") || "",
        newest_by: val("newest_by") || "",
        pin_version_id: val("pin_version_id") || 0,
        // Which source, so the readout answers for the file that will be read rather than for the
        // Version as a whole: two PublishedFiles on one Version can declare different colour spaces.
        source: val("source") || "auto",
        // Only when it is an override. While the box is still mirroring, sending it back would let
        // its own (now stale) content win over the very fields it is meant to reflect.
        // String(): a workflow saved before this widget moved can land a number here, and a raw
        // .trim() on it takes the whole picker down.
        filters: String(val("filters") ?? "").trim() === mirrored.trim()
          ? "" : String(val("filters") ?? ""),
      });
      for (const s of String(val("statuses") || "").split(",")) {
        const t = s.trim();
        if (t) q.append("statuses", t);
      }
      panel.loading();
      const d = await get(`/fpt/resolve?${q}`);
      if (mine !== resolving) return;      // superseded while we waited; that answer is the current one
      panel.show(d);
      const box = w("filters");
      if (box && d.filters && String(box.value ?? "").trim() === mirrored) {
        const next = JSON.stringify(d.filters, null, 1);
        if (next !== mirrored) {          // only when it actually changed; a no-op write still
          mirrored = next;                // notifies under the Vue value store
          box.value = next;
        }
      }
      if (source) {
        source.options.values = ["auto"].concat(d.media || []);
        // A saved value the site no longer offers falls back to `auto` rather than staying as a
        // combo entry the editor cannot draw. A PublishedFile key carries its type and filename, so
        // a file that was renamed or re-typed stops matching — which is the honest outcome: the
        // node would otherwise have to guess which of several files the old label meant.
        if (!source.options.values.includes(source.value)) source.value = "auto";
      }
      app.graph.setDirtyCanvas(true, true);
    };

    const loadTasks = async (picked) => {
      const chosen = picked ?? link.value;
      const d = await get(`/fpt/tasks?type=${encodeURIComponent(typeFromLabel(chosen))}` +
        `&id=${linkIds[chosen] || 0}`);
      if (task) setOptions(task, d.items.map((x) => x.label));
      await refresh();
    };

    const loadLinks = async (picked) => {
      const chosen = picked ?? linkTypeW?.value;
      const t = (chosen && chosen !== ALL_TYPES) ? `&type=${encodeURIComponent(chosen)}` : "";
      const d = await get(`/fpt/entities?project_id=${projectId}${t}`);
      linkIds = Object.fromEntries(d.items.map((x) => [x.label, x.id]));
      // The combo is hidden but still holds the value, so its options must stay legal for a saved
      // workflow whose link this project does not have.
      setOptions(link, d.items.map((x) => x.label));
      linkPick.refresh();
      await loadTasks();
    };

    const loadProject = async (picked) => {
      const d = await get("/fpt/projects");
      projectRows = d.items || [];
      const chosen = picked ?? project.value;   // after the await; the widget value lags
      projectId = (d.items.find((x) => x.label === chosen) || {}).id || 0;
      setOptions(project, d.items.map((x) => x.label), chosen);
      if (linkTypeW) {
        const t = await get(`/fpt/link_types?project_id=${projectId}`);
        const vals = t.items.map((x) => x.label);
        linkTypeW.options.values = vals;
        if (!vals.includes(linkTypeW.value)) linkTypeW.value = ALL_TYPES;
      }
      projectPick.refresh(projectCard());
      statusChips?.reload();
      await loadLinks();
    };

    const wrap = (widget, after) => {
      if (!widget) return;
      const prev = widget.callback;
      widget.callback = function (value) {
        const r = prev?.apply(this, arguments);
        after(value);
        return r;
      };
    };
    wrap(project, loadProject);
    wrap(linkTypeW, loadLinks);
    wrap(link, loadTasks);
    // `filters` is deliberately absent. refresh writes it (`box.value = mirrored`), and wrapping it
    // made that write call refresh again — 7 resolves every 6 seconds at idle, one always in flight,
    // so the panel could never leave "loading".
    // `source` is here and `frame`/`frame_count` are not: which file is read changes the type, the
    // count and the declared colour space the readout shows, while where in it to start does not.
    ["task", "name_contains", "statuses", "newest_by", "pin_version_id", "source"].forEach((n) =>
      wrap(w(n), (value) => refresh({ [n]: value })));

    dontSerialize(this.addWidget("button", "refresh from site", null, loadProject));
    loadProject();
  };
}

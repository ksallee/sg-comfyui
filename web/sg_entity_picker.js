/* The editor half of both nodes: the site-backed pickers, the readout, and the requests that fill
 * them.
 *
 * A picker over a list the site pages searches the site, not the page already sent. A browser-side
 * substring over what is loaded finds `giraffe_ruler` for `f` and not for `f r`. `task` and
 * `status` are the exceptions: the Tasks on one link and the statuses on one project arrive as
 * complete lists, so their words are matched here.
 */
import { app } from "../../scripts/app.js";
import { addPanel } from "./sg_panel.js";
import { onSession } from "./sg_settings.js";
import { searchPicker, chipSelect, hideWidget, requireVueNodes, fitNode, dontSerialize,
         restoreDeclaredWidgets, restoreValue, textRows, cascade, call,
         setPlaceholder, templateCompletion } from "./sg_dom_widgets.js";

const NONE = "(none)";        // a visible "no value"; an empty option cannot be clicked

/** The site's own value for a label. "(none)" is a label for the operator. */
const bare = (v) => (!v || v === NONE) ? "" : v;

/** Sync from SG. The server drops its cached site reads first, so a Task or Step edited on the site
 *  since the last read is seen. Other open nodes read the site again on their next preview. */
const resync = async (reload) => {
  await call("/sg/sync", { body: {} });
  return reload();
};

/** The type out of a `name (Type)` label. Context on the row, not part of what is searched. */
// Which of a node definition's inputs are widgets, in declared order. An input slot has a type name
// this list does not list, so it is skipped. A combo arrives as an array of its labels.
// Allowed types are named rather than excluded: a new slot type would otherwise be counted as a
// widget and shift each value after it.
const WIDGET_TYPES = new Set(["STRING", "INT", "FLOAT", "BOOLEAN", "COMBO"]);

function declaredWidgets(nodeData) {
  const out = [];
  for (const section of ["required", "optional"]) {
    for (const [name, spec] of Object.entries(nodeData?.input?.[section] || {})) {
      if (Array.isArray(spec?.[0]) || WIDGET_TYPES.has(spec?.[0])) out.push(name);
    }
  }
  return out;
}

function typeFromLabel(label) {
  const m = /\s\(([^()]+)\)$/.exec(label || "");
  return m ? m[1] : "";
}

/** The same label without its trailing type. */
const withoutType = (label) => String(label ?? "").replace(/\s\([^()]+\)$/, "");

/** Keep a combo's options in step with the site, and return the site's sentence if it sent one.
 *  The value is changed only when it is no longer in the list.
 *
 *  An answer with `error` leaves the options and the value alone. A login that expired while the
 *  graph was opening would otherwise reset link, task and status to "(none)", and the next Run
 *  would publish an unlinked Version. */
function setOptions(widget, d, keep) {
  if (!widget) return "";
  if (d.error) return d.error;
  widget.options.values = [NONE].concat((d.items || []).map((x) => x.label));
  const wanted = keep ?? widget.value;
  widget.value = widget.options.values.includes(wanted) ? wanted : widget.options.values[0];
  return "";
}

/** Chain `after` onto a widget's callback, keeping the callback already set. */
function wrap(widget, after) {
  if (!widget) return;
  const prev = widget.callback;
  widget.callback = function (value) {
    const r = prev?.apply(this, arguments);
    after(value);
    return r;
  };
}

/** A project as a picker row. A show is recognised by its thumbnail and code as much as by its
 *  name. `image` is a presigned URL, re-signed on each read (field_types/image). */
const projectCard = (x) => ({ name: x.label, code: x.code || "", image: x.image || "",
                              value: x.label });

/** The project picker on both nodes. A studio site has hundreds of projects, so this searches name
 *  and code rather than listing them in a combo. */
function projectPicker(node, widget, state, onPick) {
  hideWidget(widget);
  return searchPicker(node, widget, {
    label: "project",
    placeholder: "search projects",
    empty: "No project matches those words.",
    search: async (q, { live, signal }) => {
      const d = await call("/sg/projects", { signal });
      if (!live()) return [];      // a superseded search records nothing
      state.projects = d.items || [];
      const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
      const hay = (x) => `${x.label} ${x.code || ""}`.toLowerCase();
      return state.projects.filter((x) => terms.every((t) => hay(x).includes(t))).map(projectCard);
    },
    onPick,
  });
}

/** Read the projects, point `state` at the one picked, and keep the hidden combo legal. Returns the
 *  sentence to show, or "".
 *
 * The picked value is read after the fetch. ComfyUI applies a saved graph's widget values while
 * this is in flight, so a value read before the await is stale, and writing it back resets the
 * node to the default project.
 */
async function selectProject(widget, state, picked, tok) {
  const d = await call("/sg/projects", tok);
  if (!tok.live) return "";
  if (d.error) return d.error;
  state.projects = d.items || [];
  let chosen = picked ?? widget.value;
  // "(none)" in a saved graph is no choice. No choice means the project under Settings, which is
  // the project a new node opens on. A template then opens on the operator's show.
  if (!bare(chosen)) chosen = (state.projects.find((x) => x.id === d.default) || {}).label || chosen;
  const row = state.projects.find((x) => x.label === chosen);
  state.projectId = row?.id || 0;
  widget.options.values = [NONE].concat(state.projects.map((x) => x.label));
  // A project this login cannot see stays on the widget rather than being replaced by "(none)".
  // The graph names a show that exists, and an operator who signs in as themselves gets it back.
  restoreValue(widget, chosen || NONE);
  return (row || !bare(chosen))
    ? "" : `No project named ${chosen} on this site. Pick one from the list.`;
}

/** The row behind the combo's current value, so the trigger shows the project's thumbnail. */
function currentProject(widget, state) {
  const row = state.projects.find((x) => x.label === widget.value);
  return row && projectCard(row);
}

/** The link picker on both nodes. `contains` runs on the site (probe 017), so two words find one
 *  entity out of thousands, and each row names the type it will be linked as. Each row drawn
 *  records its id in `state.linkIds`, which turns a picked label back into an entity id. */
function linkPicker(node, widget, state, { empty, onPick }) {
  hideWidget(widget);
  return searchPicker(node, widget, {
    label: "link",
    placeholder: "search links",
    empty,
    search: async (q, { live, signal }) => {
      const d = await call(`/sg/entities?project_id=${state.projectId}` +
        `&q=${encodeURIComponent(q)}`, { signal });
      if (!live()) return [];      // a superseded search records no ids
      for (const x of d.items || []) state.linkIds[x.label] = x.id;
      return (d.items || []).map((x) => ({
        name: withoutType(x.label), type: x.type, value: x.label,
      }));
    },
    onPick,
  });
}

/** The links on the project, into the hidden combo. The hidden combo is still the widget that is
 *  saved, so its options must stay legal for a saved graph whose link this project does not
 *  have. */
async function loadLinkOptions(widget, state, tok) {
  const d = await call(`/sg/entities?project_id=${state.projectId}`, tok);
  if (!tok.live) return "";
  if (d.error) return d.error;
  state.linkIds = Object.fromEntries((d.items || []).map((x) => [x.label, x.id]));
  return setOptions(widget, d);
}

/** The tasks on one link, into the `task` combo and into `state.tasks` for the picker. */
async function loadTaskOptions(widget, state, type, id, tok) {
  const d = await call(`/sg/tasks?type=${encodeURIComponent(type)}&id=${id || 0}`, tok);
  if (!tok.live) return "";
  if (!d.error) state.tasks = d.items || [];
  return setOptions(widget, d);
}

/** The task picker on both nodes.
 *
 * A combo cannot show this list. Nodes 2.0 builds `WidgetSelectDefault` from the node definition
 * once, and `task` is declared as "(none)" alone because the Tasks depend on the link. A later
 * `options.values` does not reach the built component, so the dropdown offers one row.
 *
 * The words are matched here rather than on the site. The Tasks on one link arrive as a complete
 * list.
 */
function taskPicker(node, widget, state, { onPick } = {}) {
  hideWidget(widget);
  return searchPicker(node, widget, {
    label: "task",
    placeholder: "search tasks",
    empty: "No Task on this link matches those words.",
    search: async (q) => {
      const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
      const hay = (x) => `${x.label} ${x.step || ""}`.toLowerCase();
      const rows = (state.tasks || [])
        .filter((x) => terms.every((t) => hay(x).includes(t)))
        // The step beside the name, in the site's word for it, where the Task has one.
        .map((x) => ({ name: x.label, code: x.step || "", value: x.label }));
      // A Version need not be for a Task, so "(none)" is a row. A typed term is about the Tasks,
      // so it drops out of a search.
      return terms.length ? rows : [{ name: NONE, value: NONE }].concat(rows);
    },
    onPick,
  });
}

/** The status picker on the publish node. One status, drawn the way SG draws it (recipe 010).
 *
 * A combo cannot show this list either. The statuses a project allows are its own (probe 009), and
 * `WidgetSelectDefault` keeps the list it was built from, which is the list of the project
 * INPUT_TYPES was evaluated for. A combo would offer the first project's statuses on the second.
 * "(none)" is a row: it sends no status, and the site applies the field default.
 */
function statusPicker(node, widget, state, { onPick } = {}) {
  hideWidget(widget);
  return searchPicker(node, widget, {
    label: "status",
    placeholder: "search statuses",
    empty: "No status on this project matches those words.",
    search: async (q) => {
      const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
      const hay = (x) => `${x.label} ${x.code || ""}`.toLowerCase();
      const rows = (state.statuses || []).filter((x) => terms.every((t) => hay(x).includes(t)))
        .map((x) => ({ name: x.label, code: x.code || "", icon: x.icon, rgb: x.rgb,
                       value: x.label }));
      return terms.length ? rows : [{ name: NONE, value: NONE }].concat(rows);
    },
    onPick,
  });
}

app.registerExtension({
  name: "sg.pickers",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name === "SGLoadVersion") return loadPickers(nodeType, nodeData);
    if (nodeData.name === "SGPublishVersion") return publishPickers(nodeType, nodeData);
  },
});

// Publish node. A publish is remote and cannot be undone, so what the run would do is on screen
// before it runs: the name it would create, the path it would write to, and each provenance concept
// beside the field it will be written to.
function publishPickers(nodeType, nodeData) {
  // The declared widgets, in INPUT_TYPES order, read from the definition the server sent. This is
  // the order of a saved graph's widgets_values.
  restoreDeclaredWidgets(nodeType, declaredWidgets(nodeData));

  const onCreated = nodeType.prototype.onNodeCreated;
  nodeType.prototype.onNodeCreated = function () {
    onCreated?.apply(this, arguments);
    const node = this;

    if (!requireVueNodes(this)) return;

    const w = (n) => this.widgets?.find((x) => x.name === n);
    const project = w("project"), link = w("link"), task = w("task"), status = w("status");

    const state = { projectId: 0, projects: [], linkIds: {}, tasks: [], statuses: [] };
    let statusMeta = {};
    let linkType = "Shot";   // per project, from /sg/profile; never assumed (probe 005)
    // A picked label names its own type. `linkType` is the fallback for a label that does not.
    const typeOf = (label) => typeFromLabel(label) || linkType;

    const relayout = () => fitNode(this);

    textRows(w("note"), 5);   // prose, not a name

    const panel = addPanel(this, "SG Publish", relayout);
    // The status the operator picked, drawn the way SG draws it (probe 010).
    const statusOf = (label) => statusMeta[bare(label)] || null;

    // The templates Settings has in force, by widget, read from each preview. The completion
    // lists one of them as its Default row.
    let inForce = {};
    const TEMPLATES = [["root_name", "root"], ["code_template", "name"],
                       ["sequence_path", "sequence"], ["still_path", "still"],
                       ["movie_path", "movie"]];
    // An opening brace lists the tokens a template of this kind may use, and a token that names an
    // entity descends into that type's own fields. `{entity}` is the picked link's type, else what
    // this project links a Version to, so both are passed.
    for (const [widget, kind] of TEMPLATES) {
      templateCompletion(this, { name: widget, kind,
                                 project: () => project?.value || "",
                                 linkType: () => typeFromLabel(bare(link?.value)),
                                 defaultTemplate: () => inForce[widget] || "" });
    }

    // Each preview is numbered and the newest one alone may write. There are two requests per
    // preview, so a widget changed twice quickly can answer out of order and leave the panel
    // describing the older graph.
    let previewing = 0;
    // The latest Version on this link and the files it wrote, as links. Built from any object with
    // {id, site_url, files}: the preview's `latest` before a run, the executed payload after one.
    // A `%04d` pattern is not a file, so its link opens the containing folder.
    const runFacts = (r) => !r || !r.id ? [] : [
      ...(r.site_url ? [{ label: "latest", value: `${r.code || "Version " + r.id}`,
                          href: `${r.site_url}/detail/Version/${r.id}` }] : []),
      ...(r.files || []).map((f) => ({
        label: { frames: "frames path", still: "still path" }[f.kind] || "clip path",
        value: f.path,
        href: "file://" + f.path.replace(/[^/]*$/, ""),
      })),
    ];

    // `keepLog` is passed by the redraw after a run. The readout above changes, and the lines that
    // run wrote stay under it until the next Run or the next edit.
    const preview = async (keepLog = false) => {
      const mine = ++previewing;
      panel.loading();
      const q = new URLSearchParams({
        project: project?.value || "", link: bare(link?.value), task: bare(task?.value),
        code_template: w("code_template")?.value || "",
        root_name: w("root_name")?.value || "",
      });
      const d = await call(`/sg/preview_code?${q}`);
      if (mine !== previewing) return;
      if (!keepLog) panel.clearLog();
      // An empty template field is set by Settings. The template in force is drawn greyed inside
      // the empty field, where one would be typed, and is the completion's Default row whether
      // the field is empty or not.
      inForce = d.settings || {};
      for (const [name] of TEMPLATES) {
        setPlaceholder(node, name, w(name)?.value?.trim() ? "" : inForce[name] || "");
      }
      if (!d.code) {
        panel.show({ error: d.error || "Version name produced nothing. Edit version name on this "
          + "node, or empty it to use the default under Settings, then SG." });
        return;
      }
      // Provenance is read from the executing graph, so this sends what Run would send.
      let extra = {};
      try {
        const { output } = await app.graphToPrompt();
        extra = await call("/sg/preview_publish",
                           { body: { prompt: output, node_id: String(node.id) } });
      } catch (e) { /* an unbuilt graph simply has nothing to describe yet */ }
      if (mine !== previewing) return;
      // Its `error` is kept out of the spread. An `error` anywhere in what show() is given replaces
      // the readout, and the name must survive a failed provenance call. It becomes the line under
      // the name instead.
      const { error, ...rest } = extra || {};
      // What this Run would publish: the review media, the files, and the paths they are written
      // to. One run creates one Version. The previous Version is drawn as a link alone, so its
      // files do not read as this Run's.
      const facts = []
        .concat(rest.review ? [{ label: "review", value: rest.review }] : [])
        .concat(rest.files ? [{ label: "files", value: rest.files }] : [])
        .concat((rest.paths || []).map((x) => ({ label: x.label, value: x.path })))
        .concat(runFacts(d.latest));
      panel.show({
        ...rest, facts,
        id: -1, code: d.code, task: d.task,
        // preview_code returns the type it would use even when nothing is picked, so an unset link
        // would otherwise read as a "Shot" that had been decided.
        link: bare(link?.value) ? d.link : "",
        status: statusOf(status?.value),
        // What stops this Run: a name that cannot be written, or files that cannot be written.
        // Not folded, because neither is about the name above it.
        alert: d.alert || rest.alert || "",
        // The reason is in the fold, so the pill states the state. A publish that cannot read its
        // provenance, or that would drop a mapped value, is not valid whatever the name reads.
        state: (error || d.alert || rest.alert) ? "warn" : "ok",
        why: error ? `Provenance could not be read. ${error}`
          : "This is what the next Run will create.",
      });
    };
    // A typed widget is debounced. Each keystroke costs a graphToPrompt and two requests. A picked
    // value redraws at once.
    let pending;
    const previewSoon = () => { clearTimeout(pending); pending = setTimeout(preview, 250); };

    // ComfyUI skips a node whose inputs did not change and keeps its last result. That is what
    // stops a re-run from filing duplicate Versions. It is written on the panel: the readout above
    // names the next version, and a silent skip reads as a publish that failed. ComfyUI announces
    // the cached nodes first, then replays each one's old result as `executed`, so the flag is read
    // there and the sentence is written after the readout it explains.
    let cached = false;
    // Each listener is dropped when the node is removed. A workflow opened and closed would
    // otherwise leave its listeners registered, and each later run would redraw a panel that is on
    // no screen.
    const listen = (name, fn) => {
      app.api.addEventListener(name, fn);
      const prev = node.onRemoved;
      node.onRemoved = function () {
        app.api.removeEventListener(name, fn);
        return prev?.apply(this, arguments);
      };
    };
    listen("execution_start", () => { cached = false; panel.clearLog(); });
    listen("execution_cached", ({ detail }) => {
      cached = (detail.nodes || []).map(String).includes(String(node.id));
    });
    listen("executed", ({ detail }) => {
      if (String(detail.node) !== String(node.id)) return;
      const rows = (detail.output && detail.output.published) || [];
      panel.clearLog();
      if (rows.length && cached) {
        panel.show({ id: rows[0].id, code: rows[0].code, link: rows[0].link,
                     status: statusOf(status?.value), state: "warn", why: "" });
        panel.log(`Not published again: nothing changed since ${rows[0].code}. Change the image `
          + "or a field on this node, then Run, for the next version.", false);
        return;
      }
      if (rows.length) {
        const r = rows[0];
        panel.show({ id: r.id, code: r.code, link: r.link, status: statusOf(status?.value),
                     state: "ok", why: "" });
        // What the run did, as rows: the Version by name (its id is in the link), the review
        // media, the files in the format they were written in, and the path of each.
        const files = (r.files || []).map((f) => f.kind === "movie"
          ? "the clip as it is"
          : `${f.count} frame${f.count === 1 ? "" : "s"} as ${r.format || "PNG"}`).join(", ");
        panel.ran([
          ...(r.site_url ? [["published", r.code, `${r.site_url}/detail/Version/${r.id}`]] : []),
          ...(r.media ? [["review", r.media]] : []),
          ...(files ? [["files", files]] : []),
          // The client that submitted this Run, known to the run alone. It names itself in the
          // body of /prompt. A Run that named no client leaves the row off.
          ...(r.client ? [["submitted by", r.client]] : []),
          ...runFacts({ ...r, site_url: "" }).map((x) => [x.label, x.value, x.href]),
        ], r.notes || []);
      } else {
        const text = (detail.output && detail.output.text) || [];
        if (text.length) panel.log(text, false);
      }
      // What the next run would create, now that this one has taken a number. The lines this run
      // wrote are the Version id and the paths it wrote to, so they stay on the panel.
      setTimeout(() => preview(true), 1200);
    });
    if (!project || !link || !task) return;

    // No onPick on the project. The widget's callback is wrapped below and searchPicker fires it,
    // so an onPick as well would load the project twice.
    const projectPick = projectPicker(this, project, state);
    const linkPick = linkPicker(this, link, state, {
      empty: "No link on this project matches those words.",
    });
    const taskPick = taskPicker(this, task, state);
    const statusPick = status && statusPicker(this, status, state);

    // Picking a second project supersedes the reads the first one started. One cascade at a time,
    // and each step of it is passed the token the entry point began with.
    const chain = cascade();
    // A site that answered with a sentence instead of rows stops the cascade there. Each widget
    // keeps the value the saved graph gave it, and the sentence is on the panel.
    const stop = (msg) => { if (msg) panel.show({ error: msg }); return !!msg; };

    const loadTasks = async (picked, tok = chain.begin()) => {
      // The picked value, not the widget's. A widget's .value is not assigned yet when its
      // callback fires, so reading it here would ask about the previous link.
      const chosen = picked ?? link.value;
      const bad = await loadTaskOptions(task, state, typeOf(chosen), state.linkIds[chosen], tok);
      if (!tok.live || stop(bad)) return;
      taskPick.refresh();
      await preview();
    };

    const loadLinks = async (tok = chain.begin()) => {
      const bad = await loadLinkOptions(link, state, tok);
      if (!tok.live || stop(bad)) return;
      linkPick.refresh();
      await loadTasks(undefined, tok);
    };

    const loadProject = async (picked, tok = chain.begin()) => {
      const bad = await selectProject(project, state, picked, tok);
      if (!tok.live || stop(bad)) return;
      // Per project. One show links Versions to Shots and the next to Assets.
      const prof = await call(`/sg/profile?project_id=${state.projectId}`, tok);
      if (!tok.live || stop(prof.error)) return;
      linkType = prof.link_type || "Shot";
      if (status) {
        const s = await call(`/sg/statuses?project_id=${state.projectId}`, tok);
        if (!tok.live || stop(setOptions(status, s))) return;
        statusMeta = Object.fromEntries((s.items || []).map((x) => [x.label, x]));
        state.statuses = s.items || [];
        statusPick.refresh(statusOf(status.value));
      }
      projectPick.refresh(currentProject(project, state));
      await loadLinks(tok);
    };

    wrap(project, loadProject);
    wrap(link, loadTasks);
    // The widgets the readout depends on. preview() writes none of them back, so this is not a
    // loop.
    ["task", "status", "attach_workflow", "register_files"].forEach((n) =>
      wrap(w(n), () => preview()));
    ["code_template", "root_name", "note", "source_versions", "colour_space", "sequence_path",
     "still_path", "movie_path"].forEach((n) => wrap(w(n), previewSoon));

    // domRow marks each row we add. litegraph does not mark a button, and an injected widget that
    // serializes shifts each declared value after it. The callback takes no arguments: litegraph
    // passes a button's callback the canvas and the node, and the cascade token is the second
    // parameter.
    dontSerialize(this.addWidget("button", "Sync from SG", null, () => resync(loadProject)));
    // Who this publishes as is set under Settings. A change there changes what each picker reads
    // (probe 027), so the node reloads.
    onSession(this, () => loadProject());
    loadProject();
  };
}

// Load node. The inputs are a rule, not an id, so the panel shows which Version the rule resolves
// to and what made it. The node's own code resolves it, so the preview cannot disagree with the
// run.
function loadPickers(nodeType, nodeData) {
  restoreDeclaredWidgets(nodeType, declaredWidgets(nodeData));
  const onCreated = nodeType.prototype.onNodeCreated;
  nodeType.prototype.onNodeCreated = function () {
    onCreated?.apply(this, arguments);

    if (!requireVueNodes(this)) return;

    const w = (n) => this.widgets?.find((x) => x.name === n);
    const project = w("project"), link = w("link"), task = w("task");
    const source = w("source"), statuses = w("statuses");
    if (!project || !link || !task) return;

    // Wide enough for `label | control` plus the readout's two columns. The stock 210px default
    // wraps each provenance label onto a line of its own.
    if (this.size[0] < 380) this.size[0] = 380;
    // The filter box shows a dozen lines of JSON. The stock floor shows three. Anything longer
    // scrolls, which is the frontend's behaviour.
    textRows(w("filters"), 10);

    const state = { projectId: 0, projects: [], linkIds: {}, tasks: [] };
    const relayout = () => fitNode(this);

    const projectPick = projectPicker(this, project, state, (it) => loadProject(it.value));
    const linkPick = linkPicker(this, link, state, {
      empty: "No link on this project matches those words.",
      onPick: () => loadTasks(),
    });
    const taskPick = taskPicker(this, task, state);
    hideWidget(statuses);
    const statusChips = statuses && chipSelect(this, statuses, {
      label: "statuses",
      empty: "This project has no statuses.",
      load: async () => (await call(`/sg/statuses?project_id=${state.projectId}`)).items || [],
    });

    const panel = addPanel(this, "SG Load", relayout);

    // Each resolve is numbered and the newest one alone may write. Two requests are in flight when
    // a widget is changed twice quickly, they can come back in either order, and the panel would
    // otherwise flicker through stale states before settling.
    let resolving = 0;
    // The last answer from /sg/resolve, kept so the frame widgets redraw the readout without asking
    // the site again. The range was read from disk once, and which slice of it to take is
    // arithmetic.
    let resolved = null;

    const draw = () => {
      if (!resolved) return;
      panel.show({
        ...resolved,
        // What the two frame widgets ask for, so the frames row states what will be read rather
        // than what exists.
        frame_ask: Number(w("frame")?.value || 0),
        count_ask: Number(w("frame_count")?.value ?? 0),
        // A pinned id ignores the fields above it, so the panel states that. `extra filters`
        // narrows rather than replaces, so it is not an override and adds no line.
        alert: resolved.alert || (resolved.pinned
          ? `Pinned to Version ${resolved.pinned}. All the fields above are ignored.` : ""),
      });
    };

    const refresh = async (over = {}) => {
      const mine = ++resolving;
      // `over` is the value the callback was passed. A widget's .value is not assigned yet when
      // its callback fires, so reading it here would ask about the previous pick.
      const val = (n) => (n in over ? over[n] : w(n)?.value);
      const q = new URLSearchParams({
        project_id: state.projectId, project: project.value || "",
        link: bare(link.value), task: bare(val("task")),
        name_contains: val("name_contains") || "",
        newest_by: val("newest_by") || "",
        pin_version_id: val("pin_version_id") || 0,
        // Which source, so the readout describes the file that will be read rather than the
        // Version. Two PublishedFiles on one Version can declare different colour spaces.
        source: val("source") || "auto",
        // String(): a graph saved before this widget moved can put a number here, and .trim() on a
        // number throws.
        filters: String(val("filters") ?? ""),
      });
      for (const s of String(val("statuses") || "").split(",")) {
        const t = s.trim();
        if (t) q.append("statuses", t);
      }
      panel.loading();
      const d = await call(`/sg/resolve?${q}`);
      if (mine !== resolving) return;      // superseded while we waited
      const pinned = Number(val("pin_version_id") || 0);
      resolved = { ...d, pinned };
      draw();
      if (source) {
        source.options.values = ["auto"].concat(d.media || []);
        // A saved value the site no longer offers falls back to `auto` rather than staying as a
        // combo entry the editor cannot draw. A PublishedFile key includes its type and filename,
        // so a file that was renamed or re-typed stops matching. The node has no way to tell which
        // of several files the old label named.
        if (!source.options.values.includes(source.value)) source.value = "auto";
      }
      app.graph.setDirtyCanvas(true, true);
    };

    // Picking a second project supersedes every read the first one started: one cascade at a time,
    // and each step of it is handed the token the entry point began with.
    const chain = cascade();
    // A site that answered with a sentence instead of rows stops the cascade there: every widget
    // keeps the value the saved graph gave it, and the sentence is on the panel.
    const stop = (msg) => { if (msg) panel.show({ error: msg }); return !!msg; };

    const loadTasks = async (picked, tok = chain.begin()) => {
      const chosen = picked ?? link.value;
      const bad = await loadTaskOptions(task, state, typeFromLabel(chosen), state.linkIds[chosen],
                                        tok);
      if (!tok.live || stop(bad)) return;
      taskPick.refresh();
      await refresh();
    };

    const loadLinks = async (tok = chain.begin()) => {
      const bad = await loadLinkOptions(link, state, tok);
      if (!tok.live || stop(bad)) return;
      linkPick.refresh();
      await loadTasks(undefined, tok);
    };

    const loadProject = async (picked, tok = chain.begin()) => {
      const bad = await selectProject(project, state, picked, tok);
      if (!tok.live || stop(bad)) return;
      projectPick.refresh(currentProject(project, state));
      statusChips?.reload();
      await loadLinks(tok);
    };

    wrap(project, loadProject);
    wrap(link, loadTasks);
    // `source` is in this list: which file is read changes the type, the count and the declared
    // colour space the readout shows.
    ["task", "name_contains", "statuses", "newest_by", "pin_version_id", "source"].forEach((n) =>
      wrap(w(n), (value) => refresh({ [n]: value })));
    // `frame` and `frame_count` redraw and do not re-resolve. Where in a sequence to start does not
    // change what resolved, it changes which frames the readout states will be read.
    ["frame", "frame_count"].forEach((n) => wrap(w(n), draw));
    // `filters` is the operator's own conditions, ANDed onto the fields server-side. Nothing writes
    // it, so it triggers a refresh like any other field. Debounced, because it is typed.
    let typing;
    wrap(w("filters"), (value) => {
      clearTimeout(typing);
      typing = setTimeout(() => refresh({ filters: value }), 400);
    });

    dontSerialize(this.addWidget("button", "Sync from SG", null, () => resync(loadProject)));
    onSession(this, () => loadProject());
    loadProject();
  };
}

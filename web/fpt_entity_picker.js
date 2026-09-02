import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

const NONE = "";

// Labels read `name (Type)` — the type is context, never part of what is searched.
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
function setOptions(widget, labels) {
  widget.options.values = [NONE].concat(labels);
  if (!widget.options.values.includes(widget.value)) widget.value = NONE;
}

app.registerExtension({
  name: "fpt.pickers",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name === "FPTFetchVersion") return fetchPickers(nodeType);
    if (nodeData.name !== "FPTPublishVersion") return;

    const onCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      onCreated?.apply(this, arguments);

      const w = (n) => this.widgets?.find((x) => x.name === n);
      const project = w("project"), link = w("link"), task = w("task"), status = w("status");
      if (!project || !link) return;

      // project ids are not on the widgets - the combos carry labels, so the server resolves them.
      let projectId = 0;
      let linkType = "Shot";   // replaced per project by /fpt/profile; never assume (probe 005)
      let linkIds = {};

      const typeOf = (label) => typeFromLabel(label) || linkType;
      const loadTasks = async () => {
        const id = linkIds[link.value] || 0;
        const d = await get(`/fpt/tasks?type=${encodeURIComponent(typeOf(link.value))}&id=${id}`);
        if (task) setOptions(task, d.items.map((x) => x.label));
        app.graph.setDirtyCanvas(true, true);
      };

      const loadLinks = async (q) => {
        // No type filter: Version.entity accepts many types and a show may use several at once.
        const d = await get(
          `/fpt/entities?project_id=${projectId}&q=${encodeURIComponent(q || "")}`);
        linkIds = Object.fromEntries(d.items.map((x) => [x.label, x.id]));
        setOptions(link, d.items.map((x) => x.label));
        await loadTasks();
      };

      const loadProject = async () => {
        const d = await get("/fpt/projects");
        projectId = (d.items.find((x) => x.label === project.value) || {}).id || 0;
        setOptions(project, d.items.map((x) => x.label));
        // link_type is per project: one show hangs Versions off Shots, the next off Assets. Asking
        // the server is what lets two graphs in one ComfyUI target two shows that disagree.
        const prof = await get(`/fpt/profile?project_id=${projectId}`);
        linkType = prof.link_type || "Shot";
        link.tooltip = "What this Version belongs to — each option carries its own type.";
        search.tooltip = "Type to search across every entity type this project uses.";
        if (status) {
          const s = await get(`/fpt/statuses?project_id=${projectId}`);
          setOptions(status, s.items.map((x) => x.label));
        }
        await loadLinks(search.value);
      };

      // Type-ahead. Filtering is server-side (probe 017 `contains`), so this scales past the page size.
      let pending;
      const search = this.addWidget("text", "link_search", "", (v) => {
        clearTimeout(pending);
        pending = setTimeout(() => loadLinks(v), 200);
      });
      search.tooltip = `Type to search ${linkType}s by name.`;

      const wrap = (widget, after) => {
        const prev = widget.callback;
        widget.callback = function () {
          const r = prev?.apply(this, arguments);
          after();
          return r;
        };
      };
      wrap(project, loadProject);
      wrap(link, loadTasks);

      this.addWidget("button", "refresh from site", null, loadProject);
      loadProject();
    };
  },
});

// Fetch node. Same shape as the publish pickers, with one extra step: which media a Version can
// deliver is a property of that Version, not of the site (probe 021), so `source` is reloaded per
// pick and only ever offers tiers that resolve to something.
function fetchPickers(nodeType) {
  const onCreated = nodeType.prototype.onNodeCreated;
  nodeType.prototype.onNodeCreated = function () {
    onCreated?.apply(this, arguments);

    const w = (n) => this.widgets?.find((x) => x.name === n);
    const project = w("project"), link = w("link"), version = w("version");
    const source = w("source"), versionId = w("version_id");
    if (!project || !version || !versionId) return;

    let projectId = 0, linkType = "Shot", linkIds = {}, versionIds = {}, statusCodes = {};

    const select = w("select"), status = w("status"), order = w("order"), match = w("match");

    // What this rule lands on, and what made it — shown before anything runs. It calls the same
    // resolver the node uses, so the preview cannot disagree with the run.
    let panel = null;
    try {
      panel = ComfyWidgets.STRING(this, "resolves to",
        ["STRING", { multiline: true }], app).widget;
      panel.inputEl.readOnly = true;
      panel.inputEl.style.opacity = 0.75;
    } catch (e) { /* older frontend: the pickers still work without the panel */ }

    const loadSources = async () => {
      const id = versionIds[version.value] || 0;
      versionId.value = id;
      if (select && id && select.value !== "pinned id") select.value = "pinned id";
      const picked = link?.value || "";
      const q = new URLSearchParams({
        project_id: projectId, link_id: linkIds[picked] || 0,
        link_type: typeFromLabel(picked),
        select: select?.value || "", version_id: versionId.value || 0,
        status: statusCodes[status?.value] || "", order: order?.value || "",
        match: match?.value || "",
      });
      const d = await get(`/fpt/resolve?${q}`);
      if (panel) panel.value = d.summary || "nothing resolves yet";
      if (source) {
        source.options.values = ["auto"].concat(d.sources || []);
        if (!source.options.values.includes(source.value)) source.value = "auto";
      }
      app.graph.setDirtyCanvas(true, true);
    };

    const loadVersions = async (q) => {
      const d = await get(`/fpt/versions?project_id=${projectId}` +
        `&type=${encodeURIComponent(linkType)}&link_id=${linkIds[link?.value] || 0}` +
        `&q=${encodeURIComponent(q || "")}`);
      versionIds = Object.fromEntries(d.items.map((x) => [x.label, x.id]));
      setOptions(version, d.items.map((x) => x.label));
      await loadSources();
    };

    const loadLinks = async () => {
      const d = await get(`/fpt/entities?project_id=${projectId}`);
      linkIds = Object.fromEntries(d.items.map((x) => [x.label, x.id]));
      if (link) setOptions(link, d.items.map((x) => x.label));
      await loadVersions(search.value);
    };

    const loadProject = async () => {
      const d = await get("/fpt/projects");
      projectId = (d.items.find((x) => x.label === project.value) || {}).id || 0;
      setOptions(project, d.items.map((x) => x.label));
      const prof = await get(`/fpt/profile?project_id=${projectId}`);
      linkType = prof.link_type || "Shot";
      if (link) link.tooltip = "Narrow to one entity — each option carries its own type.";
      // Status codes are per project (probe 009), so the filter list follows the project too.
      if (status) {
        const d2 = await get(`/fpt/statuses?project_id=${projectId}`);
        statusCodes = Object.fromEntries(d2.items.map((x) => [x.label, x.id]));
        setOptions(status, d2.items.map((x) => x.label));
      }
      await loadLinks();
    };

    let pending;
    const search = this.addWidget("text", "version_search", "", (v) => {
      clearTimeout(pending);
      pending = setTimeout(() => loadVersions(v), 200);
    });

    const wrap = (widget, after) => {
      if (!widget) return;
      const prev = widget.callback;
      widget.callback = function () {
        const r = prev?.apply(this, arguments);
        after();
        return r;
      };
    };
    wrap(project, loadProject);
    wrap(link, () => loadVersions(search.value));
    wrap(version, loadSources);
    // Anything that changes which Version the rule lands on refreshes the panel.
    [select, status, order, match].forEach((x) => wrap(x, loadSources));

    this.addWidget("button", "refresh from site", null, loadProject);
    loadProject();
  };
}

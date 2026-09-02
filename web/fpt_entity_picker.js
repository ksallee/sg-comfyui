import { app } from "../../scripts/app.js";

const NONE = "";

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
    if (nodeData.name !== "FPTPublishVersion") return;

    const onCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      onCreated?.apply(this, arguments);

      const w = (n) => this.widgets?.find((x) => x.name === n);
      const project = w("project"), link = w("link"), task = w("task"), status = w("status");
      if (!project || !link) return;

      // project ids are not on the widgets - the combos carry labels, so the server resolves them.
      let projectId = 0;
      let linkType = "Shot";
      let linkIds = {};

      const loadTasks = async () => {
        const id = linkIds[link.value] || 0;
        const d = await get(`/fpt/tasks?type=${encodeURIComponent(linkType)}&id=${id}`);
        if (task) setOptions(task, d.items.map((x) => x.label));
        app.graph.setDirtyCanvas(true, true);
      };

      const loadLinks = async (q) => {
        const d = await get(
          `/fpt/entities?type=${encodeURIComponent(linkType)}&project_id=${projectId}` +
          `&q=${encodeURIComponent(q || "")}`);
        linkIds = Object.fromEntries(d.items.map((x) => [x.label, x.id]));
        setOptions(link, d.items.map((x) => x.label));
        await loadTasks();
      };

      const loadProject = async () => {
        const d = await get("/fpt/projects");
        projectId = (d.items.find((x) => x.label === project.value) || {}).id || 0;
        setOptions(project, d.items.map((x) => x.label));
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

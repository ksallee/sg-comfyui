import { app } from "../../scripts/app.js";
import { addPanel } from "./fpt_panel.js";

const NONE = "";
const ALL_TYPES = "(all types)";

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
function setOptions(widget, labels, keep) {
  widget.options.values = [NONE].concat(labels);
  const wanted = keep ?? widget.value;
  widget.value = widget.options.values.includes(wanted) ? wanted : NONE;
}

// There is deliberately no search box of our own. ComfyUI's combo dropdown already searches, and a
// second box beside it behaved differently — its filter is a plain substring over what is loaded, so
// `f` found Giraffe Ruler and `f r` did not. Narrowing is `link_type` instead: the list stays whole,
// and the editor searches it the way it searches everything else.

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
      const linkTypeW = w("link_type");
      // The publish panel needs the same re-measure hook as the fetch one: without it nothing ever
      // resized the node, so the box kept whatever height it had when the graph loaded.
      const relayout = () => {
        // Height only. computeSize() returns the node's MINIMUM for both dimensions, so passing it
        // whole snapped the width to that minimum every time the panel re-measured.
        this.setSize([this.size[0], this.computeSize()[1]]);
        app.graph.setDirtyCanvas(true, true);
      };
      const panel = addPanel(this, "Flow PT Publish", relayout);
      const preview = async () => {
        const q = new URLSearchParams({
          project: project.value || "", link_type: linkTypeW?.value || "",
          link: link.value || "", task: task?.value || "",
          code_template: w("code_template")?.value || "",
          output_name: w("output_name")?.value || "",
        });
        const d = await get(`/fpt/preview_code?${q}`);
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
        panel.show({ id: -1, code: d.code, link: d.link, task: d.task,
                     why: "this is what the next Run will create", ...extra });
      };
      const node = this;
      app.api.addEventListener("executed", ({ detail }) => {
        if (String(detail.node) !== String(node.id)) return;
        const rows = (detail.output && detail.output.published) || [];
        panel.clearLog();
        if (rows.length) {
          panel.show({ id: rows[0].id, code: rows[0].code, link: rows[0].link,
                       facts: rows[0].outputs && rows[0].outputs.length
                         ? [{ label: "fields", value: rows[0].outputs.join(", ") }] : [] });
        }
        const text = (detail.output && detail.output.text) || [];
        if (text.length) panel.log(text, rows.length > 0);
        // What the NEXT run would create, now that this one has taken a number.
        setTimeout(preview, 1200);
      });
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
        await preview();
        app.graph.setDirtyCanvas(true, true);
      };

      const loadLinks = async (picked) => {
        // The picked value again, not the widget's: it lags the callback.
        const chosen = picked ?? linkTypeW?.value;
        const t = (chosen && chosen !== ALL_TYPES) ? `&type=${encodeURIComponent(chosen)}` : "";
        const d = await get(`/fpt/entities?project_id=${projectId}${t}`);
        linkIds = Object.fromEntries(d.items.map((x) => [x.label, x.id]));
        setOptions(link, d.items.map((x) => x.label));
        await loadTasks();
      };

      const loadProject = async (picked) => {
        const d = await get("/fpt/projects");
        // Read AFTER the fetch: ComfyUI applies a saved workflow's widget values while this is in
        // flight, so a value captured before the await is stale and writing it back reverts the node
        // to the default project — which then needs a manual click or two to correct.
        const chosen = picked ?? project.value;
        projectId = (d.items.find((x) => x.label === chosen) || {}).id || 0;
        setOptions(project, d.items.map((x) => x.label), chosen);
        // link_type is per project: one show hangs Versions off Shots, the next off Assets. Asking
        // the server is what lets two graphs in one ComfyUI target two shows that disagree.
        const prof = await get(`/fpt/profile?project_id=${projectId}`);
        linkType = prof.link_type || "Shot";
        link.tooltip = "What this Version belongs to — each option carries its own type.";
        if (status) {
          const s = await get(`/fpt/statuses?project_id=${projectId}`);
          setOptions(status, s.items.map((x) => x.label));
        }
        if (linkTypeW) {
          const t = await get(`/fpt/link_types?project_id=${projectId}`);
          const vals = t.items.map((x) => x.label);
          linkTypeW.options.values = vals;
          if (!vals.includes(linkTypeW.value)) linkTypeW.value = ALL_TYPES;
        }
        await loadLinks();
        await preview();
      };

      // Type-ahead. Filtering is server-side (probe 017 `contains`), so this scales past the page size.

      const wrap = (widget, after) => {
        if (!widget) return;
        const prev = widget.callback;
        widget.callback = function (value) {
          const r = prev?.apply(this, arguments);
          // The widget's own `value` is not always assigned yet when the callback fires, so take the
          // new one from the argument. Reading widget.value here saw the PREVIOUS project, which is
          // why switching project needed a second click before the links matched it.
          after(value);
          return r;
        };
      };
      wrap(project, loadProject);
      wrap(linkTypeW, loadLinks);
      wrap(link, loadTasks);
      ["code_template", "output_name", "task"].forEach((n) => wrap(w(n), preview));

      this.addWidget("button", "refresh from site", null, loadProject);
      loadProject();
    };
  },
});

// Fetch node. The inputs are a rule, not an id, so the panel shows which Version the rule lands on
// and what made it — resolved by the node's own code, so the preview cannot disagree with the run.
function fetchPickers(nodeType) {
  const onCreated = nodeType.prototype.onNodeCreated;
  nodeType.prototype.onNodeCreated = function () {
    onCreated?.apply(this, arguments);

    const w = (n) => this.widgets?.find((x) => x.name === n);
    const project = w("project"), linkTypeW = w("link_type"), link = w("link"), task = w("task");
    const source = w("source"), statuses = w("statuses");
    if (!project || !link) return;

    let projectId = 0, linkIds = {};
    // The SG Filters box mirrors the pickers until someone edits it, then it is theirs. Comparing
    // against the last value we wrote is how we tell: no flag to keep in sync, no mode to explain.
    let mirrored = "";

    // The declared `filters` widget stays hidden for good and only carries the value: a widget can
    // only render where INPUT_TYPES puts it, which is above this panel, and it cannot be moved below
    // because widgets_values is positional. The editable box lives inside the panel instead, under
    // the readout it belongs to, where its height is ours to choose.
    const filterBox = w("filters");
    if (filterBox) filterBox.hidden = true;
    const relayout = () => {
      this.setSize([this.size[0], this.computeSize()[1]]);   // height only; see the note above
      app.graph.setDirtyCanvas(true, true);
    };

    const panel = addPanel(this, "Flow PT Fetch", relayout);
    panel.editor((text) => {
      if (filterBox) filterBox.value = text;
      refresh();
    });

    const refresh = async () => {
      const q = new URLSearchParams({
        project_id: projectId, project: project.value || "",
        link_type: linkTypeW?.value || "", link: link.value || "", task: task?.value || "",
        name_contains: w("name_contains")?.value || "",
        newest_by: w("newest_by")?.value || "",
        pin_version_id: w("pin_version_id")?.value || 0,
        // Only when it is an override. While the box is still mirroring, sending it back would let
        // its own (now stale) content win over the very fields it is meant to reflect.
        // String(): a workflow saved before this widget moved can land a number here, and a raw
        // .trim() on it takes the whole picker down.
        filters: String(w("filters")?.value ?? "").trim() === mirrored.trim()
          ? "" : String(w("filters")?.value ?? ""),
      });
      for (const s of String(statuses?.value || "").split(",")) {
        const t = s.trim();
        if (t) q.append("statuses", t);
      }
      const d = await get(`/fpt/resolve?${q}`);
      panel.show(d);
      const box = w("filters");
      if (box && d.filters && String(box.value ?? "").trim() === mirrored) {
        mirrored = JSON.stringify(d.filters, null, 1);
        box.value = mirrored;
      }
      panel.setFilterText(String(box?.value ?? ""));
      if (source) {
        source.options.values = ["auto"].concat(d.media || []);
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
      setOptions(link, d.items.map((x) => x.label));
      await loadTasks();
    };

    const loadProject = async (picked) => {
      const d = await get("/fpt/projects");
      const chosen = picked ?? project.value;   // after the await; the widget value lags
      projectId = (d.items.find((x) => x.label === chosen) || {}).id || 0;
      setOptions(project, d.items.map((x) => x.label), chosen);
      if (linkTypeW) {
        const t = await get(`/fpt/link_types?project_id=${projectId}`);
        const vals = t.items.map((x) => x.label);
        linkTypeW.options.values = vals;
        if (!vals.includes(linkTypeW.value)) linkTypeW.value = ALL_TYPES;
      }
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
    ["task", "name_contains", "statuses", "filters", "newest_by", "pin_version_id"].forEach((n) =>
      wrap(w(n), refresh));

    this.addWidget("button", "refresh from site", null, loadProject);
    loadProject();
  };
}

/* The SG sidebar tab: search a project's Versions and add them to the graph as SG Load nodes.
 *
 * The tab is drawn by `sidebar/`, built into `web/sidebar/sg_sidebar_app.js`. This file registers
 * the tab with ComfyUI, adds the node a tile asks for, and accepts a tile dropped on the canvas.
 */
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { call, restoreValue } from "./sg_dom_widgets.js";
import { mountSidebar, startProject, DRAG_TYPE, LOAD_NODE } from "./sidebar/sg_sidebar_app.js";

// The project picked last. A hidden setting: stored by ComfyUI with the user's settings, not shown in
// the Settings dialog.
const PROJECT_SETTING = "SG.Sidebar.Project";

// The tab's element is created by ComfyUI each time the tab opens. The sidebar is drawn once into
// this host and moved into each new element, so the search and the scroll position are kept.
let host = null;
let signedIn = false;
let unmount = null;

/** The visible middle of the canvas, in graph coordinates. */
function middle() {
  const [x, y, w, h] = app.canvas.ds.visible_area;
  return [x + w / 2, y + h / 2];
}

/** Adds an SG Load node at `pos`, set to the values a tile gave, the way a saved graph is restored. */
function addLoadNode(values, pos = middle()) {
  const node = window.LiteGraph.createNode(LOAD_NODE);
  if (!node) return;
  node.pos = pos;
  app.graph.add(node);
  for (const [name, value] of Object.entries(values)) {
    restoreValue(node.widgets?.find((w) => w.name === name), value);
  }
  app.graph.setDirtyCanvas(true, true);
}

function hasTile(event) {
  return !!event.dataTransfer?.types?.includes(DRAG_TYPE);
}

/** True for a drop on the graph rather than on the sidebar or a dialog. */
function overGraph(event) {
  const graph = app.canvasEl?.parentElement;
  return !!graph && graph.contains(event.target) && !host?.contains(event.target);
}

// Capture phase, ahead of ComfyUI's own drop handler, which opens dropped files.
document.addEventListener("dragover", (event) => {
  if (!hasTile(event) || !overGraph(event)) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = "copy";
}, true);

document.addEventListener("drop", (event) => {
  if (!hasTile(event) || !overGraph(event)) return;
  event.preventDefault();
  event.stopPropagation();
  addLoadNode(JSON.parse(event.dataTransfer.getData(DRAG_TYPE)),
              app.canvas.convertEventToCanvasOffset(event));
}, true);

/** Replaces what the tab shows with one sentence. */
function say(text) {
  const root = host.shadowRoot ?? host.attachShadow({ mode: "open" });
  const p = document.createElement("p");
  p.textContent = text;
  p.style.cssText = "margin: 0; padding: 12px; font-size: 13px; color: var(--descrip-text);";
  root.replaceChildren(p);
}

/** Draws the sidebar into `host`, or the sentence that says how to sign in. */
async function draw() {
  unmount?.();
  unmount = null;
  const [session, projects] = await Promise.all([call("/sg/session"), call("/sg/projects")]);
  signedIn = !!session.how && session.how !== "none";
  if (!signedIn) {
    say("Open Settings, then SG, and log in to search Versions.");
    return;
  }
  const settings = app.extensionManager.setting;
  unmount = mountSidebar(host, {
    // Absolute: RestClient builds each request with `new URL`, which refuses a bare path.
    relayUrl: new URL(api.apiURL("/sg/rest"), location.href).href,
    siteUrl: session.site || "",
    project: startProject(projects.items || [], Number(settings.get(PROJECT_SETTING) || 0),
                          projects.default || 0),
    dark: getComputedStyle(document.documentElement).colorScheme.includes("dark"),
    onAdd: (values) => addLoadNode(values),
    provenanceFields: async (projectId) =>
      (await call(`/sg/provenance_fields?project_id=${projectId}`)).items || [],
    onProjectChange: (project) => settings.set(PROJECT_SETTING, project.id),
  });
}

app.registerExtension({
  name: "sg.sidebar",
  settings: [{ id: PROJECT_SETTING, name: "SG sidebar project", type: "hidden", defaultValue: 0 }],
  setup() {
    app.extensionManager.registerSidebarTab({
      id: "sg-versions",
      icon: "pi pi-images",
      title: "SG",
      tooltip: "Search Flow Production Tracking Versions",
      type: "custom",
      render: (el) => {
        el.style.height = "100%";
        const first = !host;
        if (first) {
          host = document.createElement("div");
          host.style.height = "100%";
        }
        el.append(host);
        // Signed out last time: try again, the operator may have logged in since.
        if (first || !signedIn) draw();
      },
    });
  },
});

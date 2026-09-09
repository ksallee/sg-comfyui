// Load one saved graph, close every toast, hide the minimap, and frame the whole graph with room
// around it. Nothing is run. GRAPH is prepended: the JSON text of the workflow.
const pause = (ms) => wait(ms);
// The open workflow is marked modified by the harness's own setup, and loading over a modified
// one asks to save. Reset its change tracker so the load goes through without a dialog.
const closeAnyway = () => [...document.querySelectorAll("button")]
  .find((b) => /Close anyway/i.test(b.textContent))?.click();
const loading = app.loadGraphData(JSON.parse(GRAPH));
for (let i = 0; i < 20; i++) { await pause(250); closeAnyway(); }
await loading; await pause(4000); closeAnyway();
// A stock template names an example file this machine does not have; point every Load Image at
// a plate that exists, so the graph reads as a graph and not as a red node.
for (const n of app.graph.nodes.filter((n) => n.type === "LoadImage")) {
  const w = n.widgets?.find((x) => x.name === "image");
  if (w) { w.value = "sh010_plate_f0001.png"; w.callback?.(w.value); }
}
// The red badge is the validation of the first load, which a widget change does not clear.
for (const n of app.graph.nodes) n.has_errors = false;
app.canvas.setDirty(true, true);
// Toasts arrive on their own clock; keep closing them until the shot.
for (let i = 0; i < 10; i++) {
  await pause(400);
  document.querySelectorAll(".p-toast button, .p-toast [role=button]").forEach((b) => b.click());
}
// Toasts only: a generic Close matches the workflow tabs, and closing one empties the graph.
document.querySelectorAll(".p-toast-close-button").forEach((b) => b.click());
const mini = document.querySelector("[aria-label*='minimap' i], button[title*='minimap' i]");
if (mini && document.querySelector(".litegraph-minimap, [class*='minimap']")) mini.click();
await pause(500);
const ns = app.graph.nodes;
const x0 = Math.min(...ns.map(n => n.pos[0])) - 120, y0 = Math.min(...ns.map(n => n.pos[1])) - 140;
const x1 = Math.max(...ns.map(n => n.pos[0] + (n.size?.[0] || 260))) + 120;
const y1 = Math.max(...ns.map(n => n.pos[1] + (n.size?.[1] || 120))) + 120;
const cw = app.canvas.canvas.width, ch = app.canvas.canvas.height;
const s = Math.min(cw / (x1 - x0), ch / (y1 - y0), 1);
app.canvas.ds.state.scale = s;
app.canvas.ds.state.offset = [-x0 + ((cw / s) - (x1 - x0)) / 2, -y0 + ((ch / s) - (y1 - y0)) / 2];
app.canvas.setDirty(true, true); await pause(2500);
document.querySelectorAll(".p-toast-close-button").forEach((b) => b.click());
await pause(800);
return { nodes: ns.length, scale: s, toasts: document.querySelectorAll(".p-toast-message").length };

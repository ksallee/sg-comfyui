// Captures the example graph's top row alone, at device scale 2, with the editor chrome hidden, for
// the README hero. Nothing is run.
// Needs GRAPH prepended: the JSON text of the workflow.
// Needs a plate named sh010_plate_f0001.png in the instance's input directory.
// Crop the sidebar and the tab bar afterwards: 59 and 38 CSS pixels, times the scale.
//   { printf 'const GRAPH = %s;\n' "$(python3 -c 'import json; print(json.dumps(open("example_workflows/00_example.json").read()))')"; cat tools/drive_hero_shot.js; } > /tmp/hero.js
//   uv run --with playwright --python 3.11 python tools/qa_node.py --start --drive /tmp/hero.js --shot hero.png --scale 2 --viewport 1500x560
const pause = (ms) => wait(ms);
const closeAnyway = () => [...document.querySelectorAll("button")]
  .find((b) => /Close anyway/i.test(b.textContent))?.click();
const loading = app.loadGraphData(JSON.parse(GRAPH));
for (let i = 0; i < 20; i++) { await pause(250); closeAnyway(); }
await loading; await pause(4000); closeAnyway();
for (const n of app.graph.nodes.filter((n) => n.type === "LoadImage")) {
  const w = n.widgets?.find((x) => x.name === "image");
  if (w) { w.value = "sh010_plate_f0001.png"; w.callback?.(w.value); }
}
for (const n of app.graph.nodes) n.has_errors = false;
app.canvas.setDirty(true, true);
for (let i = 0; i < 10; i++) {
  await pause(400);
  document.querySelectorAll(".p-toast button, .p-toast [role=button]").forEach((b) => b.click());
}
document.querySelectorAll(".p-toast-close-button").forEach((b) => b.click());
const mini = document.querySelector("[aria-label*='minimap' i], button[title*='minimap' i]");
if (mini && document.querySelector(".litegraph-minimap, [class*='minimap']")) mini.click();
// Hide the chrome over the canvas: the body panels, the Run bar, the canvas controls.
const hidden = [];
for (const sel of ["#comfyui-body-top", "#comfyui-body-left", "#comfyui-body-right", "#comfyui-body-bottom",
                   ".actionbar", "[class*='actionbar']", "[data-testid='action-bar-card']",
                   "[class*='graph-canvas-menu']", "[class*='canvas-menu']",
                   "[class*='subgraph-breadcrumb']", ".comfyui-menu", ".p-buttongroup"]) {
  document.querySelectorAll(sel).forEach((e) => { hidden.push(sel); e.style.display = "none"; });
}
await pause(500);
const row = app.graph.nodes.filter((n) => !/Note/i.test(n.type) && n.pos[1] < 400);
const x0 = Math.min(...row.map(n => n.pos[0])) - 30, y0 = Math.min(...row.map(n => n.pos[1])) - 50;
const x1 = Math.max(...row.map(n => n.pos[0] + (n.size?.[0] || 260))) + 30;
const y1 = Math.max(...row.map(n => n.pos[1] + (n.size?.[1] || 120))) + 30;
// The sidebar and the tab bar overlay the canvas. Frame inside the area they leave.
const rect = (sel) => document.querySelector(sel)?.getBoundingClientRect() || { width: 0, height: 0 };
const sideW = rect("[class*='side-tool']").width, topH = rect("[class*='workflow-tabs']").height;
const cw = app.canvas.canvas.clientWidth - sideW, ch = app.canvas.canvas.clientHeight - topH;
const s = Math.min(cw / (x1 - x0), ch / (y1 - y0));
app.canvas.ds.state.scale = s;
app.canvas.ds.state.offset = [-x0 + sideW / s + ((cw / s) - (x1 - x0)) / 2, -y0 + topH / s + ((ch / s) - (y1 - y0)) / 2];
app.canvas.setDirty(true, true); await pause(2500);
document.querySelectorAll(".p-toast-close-button").forEach((b) => b.click());
await pause(800);
return { row: row.map(n => n.type), scale: s, sideW, topH, box: [x1 - x0, y1 - y0] };

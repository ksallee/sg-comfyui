// Runs one SG Load pinned to PIN, its image into a Preview and its mask through Convert Mask to
// Image into a second Preview, then frames the graph with room around it.
// Needs PIN prepended: the Version id to pin.
// Needs SOURCE prepended: a word from the source option to pick, or "".
//   { printf 'const PIN = 31995;\nconst SOURCE = "";\n'; cat tools/drive_load_shot.js; } > /tmp/load.js
//   uv run --with playwright --python 3.11 python tools/qa_node.py --start --repo . --drive /tmp/load.js --shot load.png
const pause = (ms) => wait(ms);
const seen = [];
app.graph.clear(); await pause(300);
const ld = LiteGraph.createNode("SGLoadVersion"); ld.pos = [60, 80]; app.graph.add(ld);
const w = (n) => ld.widgets.find(x => x.name === n);
w("pin_version_id").value = PIN; w("pin_version_id").callback?.(PIN);
const pv1 = LiteGraph.createNode("PreviewImage"); pv1.pos = [560, 80]; pv1.title = "image"; app.graph.add(pv1);
const m2i = LiteGraph.createNode("MaskToImage"); m2i.pos = [560, 560]; app.graph.add(m2i);
const pv2 = LiteGraph.createNode("PreviewImage"); pv2.pos = [860, 560]; pv2.title = "mask"; app.graph.add(pv2);
ld.connect(0, pv1, 0); ld.connect(2, m2i, 0); m2i.connect(0, pv2, 0);
app.canvas.setDirty(true, true); await pause(5000);
if (SOURCE) {
  for (let i = 0; i < 20 && !(w("source").options?.values || []).some(v => v.includes(SOURCE)); i++) await pause(500);
  const opt = (w("source").options?.values || []).find(v => v.includes(SOURCE));
  if (opt) { w("source").value = opt; w("source").callback?.(opt); await pause(4000); }
  seen.push("source: " + (opt || "not offered"));
}
await app.queuePrompt(0, 1);
for (let i = 0; i < 60; i++) { await pause(1000); if (pv1.imgs && pv1.imgs.length) break; }
await pause(3000);
const ns = app.graph.nodes;
const x0 = Math.min(...ns.map(n => n.pos[0])) - 100, y0 = Math.min(...ns.map(n => n.pos[1])) - 120;
const x1 = Math.max(...ns.map(n => n.pos[0] + (n.size?.[0] || 260))) + 100;
const y1 = Math.max(...ns.map(n => n.pos[1] + (n.size?.[1] || 120))) + 100;
const cw = app.canvas.canvas.width, ch = app.canvas.canvas.height;
const s = Math.min(cw / (x1 - x0), ch / (y1 - y0), 1);
app.canvas.ds.state.scale = s;
app.canvas.ds.state.offset = [-x0 + ((cw / s) - (x1 - x0)) / 2, -y0 + ((ch / s) - (y1 - y0)) / 2];
app.canvas.setDirty(true, true); await pause(1500);
// The run's "Job completed" toast arrives on its own clock and would otherwise be in the shot.
// Close it by its own control: a generic Close matches the workflow tabs, and closing one empties
// the graph.
for (let i = 0; i < 6; i++) {
  await pause(300);
  document.querySelectorAll(".p-toast-close-button").forEach((b) => b.click());
}
seen.push("images: " + (pv1.imgs?.length || 0) + " mask: " + (pv2.imgs?.length || 0));
seen.push("panel: " + (document.querySelector(".sg-panel .sg-body")?.innerText || "").replace(/\n/g, " | ").slice(0, 160));
return { steps: seen };

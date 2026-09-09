// SG Load on an RGBA Version, its mask wired through Convert Mask to Image into a Preview, run live.
const pause = (ms) => wait(ms);
const seen = [];
app.graph.clear(); await pause(300);
const ld = LiteGraph.createNode("SGLoadVersion"); ld.pos = [40, 80]; app.graph.add(ld);
const w = (n) => ld.widgets.find(x => x.name === n);
w("pin_version_id").value = 31995; w("pin_version_id").callback?.(31995);
const m2i = LiteGraph.createNode("MaskToImage"); m2i.pos = [520, 620]; app.graph.add(m2i);
const pv1 = LiteGraph.createNode("PreviewImage"); pv1.pos = [520, 80]; pv1.title = "image"; app.graph.add(pv1);
const pv2 = LiteGraph.createNode("PreviewImage"); pv2.pos = [820, 620]; pv2.title = "mask"; app.graph.add(pv2);
ld.connect(0, pv1, 0);
ld.connect(5, m2i, 0);
m2i.connect(0, pv2, 0);
app.canvas.setDirty(true, true); await pause(4000);
const ns = app.graph.nodes;
const x0 = Math.min(...ns.map(n => n.pos[0])) - 40, y0 = Math.min(...ns.map(n => n.pos[1])) - 40;
const x1 = Math.max(...ns.map(n => n.pos[0] + (n.size?.[0] || 260))) + 40;
const y1 = Math.max(...ns.map(n => n.pos[1] + (n.size?.[1] || 120))) + 40;
const s = Math.min(app.canvas.canvas.width / (x1 - x0), app.canvas.canvas.height / (y1 - y0), 1);
app.canvas.ds.state.scale = s; app.canvas.ds.state.offset = [-x0 + 20 / s, -y0 + 20 / s];
app.canvas.setDirty(true, true); await pause(800);
await app.queuePrompt(0, 1);
for (let i = 0; i < 60; i++) { await pause(1000);
  if (pv2.imgs && pv2.imgs.length) break; }
await pause(2500);
seen.push("mask preview images: " + (pv2.imgs ? pv2.imgs.length : 0));
seen.push("panel: " + (document.querySelector(".sg-panel .sg-body")?.innerText || "").replace(/\n/g, " | ").slice(0, 300));
return { steps: seen };

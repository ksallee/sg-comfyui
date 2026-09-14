// Captures SG Load resolving a Version from a rule, its image into a Preview, and its mask through
// Convert Mask to Image into a second Preview.
// Needs the sandbox project, Shot sh010, and an RGBA Version whose name contains rgba.
// `mask` is the third output.
//   tools/capture.py --drive tools/drive_clip_06_load_image_mask.js --out 06
await settle(300);
app.graph.clear();
const ld = LiteGraph.createNode("SGLoadVersion"); ld.pos = [40, 60]; app.graph.add(ld);
const pv1 = LiteGraph.createNode("PreviewImage"); pv1.pos = [560, 60]; pv1.title = "image";
app.graph.add(pv1);
const m2i = LiteGraph.createNode("MaskToImage"); m2i.pos = [560, 520]; app.graph.add(m2i);
const pv2 = LiteGraph.createNode("PreviewImage"); pv2.pos = [860, 520]; pv2.title = "mask";
app.graph.add(pv2);
ld.connect(0, pv1, 0);
ld.connect(2, m2i, 0);
m2i.connect(0, pv2, 0);

const w = (n) => ld.widgets.find((x) => x.name === n);
w("name_contains").value = "rgba";
w("project").value = "sg-comfyui Sandbox"; w("project").callback?.(w("project").value);
await pause(1200);
await frameAll(70);
await pause(400);

// Pick the link the way an operator does. The panel then names the Version the rule resolves to.
await pick("link", "sh010", "sh010");
await pause(1000);

await click(runButton(), 650);
for (let i = 0; i < 120; i++) {
  await pause(400);
  const q = await (await fetch("/queue")).json();
  if (i > 3 && !q.queue_running?.length && !q.queue_pending?.length) break;
}
for (let i = 0; i < 30 && !(pv1.imgs?.length && pv2.imgs?.length); i++) await pause(300);
await frameAll(70);
await pause(2200);

return {
  images: pv1.imgs?.length || 0,
  mask: pv2.imgs?.length || 0,
  panel: (document.querySelector(".sg-panel")?.innerText || "").replace(/\n/g, " | ").slice(0, 260),
};

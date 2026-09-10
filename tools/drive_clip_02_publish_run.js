// Captures Preview Image run on its own from the selection toolbox, then SG Publish run the same
// way, ending on the rows the Version left.
// Publishes one 512x512 frame to the sandbox project.
// Needs the sandbox project and Shot sh010.
//   tools/capture.py --drive tools/drive_clip_02_publish_run.js --out 02
await settle(300);
app.graph.clear();
const img = LiteGraph.createNode("EmptyImage");
img.pos = [40, 160];
app.graph.add(img);
for (const [k, v] of [["width", 512], ["height", 512], ["batch_size", 1], ["color", 3368601]]) {
  const x = img.widgets.find((w) => w.name === k);
  if (x) { x.value = v; x.callback?.(v); }
}
const prev = LiteGraph.createNode("PreviewImage");
prev.pos = [400, 160];
app.graph.add(prev);
const pub = LiteGraph.createNode("SGPublishVersion");
pub.pos = [720, 60];
app.graph.add(pub);
img.connect(0, prev, 0);
img.connect(0, pub, 0);

// A named link resolves on the site. The pickers stay closed here. Clip 1 is the one about picking.
// A picker draws the value it finds when it is built. Set both before the node is added.
const w = (n) => pub.widgets.find((x) => x.name === n);
w("link").value = "sh010 (Shot)";
w("root_name").value = "launch_clip";
w("note").value = "Recorded for the launch page.";
w("project").value = "sg-comfyui Sandbox"; w("project").callback?.(w("project").value);
await settleSize(pub);
await frameAll(60);
await pause(1600);

// One node at a time. Select it, then run up to it from the toolbox over it.
await runNode(prev, "Preview Image");
// The preview lands almost at once, so wait for the image itself rather than for the queue.
for (let i = 0; i < 80 && !(prev.imgs || []).length; i++) await pause(100);
await pause(1000);

await runNode(pub, "SG Publish");
await ranOut();
const panel = () => document.querySelector(".sg-panel")?.innerText || "";
for (let i = 0; i < 40 && !/last run/i.test(panel()); i++) await pause(300);
await settleSize(pub);
await frameAll(60);
await pause(2400);

return {
  link: w("link").value,
  panel: panel().replace(/\n/g, " | ").slice(0, 400),
  anchors: [...document.querySelectorAll("a.sg-a")].map((a) => `${a.textContent.trim()} -> ${a.href}`),
};

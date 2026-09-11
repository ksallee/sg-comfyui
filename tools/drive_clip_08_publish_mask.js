// Captures a mask read off a Version by SG Load and published with the frames by SG Publish.
// Needs the sandbox project, Shot sh010 with an RGBA Version whose name contains rgba, and Shot
// sbx_0020 with Task Roto. Publishes one frame and one Published File to the sandbox project.
// `mask` is SG Load's third output and SG Publish's third input.
//   tools/capture.py --drive tools/drive_clip_08_publish_mask.js --out 08
await settle(300);
app.graph.clear();
const ld = LiteGraph.createNode("SGLoadVersion"); ld.pos = [40, 120]; app.graph.add(ld);
// The frames are inverted between the two nodes, so the published still differs from the one read.
const inv = LiteGraph.createNode("ImageInvert"); inv.pos = [620, 120]; app.graph.add(inv);
const pub = LiteGraph.createNode("SGPublishVersion"); pub.pos = [900, 60]; app.graph.add(pub);
ld.connect(0, inv, 0);
inv.connect(0, pub, pub.findInputSlot("images"));
ld.connect(2, pub, pub.findInputSlot("mask"));

// Three nodes fill the width, and the editor's icon rail overlays the left of the canvas. Frame
// with room for the rail, then pan clear of it.
const frameClear = async () => {
  await frameAll(90);
  app.canvas.ds.state.offset[0] += 40;
  app.canvas.setDirty(true, true);
  await pause(400);
};

const lw = (n) => ld.widgets.find((x) => x.name === n);
lw("name_contains").value = "rgba";
lw("link").value = "sh010 (Shot)";
lw("project").value = "sg-comfyui Sandbox"; lw("project").callback?.(lw("project").value);

// A named link resolves on the site, so the pickers stay closed here. Clip 1 covers picking.
const w = (n) => pub.widgets.find((x) => x.name === n);
w("link").value = "sbx_0020 (Shot)";
w("task").value = "Roto";
w("root_name").value = "mask_roundtrip";
w("register_files").value = true;
w("note").value = "The alpha comes off the Version SG Load read.";
w("project").value = "sg-comfyui Sandbox"; w("project").callback?.(w("project").value);
await settleSize(pub);
await settleSize(ld);
await frameClear();
await pause(2200);

await runNode(pub, "SG Publish");
await ranOut();
// Two nodes draw a panel here. The one the Run wrote to is the one naming a last run.
const ran = () => [...document.querySelectorAll(".sg-panel")]
  .map((p) => p.innerText).find((t) => /last run/i.test(t)) || "";
for (let i = 0; i < 40 && !ran(); i++) await pause(300);
await settleSize(pub);
await frameClear();
await pause(2400);

return {
  mask_slot: pub.findInputSlot("mask"),
  published: ran().replace(/\n/g, " | ").slice(0, 400),
  anchors: [...document.querySelectorAll("a.sg-a")].map((a) => `${a.textContent.trim()} -> ${a.href}`)
};

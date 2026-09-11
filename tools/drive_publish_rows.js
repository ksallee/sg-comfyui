// Captures the publish panel before and after a Run, as rows: review, files in the format picked,
// paths.
// Needs the sandbox project and Shot sh010. Reads the site.
// Needs RUN prepended as true to publish a 2-frame EXR batch; without it the drive stops at the
// readout, which is the shot site/static/media/01_publish_before_run_exr.png.
//   (echo 'const RUN = true;'; cat tools/drive_publish_rows.js) | tools/qa_node.py --start \
//     --repo <checkout> --node SGPublishVersion --drive - --shot rows.png
const DO_RUN = typeof RUN !== "undefined" && RUN;
const pause = (ms) => wait(ms);
const seen = [];
const ctl = (label) => [...document.querySelectorAll(".sg-dom")]
  .find(d => (d.querySelector(".sg-lab")?.textContent || "").trim().toLowerCase() === label);
const pick = async (label, term, want) => {
  const c = ctl(label); if (!c) return seen.push(`${label}: no control`);
  c.querySelector("button")?.click(); await pause(1000);
  const inp = document.querySelector(".sg-pop-input");
  if (inp && term) { inp.value = term; inp.dispatchEvent(new Event("input", {bubbles:true})); }
  let hit = null;
  for (let i = 0; i < 25; i++) {
    await pause(400);
    hit = [...document.querySelectorAll('[role="option"]')]
      .find(r => (r.textContent || "").toLowerCase().includes(want.toLowerCase()));
    if (hit) break;
  }
  hit?.click(); await pause(1000);
};
app.graph.clear(); await pause(300);
const img = LiteGraph.createNode("EmptyImage"); img.pos = [40, 200]; app.graph.add(img);
img.widgets.find(w => w.name === "width").value = 512;
img.widgets.find(w => w.name === "height").value = 512;
img.widgets.find(w => w.name === "batch_size").value = 2;
img.widgets.find(w => w.name === "color").value = 3368601;
// The image node is as wide as the gap the editor gives it. Place the publish node clear of it,
// so the link between the two is drawn over the canvas.
const pub = LiteGraph.createNode("SGPublishVersion"); pub.pos = [540, 120]; app.graph.add(pub);
img.connect(0, pub, 0);
app.canvas.centerOnNode(pub); app.canvas.ds.state.scale = 0.95; app.canvas.setDirty(true, true);
await pause(1500);
await pick("project", "", "sandbox");
await pick("link", "sh010", "sh010");
const w = (n) => pub.widgets.find(x => x.name === n);
w("root_name").value = "verify_pub_rows"; w("root_name").callback?.(w("root_name").value);
w("register_files").value = true; w("register_files").callback?.(true);
w("format").value = "EXR 32-bit float"; w("format").callback?.(w("format").value);
w("note").value = "Panel rows.";
app.canvas.setDirty(true, true); await pause(6000);
seen.push("before: " + (document.querySelector(".sg-panel .sg-body")?.innerText || "").replace(/\n/g, " | ").slice(0, 400));
if (DO_RUN) {
  await app.queuePrompt(0, 1);
  for (let i = 0; i < 90; i++) { await pause(1000);
    if ((document.querySelector(".sg-panel")?.innerText || "").includes("last run")) break; }
  await pause(6000);
  seen.push("after: " + (document.querySelector(".sg-panel .sg-body")?.innerText || "").replace(/\n/g, " | ").slice(0, 500));
}
return { steps: seen };

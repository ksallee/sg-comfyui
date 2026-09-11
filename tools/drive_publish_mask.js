// Publishes a two-frame batch with a mask wired, and reads the panel before and after the Run.
// Needs the sandbox project, Shot sbx_0020 and Task Roto. Reads the site.
// Needs RUN prepended as true to queue the publish; without it the drive stops at the readout.
//   (echo 'const RUN = true;'; cat tools/drive_publish_mask.js) | tools/qa_node.py --start \
//     --repo <checkout> --drive - --shot out.png
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
const toasts = () => document.querySelectorAll(".p-toast-close-button").forEach((b) => b.click());

app.graph.clear(); await pause(300);
const img = LiteGraph.createNode("EmptyImage"); img.pos = [40, 80]; app.graph.add(img);
img.widgets.find(w => w.name === "width").value = 256;
img.widgets.find(w => w.name === "height").value = 256;
img.widgets.find(w => w.name === "batch_size").value = 2;
img.widgets.find(w => w.name === "color").value = 3368601;
// 0.25 in the mask is 0.75 in the alpha, which tells the two apart in the written file.
const msk = LiteGraph.createNode("SolidMask"); msk.pos = [40, 330]; app.graph.add(msk);
msk.widgets.find(w => w.name === "value").value = 0.25;
msk.widgets.find(w => w.name === "width").value = 256;
msk.widgets.find(w => w.name === "height").value = 256;
const pub = LiteGraph.createNode("SGPublishVersion"); pub.pos = [460, 60]; app.graph.add(pub);
img.connect(0, pub, pub.findInputSlot("images"));
msk.connect(0, pub, pub.findInputSlot("mask"));
seen.push(`mask slot: ${pub.findInputSlot("mask")}`);
seen.push(`mask link: ${pub.inputs[pub.findInputSlot("mask")]?.link !== null}`);
await pause(1500);
await pick("project", "", "sandbox");
await pick("link", "sbx_0020", "sbx_0020");
await pick("task", "roto", "roto");
const w = (n) => pub.widgets.find(x => x.name === n);
w("root_name").value = "mask_check"; w("root_name").callback?.(w("root_name").value);
w("register_files").value = true; w("register_files").callback?.(true);
w("note").value = "A mask wired into the publish node.";
app.canvas.setDirty(true, true);
await pause(6000);
// The capture is the node and its readout, so the Run bar is out of the frame.
const runbar = [...document.querySelectorAll("button")]
  .find((b) => /^\s*Run\s*$/i.test(b.textContent || ""))?.closest("div[class*=action], .p-panel");
if (runbar) runbar.style.display = "none";
const fit = () => {
  const [nw, nh] = pub.size, cw = app.canvas.canvas.width, ch = app.canvas.canvas.height;
  const s = Math.min(cw / (nw + 620), ch / (nh + 200), 1);
  app.canvas.ds.state.scale = s;
  app.canvas.ds.state.offset = [-img.pos[0] + 60, -pub.pos[1] + ((ch / s) - nh) / 2 + 20];
  app.canvas.setDirty(true, true);
};
fit();
for (let i = 0; i < 6; i++) { await pause(400); toasts(); }
fit();
const body = () => (document.querySelector(".sg-panel .sg-body")?.innerText || "")
  .replace(/\n/g, " | ");
seen.push(`before: ${body().slice(0, 400)}`);

if (DO_RUN) {
  let refused = "";
  app.api.addEventListener("execution_error",
                           ({ detail }) => { refused = detail.exception_message || ""; });
  await app.queuePrompt(0, 1);
  for (let i = 0; i < 90; i++) {
    await pause(1000);
    if (refused || (document.querySelector(".sg-panel")?.innerText || "").includes("last run")) break;
  }
  await pause(5000);
  seen.push(`refused: ${refused.slice(0, 400)}`);
  seen.push(`after: ${body().slice(0, 800)}`);
  for (let i = 0; i < 4; i++) { await pause(300); toasts(); }
  fit();
  await pause(1200);
}
return { steps: seen };

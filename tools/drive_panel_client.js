// Checks the publish panel's client row, and what it says about a storage root this machine cannot
// write to.
// Needs the sandbox project and Shot sh010. Reads the site.
// Needs RUN prepended as true to queue the publish; without it the drive stops at the readout.
// Needs NO_FILES prepended as true to publish review media only, with no storage root in use.
//   (echo 'const RUN = true;'; cat tools/drive_panel_client.js) | tools/qa_node.py --start \
//     --repo <checkout> --drive - --shot out.png
const DO_RUN = typeof RUN !== "undefined" && RUN;
const FILES = typeof NO_FILES === "undefined" || !NO_FILES;
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
const img = LiteGraph.createNode("EmptyImage"); img.pos = [40, 200]; app.graph.add(img);
img.widgets.find(w => w.name === "width").value = 256;
img.widgets.find(w => w.name === "height").value = 256;
// Two frames are a sequence, which needs files. Review media on its own is one frame.
img.widgets.find(w => w.name === "batch_size").value = FILES ? 2 : 1;
const pub = LiteGraph.createNode("SGPublishVersion"); pub.pos = [420, 60]; app.graph.add(pub);
img.connect(0, pub, 0);
await pause(1500);
await pick("project", "", "sandbox");
await pick("link", "sh010", "sh010");
const w = (n) => pub.widgets.find(x => x.name === n);
w("root_name").value = "verify_panel_client"; w("root_name").callback?.(w("root_name").value);
w("register_files").value = FILES; w("register_files").callback?.(FILES);
w("note").value = "The client row, and a root that cannot be written to.";
await pause(6000);
// The concepts are inside the node's advanced fold.
[...document.querySelectorAll("button, .p-button")]
  .find((b) => /Show advanced inputs/i.test(b.textContent || ""))?.click();
await pause(1200);
// The capture is a state, not a run, so the Run bar is out of the frame.
const runbar = [...document.querySelectorAll("button")]
  .find((b) => /^\s*Run\s*$/i.test(b.textContent || ""))?.closest("div[class*=action], .p-panel");
if (runbar) runbar.style.display = "none";
// The node, framed with room around it. What is read before a Run is on its panel.
const fit = () => {
  const [nw, nh] = pub.size, cw = app.canvas.canvas.width, ch = app.canvas.canvas.height;
  const s = Math.min(cw / (nw + 260), ch / (nh + 160), 1);
  app.canvas.ds.state.scale = s;
  app.canvas.ds.state.offset = [-pub.pos[0] + ((cw / s) - nw) / 2,
                                -pub.pos[1] + ((ch / s) - nh) / 2 + 20];
  app.canvas.setDirty(true, true);
};
fit();
for (let i = 0; i < 6; i++) { await pause(400); toasts(); }
fit();
await pause(1200);

const text = (s) => (document.querySelector(s)?.innerText || "").trim();
const rowOf = (key) => [...document.querySelectorAll(".sg-more .sg-row")]
  .filter((r) => (r.querySelector(".sg-k")?.textContent || "").trim() === key)
  .map((r) => (r.querySelector(".sg-v")?.textContent || "").trim())[0] || "";
seen.push(`generator: ${rowOf("generator")}`);
seen.push(`alert: ${text(".sg-alert")}`);
seen.push(`state: ${text(".sg-state")}`);
seen.push(`panel: ${text(".sg-panel .sg-body").replace(/\n/g, " | ").slice(0, 400)}`);

if (DO_RUN) {
  // A refused publish does not reach `executed`, so the sentence arrives as an execution error.
  let refused = "";
  app.api.addEventListener("execution_error",
                           ({ detail }) => { refused = detail.exception_message || ""; });
  await app.queuePrompt(0, 1);
  for (let i = 0; i < 60; i++) {
    await pause(1000);
    if (refused || text(".sg-panel").includes("last run")) break;
  }
  await pause(4000);
  seen.push(`refused: ${refused.slice(0, 400)}`);
  seen.push(`ran: ${text(".sg-panel .sg-body").replace(/\n/g, " | ").slice(0, 600)}`);
  toasts();
}
return { steps: seen };

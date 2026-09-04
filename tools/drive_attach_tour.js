// "Attach it to any workflow" — the actual feature, as a recording.
// An existing graph is already on the canvas; we add the publish node to it, connect it, fill it in,
// run it, and read back what it wrote. Deliberately paced: this is watched, not asserted on.
const pause = (ms) => wait(ms);
const seen = [];
const frame = async (node, scale = 0.85) => {           // centre and zoom, so nothing sits half off-screen
  app.canvas.centerOnNode(node);
  app.canvas.setZoom ? app.canvas.setZoom(scale) : (app.canvas.ds.state.scale = scale);
  app.canvas.setDirty(true, true); await pause(500);
};
const type = async (inp, text, ms = 45) => {            // faster than a human, slow enough to read
  for (const ch of text) { inp.value += ch; inp.dispatchEvent(new Event("input", {bubbles:true})); await pause(ms); }
};
const ctl = (label) => [...document.querySelectorAll(".fpt-dom")]
  .find(d => (d.querySelector(".fpt-lab")?.textContent || "").trim().toLowerCase() === label);
// Pick the row that actually says `want`, never rows[0]: the list is fetched per keystroke and the
// unfiltered set is on screen until the filtered one lands, so position is a race and text is not.
const pick = async (label, term, want) => {
  const c = ctl(label); if (!c) return seen.push(`${label}: no control`);
  c.querySelector("button")?.click(); await pause(1200);
  const inp = document.querySelector(".fpt-pop-input");
  if (inp && term) { await type(inp, term); }
  let rows = [], hit = null;
  for (let i = 0; i < 25; i++) {                       // wait for the row we asked for to appear
    await pause(400);
    rows = [...document.querySelectorAll('[role="option"]')];
    hit = rows.find(r => (r.textContent || "").toLowerCase().includes(want.toLowerCase()));
    if (hit) break;
  }
  seen.push(`${label}: ${rows.length} option(s), matched ${want}: ${!!hit}`);
  (hit || rows[0])?.click(); await pause(1100);
};

// 1. somebody's existing workflow, with no Flow PT in it at all
app.graph.clear(); await pause(400);
const load = LiteGraph.createNode("LoadImage");   load.pos = [80, 200];  app.graph.add(load);
const prev = LiteGraph.createNode("PreviewImage"); prev.pos = [560, 200]; app.graph.add(prev);
load.widgets.find(w => w.name === "image").value = "sh010_plate_f0001.png";
load.connect(0, prev, 0);
app.canvas.setDirty(true, true); await pause(1400);
seen.push("existing graph: " + app.graph.nodes.map(n => n.type).join(" -> "));

// 2. add ours to it
const pub = LiteGraph.createNode("FPTPublishVersion"); pub.pos = [560, 520]; app.graph.add(pub);
app.canvas.setDirty(true, true); await pause(1200);
await frame(pub, 0.8);

// 3. one wire is the whole integration
load.connect(0, pub, 0);
app.canvas.setDirty(true, true); await pause(1600);
seen.push("connected LoadImage.IMAGE -> FPTPublishVersion.images");

// 4. say where it goes
await pick("project", "", "sandbox");
await pick("link", "sh010", "sh010");
const w = (n) => pub.widgets.find(x => x.name === n);
if (w("output_name")) { w("output_name").value = "uidemo"; }
if (w("note")) { w("note").value = "Added to an existing graph and published, for the README recording."; }
app.canvas.setDirty(true, true); await pause(1200);

// 5. run it for real
// Wait for the RUN, not merely for a link: `latest` is already on screen from the preview, so
// polling for any anchor would return before anything was published.
const before = (document.querySelector(".fpt-log")?.textContent || "") + document.body.innerText.length;
await app.queuePrompt(0, 1);
seen.push("queued");
for (let i = 0; i < 90; i++) {
  await pause(1000);
  if (/-> Version \d+/.test(document.body.innerText)) break;   // the node's own run log
}
await pause(4000);
seen.push("anchors: " + [...document.querySelectorAll("a.fpt-a")]
  .map(a => `${a.textContent.trim().slice(0,40)} -> ${a.href.slice(0,58)}`).join("  |  "));
await pause(2000);
return { steps: seen };

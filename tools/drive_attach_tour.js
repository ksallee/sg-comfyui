// Records the publish node being added to an existing graph, wired, filled in, run, and read back.
// Needs the sandbox project, Shot sh010, and a plate named sh010_plate_f0001.png in the instance's
// input directory. Publishes one Version.
// Paced for watching, not for asserting on: the pauses are long.
//   tools/qa_node.py --start --drive tools/drive_attach_tour.js --video attach.webm
const pause = (ms) => wait(ms);
const seen = [];
const frame = async (node, scale = 0.85) => {           // centre and zoom, so no node is half off-screen
  app.canvas.centerOnNode(node);
  app.canvas.setZoom ? app.canvas.setZoom(scale) : (app.canvas.ds.state.scale = scale);
  app.canvas.setDirty(true, true); await pause(700);
};
// Fit the graph before zooming in, so the graph the node joins is on screen first.
const fitAll = async () => {
  const ns = app.graph.nodes;
  const x0 = Math.min(...ns.map(n => n.pos[0])) - 60, y0 = Math.min(...ns.map(n => n.pos[1])) - 60;
  const x1 = Math.max(...ns.map(n => n.pos[0] + (n.size?.[0] || 260))) + 60;
  const y1 = Math.max(...ns.map(n => n.pos[1] + (n.size?.[1] || 120))) + 60;
  if (app.canvas.animateToBounds) { app.canvas.animateToBounds([x0, y0, x1 - x0, y1 - y0]); }
  else {
    const s = Math.min(app.canvas.canvas.width / (x1 - x0), app.canvas.canvas.height / (y1 - y0), 1);
    app.canvas.ds.state.scale = s;
    app.canvas.ds.state.offset = [-x0 + 40 / s, -y0 + 40 / s];
  }
  app.canvas.setDirty(true, true); await pause(900);
};
const type = async (inp, text, ms = 45) => {            // faster than a human, slow enough to read
  for (const ch of text) { inp.value += ch; inp.dispatchEvent(new Event("input", {bubbles:true})); await pause(ms); }
};
const ctl = (label) => [...document.querySelectorAll(".sg-dom")]
  .find(d => (d.querySelector(".sg-lab")?.textContent || "").trim().toLowerCase() === label);
// Match the row by text, not by position: the list is fetched per keystroke and the unfiltered set
// is on screen until the filtered one is drawn.
const pick = async (label, term, want) => {
  const c = ctl(label); if (!c) return seen.push(`${label}: no control`);
  c.querySelector("button")?.click(); await pause(1200);
  const inp = document.querySelector(".sg-pop-input");
  if (inp && term) { await type(inp, term); }
  let rows = [], hit = null;
  for (let i = 0; i < 25; i++) {                       // wait for the requested row
    await pause(400);
    rows = [...document.querySelectorAll('[role="option"]')];
    hit = rows.find(r => (r.textContent || "").toLowerCase().includes(want.toLowerCase()));
    if (hit) break;
  }
  seen.push(`${label}: ${rows.length} option(s), matched ${want}: ${!!hit}`);
  (hit || rows[0])?.click(); await pause(1100);
};

// 1. an existing workflow with no SG node in it
app.graph.clear(); await pause(400);
const load = LiteGraph.createNode("LoadImage");   load.pos = [80, 200];  app.graph.add(load);
const prev = LiteGraph.createNode("PreviewImage"); prev.pos = [560, 200]; app.graph.add(prev);
load.widgets.find(w => w.name === "image").value = "sh010_plate_f0001.png";
load.connect(0, prev, 0);
app.canvas.setDirty(true, true); await pause(1400);
seen.push("existing graph: " + app.graph.nodes.map(n => n.type).join(" -> "));

// 2. add the publish node, framed wide so the graph it joins stays on screen
const pub = LiteGraph.createNode("SGPublishVersion"); pub.pos = [560, 520]; app.graph.add(pub);
app.canvas.setDirty(true, true); await pause(1600);
await fitAll(); await pause(1400);

// 3. one wire, still framed wide
load.connect(0, pub, 0);
app.canvas.setDirty(true, true); await pause(2400);
seen.push("connected LoadImage.IMAGE -> SGPublishVersion.images");

// 4. zoom in and fill the node in
await frame(pub, 0.85);

// 5. set where it publishes
await pick("project", "", "sandbox");
await pick("link", "sh010", "sh010");
const w = (n) => pub.widgets.find(x => x.name === n);
if (w("note")) { w("note").value = "Added to an existing graph and published, for the README recording."; }
app.canvas.setDirty(true, true); await pause(1200);

// 6. run it
await app.queuePrompt(0, 1);
seen.push("queued");
// Wait for the run, not for a link: `latest` is on screen from the preview, so polling for any
// anchor would return before anything was published.
for (let i = 0; i < 90; i++) {
  await pause(1000);
  if (/-> Version \d+/.test(document.body.innerText)) break;   // the node's own run log
}
await pause(4000);
seen.push("anchors: " + [...document.querySelectorAll("a.sg-a")]
  .map(a => `${a.textContent.trim().slice(0,40)} -> ${a.href.slice(0,58)}`).join("  |  "));
await pause(2000);
return { steps: seen };

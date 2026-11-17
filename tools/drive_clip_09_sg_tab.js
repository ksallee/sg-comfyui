// Captures the SG tab: a search, a Version's provenance and lineage, Add to graph, a run, and a drag.
// Needs the sandbox project with the sh010_concept and sh010_style Versions, whose lineage is
// several levels deep.
//   uv run --with playwright --python 3.11 python tools/capture.py \
//     --drive tools/drive_clip_09_sg_tab.js --out ~/Desktop/clips/09_sg_tab --viewport 1440x810
const SEARCH = "sh010_concept";
const OPEN = "sh010_concept_v005";

// One caption at the bottom of the frame, for a clip watched with the sound off.
const CAPTION = document.createElement("div");
CAPTION.style.cssText = "position:fixed;left:50%;bottom:28px;transform:translateX(-50%);"
  + "z-index:2147483646;pointer-events:none;padding:10px 18px;border-radius:10px;"
  + "background:rgba(10,10,12,.82);color:#fff;font:600 19px/1.3 Inter,system-ui,sans-serif;"
  + "letter-spacing:.01em;box-shadow:0 6px 24px rgba(0,0,0,.4);transition:opacity .25s";
document.body.appendChild(CAPTION);
const caption = async (text, ms = 300) => {
  CAPTION.style.opacity = "0";
  await pause(250);
  CAPTION.textContent = text;
  CAPTION.style.opacity = text ? "1" : "0";
  await pause(ms);
};

// The tab is drawn in a shadow root.
const tabRoot = () => [...document.querySelectorAll("div")]
  .find((d) => d.shadowRoot?.querySelector(".sg-sidebar"))?.shadowRoot;
const $t = (sel) => tabRoot()?.querySelector(sel);
const $$t = (sel) => [...(tabRoot()?.querySelectorAll(sel) || [])];
const byText = (sel, text) => $$t(sel).find((e) => (e.textContent || "").trim().startsWith(text));
const until = async (fn, tries = 60) => {
  for (let i = 0; i < tries; i++) { const v = fn(); if (v) return v; await pause(250); }
  return null;
};

// Frames a box of graph coordinates in the part of the canvas the sidebar leaves visible.
// The kit's frameAll centres on the canvas element, which runs under the sidebar.
const frameBox = async (x0, y0, x1, y1, pad = 70) => {
  const r = app.canvasEl.getBoundingClientRect();
  const left = Math.max(0, (tabRoot()?.host.getBoundingClientRect().right || r.left) - r.left);
  const vw = r.width - left, vh = r.height;
  x0 -= pad; y0 -= pad + 40; x1 += pad; y1 += pad;
  const sc = Math.min(vw / (x1 - x0), vh / (y1 - y0), 1);
  app.canvas.ds.state.scale = sc;
  app.canvas.ds.state.offset = [-x0 + left / sc + (vw / sc - (x1 - x0)) / 2,
                                -y0 + (vh / sc - (y1 - y0)) / 2];
  app.canvas.setDirty(true, true);
  await pause(500);
};
const bounds = () => {
  const ns = app.graph.nodes;
  return [Math.min(...ns.map((n) => n.pos[0])), Math.min(...ns.map((n) => n.pos[1])),
          Math.max(...ns.map((n) => n.pos[0] + (n.size?.[0] || 260))),
          Math.max(...ns.map((n) => n.pos[1] + (n.size?.[1] || 120)))];
};
// The client point a graph point is drawn at.
const toClient = (gx, gy) => {
  const r = app.canvasEl.getBoundingClientRect(), d = app.canvas.ds.state;
  return [r.left + (gx + d.offset[0]) * d.scale, r.top + (gy + d.offset[1]) * d.scale];
};

// A tile dragged to x, y on the canvas: the pointer and a ghost of the thumbnail move together.
const dragTo = async (tile, x, y, ms = 1300) => {
  const [x0, y0] = aim(tile.querySelector("img") || tile);
  await move(x0, y0, 700);
  await press();
  const dt = new DataTransfer();
  tile.dispatchEvent(new DragEvent("dragstart", { bubbles: true, composed: true, dataTransfer: dt }));
  const img = tile.querySelector("img");
  const ghost = document.createElement("img");
  ghost.src = img?.src || "";
  ghost.style.cssText = "position:fixed;left:0;top:0;width:150px;border-radius:8px;opacity:.85;"
    + "z-index:2147483645;pointer-events:none;box-shadow:0 8px 28px rgba(0,0,0,.5)";
  document.body.appendChild(ghost);
  const t0 = performance.now();
  for (;;) {
    const t = Math.min(1, (performance.now() - t0) / ms);
    const e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    const px = x0 + (x - x0) * e, py = y0 + (y - y0) * e;
    at(px, py);
    ghost.style.transform = `translate(${px - 60}px,${py - 30}px)`;
    await paint();
    if (t >= 1) break;
  }
  const canvas = app.canvasEl;
  const at_ = { bubbles: true, cancelable: true, composed: true, dataTransfer: dt, clientX: x, clientY: y };
  canvas.dispatchEvent(new DragEvent("dragover", at_));
  canvas.dispatchEvent(new DragEvent("drop", at_));
  ghost.remove();
  await pause(900);
};

// The canvas: a Preview Image on the right, waiting for a Version.
app.graph.clear();
const preview = LiteGraph.createNode("PreviewImage");
preview.pos = [640, 80];
preview.size = [420, 340];
app.graph.add(preview);
app.canvas.ds.state.scale = 0.9;
app.canvas.ds.state.offset = [80, 40];
await settle(400);

// Open the tab on the sandbox project.
const projects = await (await fetch("/sg/projects")).json();
const sandbox = projects.items.find((p) => p.label === "sg-comfyui Sandbox");
await app.extensionManager.setting.set("SG.Sidebar.Project", sandbox.id);
await caption("SG tab: your Flow Production Tracking Versions, inside ComfyUI", 600);
await click(document.querySelector("button:has(.pi-images)"), 900);
await until(() => $t("[data-slot=entity-card-name]"));
await pause(1500);

await caption("Search by name. Filter by status, artist, link, Task.", 300);
const search = $t("input[type=search]");
await click(search, 700);
await type(search, SEARCH, 70);
await until(() => byText("[data-slot=entity-card-name]", OPEN));
await pause(2200);

await caption("Click a Version: its fields, its provenance…", 300);
await click(byText("[data-slot=entity-card-name]", OPEN), 800);
await until(() => byText("h4", "Provenance"));
await pause(2200);
await scrollTo(byText("h4", "Provenance"), 1600);
await pause(1600);

await caption("…and its lineage: every Version it was generated from.", 300);
await scrollTo(byText("h4", "Lineage"), 1600);
await until(() => $t("ul button"));
await pause(2600);
const source = $$t("ul button")[0];
await click(source, 800);
await pause(2200);
await click(byText("button", "Back"), 700);
await pause(1200);

await caption("Add it to the graph: an SG Load pinned to that Version.", 300);
await click(byText("button", "Add to graph"), 800);
const load = await until(() => app.graph.nodes.find((n) => n.type === "SGLoadVersion"));
load.pos = [80, 80];
load.connect(0, preview, 0);
await pause(600);
await frameBox(...bounds());
await pause(2600);

await caption("Run it.", 200);
await click(runButton(), 700);
for (let i = 0; i < 120; i++) {
  await pause(400);
  const q = await (await fetch("/queue")).json();
  if (i > 3 && !q.queue_running?.length && !q.queue_pending?.length) break;
}
for (let i = 0; i < 30 && !preview.imgs?.length; i++) await pause(300);
await pause(2800);

await caption("Or drag any Version straight onto the canvas.", 300);
await click(byText("button", "Versions"), 700);
await pause(1200);
// The empty space right of the Preview, where the tile lands.
const spot = [preview.pos[0] + preview.size[0] + 140, preview.pos[1]];
await frameBox(preview.pos[0], spot[1], spot[0] + 400, spot[1] + 640);
const tiles = $$t("[draggable=true]");
// The first tile is a Version other than the one added above.
await dragTo(tiles[0], ...toClient(spot[0] + 20, spot[1] + 20));
await pause(1200);
const dropped = app.graph.nodes.find((n) => n.type === "SGLoadVersion" && n !== load);
if (dropped) {
  await frameBox(preview.pos[0], preview.pos[1], dropped.pos[0] + (dropped.size?.[0] || 380),
                 dropped.pos[1] + (dropped.size?.[1] || 600));
}
await pause(2400);

await caption("sg-comfyui 1.0.0 · Free, open source, MIT", 300);
await pause(3200);

return {
  loads: app.graph.nodes.filter((n) => n.type === "SGLoadVersion").map((n) =>
    n.widgets.find((w) => w.name === "pin_version_id")?.value),
  previewed: preview.imgs?.length || 0,
};

// Captures SG Load reading a movie Version into Save Video, then a pinned Load refusing a batch
// over the budget.
// Needs Version 31993 on the sandbox project.
// Answers /sg/resolve here for the refusal: no plate on this site is large enough to be refused, and
// the budget is a profile value.
//   tools/capture.py --drive tools/drive_clip_07_load_movie_budget.js --out 07
const MOVIE = 31993;

await settle(300);
app.graph.clear();
const ld = LiteGraph.createNode("SGLoadVersion"); ld.pos = [40, 60]; app.graph.add(ld);
const sv = LiteGraph.createNode("SaveVideo"); sv.pos = [580, 60]; app.graph.add(sv);
ld.connect(1, sv, 0);
const w = (n) => ld.widgets.find((x) => x.name === n);
w("pin_version_id").value = MOVIE; w("pin_version_id").callback?.(MOVIE);
await pause(1600);
await frameAll(70);
await pause(1400);

await click(runButton(), 650);
for (let i = 0; i < 120; i++) {
  await pause(400);
  const q = await (await fetch("/queue")).json();
  if (i > 3 && !q.queue_running?.length && !q.queue_pending?.length) break;
}
await pause(1400);
const saved = (document.querySelector(".sg-panel")?.innerText || "")
  .replace(/\n/g, " | ").slice(0, 240);

// A 4K plate of 120 frames, pinned. The node says how many frames fit before anything is run.
const real = window.fetch.bind(window);
const RESOLVE = {
  id: 31875, code: "chr_010_comp_v006", why: "pinned by id",
  status: { code: "rev", label: "Pending Review", rgb: "149,227,167", icon: "" },
  media: ["Rendered Image · chr_010_comp_v006.%04d.exr #7101"],
  image_label: "Rendered Image — chr_010_comp_v006.%04d.exr, 120 frames",
  video_label: "the frames at 25 fps, from the Version",
  frames: { first: 1, last: 120, count: 120 },
  batch: { width: 3840, height: 2160, fits: 43, gib: "4" },
  format: "EXR 32-bit float, RGB, 3840x2160, 120 frames",
  colour_space: "ACEScg",
  link: "Shot chr_010", task: "", facts: [], provenance: "generated", generated_from: [],
};
window.fetch = (url, opts) => /\/sg\/resolve/.test(String(url?.url ?? url))
  ? Promise.resolve(new Response(JSON.stringify(RESOLVE),
      { headers: { "Content-Type": "application/json" } }))
  : real(url, opts);
w("pin_version_id").value = 31875; w("pin_version_id").callback?.(31875);
for (let i = 0; i < 40 && !document.querySelector(".sg-alert"); i++) await pause(200);
await frameNode(ld, 0.9);
await pause(2200);

return {
  saved,
  alert: document.querySelector(".sg-alert")?.textContent.trim() || "",
};

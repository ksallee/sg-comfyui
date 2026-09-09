// A movie too long to hold in one batch is refused before the Run, the same way a sequence is: the
// answer carries a count and a limit, and the source it came off makes no difference.
//   tools/qa_node.py --start --repo . --node SGLoadVersion --drive tools/drive_movie_budget.js
// Every /sg route is answered here, so nothing reaches a site.
const real = window.fetch.bind(window);
const json = (body) => new Response(JSON.stringify(body),
  { status: 200, headers: { "Content-Type": "application/json" } });
// What /sg/resolve answers for a movie: frames counted off the clip, with no numbering of their own.
const RESOLVE = {
  id: 31875, code: "chr_010_comp_v006", why: "newest on this link",
  status: { code: "rev", label: "Pending Review", rgb: "255,169,0", icon: "" },
  media: ["chr_010_comp_v006.mov — Movie"],
  image_label: "chr_010_comp_v006.mov, 300 frames",
  video_label: "chr_010_comp_v006.mov",
  frames: { count: 300 },
  batch: { width: 1920, height: 1080, fits: 172, gib: "4" },
  format: "ProRes 422, RGB, 1920x1080, 300 frames",
  colour_space: "",
};
const ROUTES = [
  [/\/sg\/projects/, () => json({ items: [{ label: "Chariot", id: 1, code: "CHR", image: "" }],
                                  default: 1 })],
  [/\/sg\/profile/, () => json({ link_type: "Shot" })],
  [/\/sg\/statuses/, () => json({ items: [{ label: "rev", rgb: "1,2,3" }] })],
  [/\/sg\/entities/, () => json({ items: [{ label: "chr_010 (Shot)", id: 11 }] })],
  [/\/sg\/tasks/, () => json({ items: [{ label: "Comp", id: 5 }] })],
  [/\/sg\/resolve/, () => json(RESOLVE)],
];
window.fetch = (url, opts) => {
  const u = String(url?.url ?? url);
  const hit = ROUTES.find(([re]) => re.test(u));
  return hit ? hit[1](opts) : real(url, opts);
};

app.graph.clear();
const n = window.LiteGraph.createNode("SGLoadVersion");
app.graph.add(n);
await wait(1800);

const alert = document.querySelector(".sg-alert")?.textContent.trim() || "";
const state = document.querySelector(".sg-state")?.textContent.trim() || "";
const want = "Set frame_count to 172 or less at this resolution. 300 frames of 1920×1080 would "
  + "need 6.95 GiB as one batch; the limit is 4 GiB, batch_budget_gib in profile.local.json.";
const ok = alert === want && state === "check this";
return { verdict: `${ok ? "PASS" : "FAIL"} pill=${state}`, alert };

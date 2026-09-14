// Checks that a pinned Version whose plate is over the batch budget shows both the pin notice and
// the refusal alert.
// Answers the /sg routes here. No site is read.
//   tools/qa_node.py --start --repo . --node SGLoadVersion --drive tools/drive_pinned_budget.js
const real = window.fetch.bind(window);
const json = (body) => new Response(JSON.stringify(body),
  { status: 200, headers: { "Content-Type": "application/json" } });
const RESOLVE = {
  id: 31875, code: "chr_010_comp_v006", why: "pinned",
  status: { code: "rev", label: "Pending Review", rgb: "255,169,0", icon: "" },
  media: ["chr_010_comp_v006.%04d.exr · Rendered Image"],
  image_label: "chr_010_comp_v006.%04d.exr, 120 frames",
  video_label: "the frames at 25 fps, from the Version",
  frames: { first: 1, last: 120, count: 120 },
  batch: { width: 3840, height: 2160, fits: 43, gib: "4" },
  format: "EXR 32-bit float, RGB, 3840x2160, 120 frames",
  colour_space: "ACEScg",
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
await wait(1500);
const w = (name) => n.widgets.find((x) => x.name === name);
w("pin_version_id").value = 31875;
w("pin_version_id").callback(31875);
await wait(1200);

const alert = document.querySelector(".sg-alert")?.textContent.trim() || "";
const dim = [...document.querySelectorAll(".sg-dim")].map((e) => e.textContent.trim());
const state = document.querySelector(".sg-state")?.textContent.trim() || "";
const ok = alert.startsWith("Set frame_count to 43 or less")
  && dim.includes("Pinned to Version 31875. All the fields above are ignored.")
  && state === "check this";
return { verdict: `${ok ? "PASS" : "FAIL"} pill=${state}`, alert, dim };

// What a run wrote stays on the panel, through the redraw that follows it.
//   tools/qa_node.py --start --repo . --node SGPublishVersion --drive tools/drive_run_log_persists.js
// Every /sg route is answered here, so nothing reaches a site.
const real = window.fetch.bind(window);
const json = (body) => new Response(JSON.stringify(body),
  { status: 200, headers: { "Content-Type": "application/json" } });
const ROUTES = [
  [/\/sg\/projects/, () => json({ items: [{ label: "Chariot", id: 1, code: "CHR", image: "" }],
                                  default: 1 })],
  [/\/sg\/profile/, () => json({ link_type: "Shot" })],
  [/\/sg\/statuses/, () => json({ items: [{ label: "rev", rgb: "1,2,3" }] })],
  [/\/sg\/entities/, () => json({ items: [{ label: "chr_010 (Shot)", id: 11 }] })],
  [/\/sg\/tasks/, () => json({ items: [{ label: "Comp", id: 5 }] })],
  [/\/sg\/preview_code/, () => json({ code: "chr_010_comp_v007", templates: [], latest: null })],
  [/\/sg\/preview_publish/, () => json({ fields: [], sources: [], media: "Frame 1, as a still." })],
  [/\/sg\/node_defaults/, () => json({})],
];
window.fetch = (url, opts) => {
  const u = String(url?.url ?? url);
  const hit = ROUTES.find(([re]) => re.test(u));
  return hit ? hit[1](opts) : real(url, opts);
};

app.graph.clear();
const n = window.LiteGraph.createNode("SGPublishVersion");
app.graph.add(n);
await wait(1500);                      // the pickers have loaded and the first preview has drawn

const LINES = ["Published chr_010_comp_v006 as Version 32002.",
               "Registered 1 frame as chr_010_comp_v006.0001.png, PublishedFile 7021.",
               "Review media: the image itself"];
app.api.dispatchEvent(new CustomEvent("executed", { detail: {
  node: String(n.id),
  output: {
    text: LINES,
    published: [{ code: "chr_010_comp_v006", id: 32002, link: "Shot chr_010", status: "",
                  outputs: [], media: "the image itself",
                  site_url: "https://example.shotgrid.autodesk.com",
                  files: [{ kind: "frames", count: 1,
                            path: "/Volumes/FPT/chr_010/comp/v006/chr_010_comp_v006.0001.png" }] }],
  },
}}));

const shown = () => [...document.querySelectorAll(".sg-ok")].map((e) => e.textContent.trim());
await wait(600);
const before = shown();
await wait(8000);                      // the redraw 1.2s after the run has long since landed
const after = shown();
const kept = LINES.every((l) => after.includes(l));
return { verdict: `${kept ? "PASS" : "FAIL"} ${after.length} lines 8s after the run`,
         before, after };

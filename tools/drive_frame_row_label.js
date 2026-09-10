// Checks that one frame reads as "1 frame" on the panel's file row, as the run log spells it.
// Answers the /sg routes here with fixtures. No site is read.
//   tools/qa_node.py --start --repo . --node SGPublishVersion --drive tools/drive_frame_row_label.js
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
  [/\/sg\/preview_publish/, () => json({ fields: [], sources: [] })],
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
const file = (count) => ({ kind: "frames", count,
  path: "/Volumes/FPT/chr_010/comp/v006/chr_010_comp_v006" +
        (count === 1 ? ".0001.png" : ".%04d.png") });
const run = (count) => app.api.dispatchEvent(new CustomEvent("executed", { detail: {
  node: String(n.id),
  output: {
    text: [`Registered ${count === 1 ? "1 frame" : count + " frames"} as chr_010_comp_v006.`],
    published: [{ code: "chr_010_comp_v006", id: 32002, link: "Shot chr_010", status: "",
                  outputs: [], media: "the image itself",
                  site_url: "https://example.shotgrid.autodesk.com", files: [file(count)] }],
  },
}}));
const labels = () => [...document.querySelectorAll(".sg-k")].map((e) => e.textContent.trim());

await wait(1500);                      // the pickers have settled and the panel is up
run(3);
await wait(500);
const many = labels();
run(1);
await wait(500);
const one = labels();

const ok = one.includes("1 frame") && !one.includes("1 frames") && many.includes("3 frames");
return { verdict: `${ok ? "PASS" : "FAIL"} one=[${one}] three=[${many}]` };

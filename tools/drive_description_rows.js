// Checks that a value going into the description says so beside itself, and that no row on the
// panel is struck through.
// Answers the /sg routes here. No site is read.
//   tools/qa_node.py --start --repo . --node SGPublishVersion --drive tools/drive_description_rows.js
const real = window.fetch.bind(window);
const json = (body) => new Response(JSON.stringify(body),
  { status: 200, headers: { "Content-Type": "application/json" } });
// What /sg/preview_publish returns: a field this site has, two values that go into the description,
// and one concept this graph has no value for.
const FIELDS = [
  { name: "ai_seed", label: "Seed", value: "42", into_description: false, note: "" },
  { name: "Prompt", label: "Prompt", value: "a red car on a wet street", into_description: true,
    note: "Into the description." },
  { name: "Model", label: "Model", value: "sd_xl_base_1.0.safetensors", into_description: true,
    note: "Into the description." },
  { name: "Steps", label: "Steps", value: "", into_description: true,
    note: "Into the description." },
];
const ROUTES = [
  [/\/sg\/projects/, () => json({ items: [{ label: "Chariot", id: 1, code: "CHR", image: "" }],
                                  default: 1 })],
  [/\/sg\/profile/, () => json({ link_type: "Shot" })],
  [/\/sg\/statuses/, () => json({ items: [{ label: "rev", rgb: "1,2,3" }] })],
  [/\/sg\/entities/, () => json({ items: [{ label: "chr_010 (Shot)", id: 11 }] })],
  [/\/sg\/tasks/, () => json({ items: [{ label: "Comp", id: 5 }] })],
  [/\/sg\/preview_code/, () => json({ code: "chr_010_comp_v007", templates: [], latest: null })],
  [/\/sg\/preview_publish/, () => json({ fields: FIELDS, sources: [], writes: [],
                                         uploads: ["image (the thumbnail)"],
                                         media: "Frame 1, as a still." })],
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
await wait(1800);
// The project list is fetched as the page loads, before this drive answers for it, so the node opens
// on the profile's project. Pick the one these routes know.
const w = (name) => n.widgets.find((x) => x.name === name);
if (w("project").value !== "Chariot") {
  w("project").value = "Chariot"; w("project").callback?.("Chariot"); await wait(2200);
}
// The fields block is inside the node's advanced fold. The button is the editor's own.
const button = [...document.querySelectorAll("button, .p-button")]
  .find((b) => /Show advanced inputs/i.test(b.textContent || ""));
button?.click();
await wait(700);

const rows = [...document.querySelectorAll(".sg-more .sg-row")].map((r) => ({
  key: r.querySelector(".sg-k")?.textContent.trim(),
  value: r.querySelector(".sg-v")?.textContent.trim(),
}));
const prompt = rows.find((r) => r.key === "Prompt");
const seed = rows.find((r) => r.key === "seed");
const ok = !document.querySelector(".sg-gone")
  && prompt?.value === "a red car on a wet street into the description"
  && seed?.value === "42";
return { verdict: `${ok ? "PASS" : "FAIL"} ${rows.length} rows, struck through: `
  + `${document.querySelectorAll(".sg-gone").length}`, rows };

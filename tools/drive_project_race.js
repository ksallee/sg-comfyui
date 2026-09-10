// Checks that a slow project's reads cannot write to the node after a second project is picked.
// Answers the /sg routes here. No site is read.
//   tools/qa_node.py --start --repo . --node SGPublishVersion --drive tools/drive_project_race.js
const real = window.fetch.bind(window);
const json = (body) => new Response(JSON.stringify(body),
  { status: 200, headers: { "Content-Type": "application/json" } });
// A slow response that honours the abort the cascade sends, as aiohttp does.
const after = (ms, body) => (opts) => new Promise((ok, no) => {
  const t = setTimeout(() => ok(json(body)), ms);
  opts?.signal?.addEventListener("abort", () => {
    clearTimeout(t); no(new DOMException("aborted", "AbortError"));
  });
});
const PROJECTS = { items: [{ label: "Chariot", id: 1, code: "CHR", image: "" },
                           { label: "Barbarian", id: 2, code: "BRB", image: "" }], default: 1 };
const ROUTES = [
  [/\/sg\/projects/, () => json(PROJECTS)],
  [/\/sg\/profile.*project_id=1/, after(1500, { link_type: "Shot" })],
  [/\/sg\/profile.*project_id=2/, () => json({ link_type: "Asset" })],
  [/\/sg\/statuses.*project_id=1/, after(1500, { items: [{ label: "chr rev", rgb: "1,2,3" }] })],
  [/\/sg\/statuses.*project_id=2/, () => json({ items: [{ label: "brb rev", rgb: "1,2,3" }] })],
  [/\/sg\/entities.*project_id=1/, after(1500, { items: [{ label: "chr_010 (Shot)", id: 11 }] })],
  [/\/sg\/entities.*project_id=2/, () => json({ items: [{ label: "brb_010 (Asset)", id: 21 }] })],
  [/\/sg\/tasks/, () => json({ items: [] })],
  [/\/sg\/preview_code/, () => json({ code: "brb_010_v001", templates: [], latest: null })],
  [/\/sg\/preview_publish/, () => json({ fields: [], sources: [] })],
  [/\/sg\/node_defaults/, () => json({})],
];
window.fetch = (url, opts) => {
  const u = String(url?.url ?? url);
  const hit = ROUTES.find(([re]) => re.test(u));
  return hit ? hit[1](opts) : real(url, opts);
};

// The node is created after the patch, so its pickers read from here.
app.graph.clear();
const n = window.LiteGraph.createNode("SGPublishVersion");
app.graph.add(n);
const w = (name) => n.widgets.find((x) => x.name === name);

await wait(250);                       // Chariot's reads are in flight and will take 1.5s
const project = w("project");
project.value = "Barbarian";
project.callback("Barbarian");         // what the picker does when a row is clicked
await wait(2500);                      // long enough for Chariot's responses to have arrived

const links = w("link").options.values.join(", ");
const statuses = w("status").options.values.join(", ");
const ok = w("project").value === "Barbarian"
  && links.includes("brb_010 (Asset)") && !links.includes("chr_010")
  && statuses.includes("brb rev") && !statuses.includes("chr rev");
return { verdict: `${ok ? "PASS" : "FAIL"} project=${w("project").value} links=[${links}] `
  + `statuses=[${statuses}]` };

// Checks that a publish whose storage cannot be resolved says so before the Run, outside the fold.
// Answers the /sg routes here. No site is read.
//   tools/qa_node.py --start --repo . --node SGPublishVersion --drive tools/drive_storage_alert.js
const ALERT = "Create Published Files is ticked, but the paths could not be worked out. "
  + "No storage is chosen, and this site has 3 to choose from. Pick Storage under Settings, "
  + "then SG: primary, renders, review.";
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
  // What the route returns when `sequence.plan` refuses: no paths, and the sentence why.
  [/\/sg\/preview_publish/, () => json({ fields: [], sources: [], writes: [], alert: ALERT,
                                         media: "Frame 1, as a still. Every frame becomes a "
                                                + "Published File." })],
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

const alert = document.querySelector(".sg-alert")?.textContent.trim() || "";
const state = document.querySelector(".sg-state")?.textContent.trim() || "";
const ok = alert === ALERT && state === "check this";
return { verdict: `${ok ? "PASS" : "FAIL"} pill=${state}`, alert };

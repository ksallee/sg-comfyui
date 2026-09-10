// Checks that a login expiring between one read and the next does not empty the node.
// Answers the /sg routes here. No site is read.
//   tools/qa_node.py --start --repo . --node SGPublishVersion --drive tools/drive_stale_project.js
const EXPIRED = "Your login has expired. Log in again under Settings, then SG.";
let expired = false;
const real = window.fetch.bind(window);
const json = (body) => new Response(JSON.stringify(body),
  { status: 200, headers: { "Content-Type": "application/json" } });
const ROUTES = [
  [/\/sg\/projects/, () => json({ items: [{ label: "Chariot", id: 1, code: "CHR", image: "" }],
                                  default: 1 })],
  [/\/sg\/profile/, () => json({ link_type: "Shot" })],
  [/\/sg\/statuses/, () => json({ items: [{ label: "rev", rgb: "1,2,3" }] })],
  [/\/sg\/entities/, () => json(expired ? { items: [], error: EXPIRED }
                                        : { items: [{ label: "chr_010 (Shot)", id: 11 }] })],
  [/\/sg\/tasks/, () => json({ items: [{ label: "Comp", id: 5 }] })],
  [/\/sg\/preview_code/, () => json({ code: "chr_010_v001", templates: [], latest: null })],
  [/\/sg\/preview_publish/, () => json({ fields: [], sources: [] })],
];
window.fetch = (url, opts) => {
  const u = String(url?.url ?? url);
  const hit = ROUTES.find(([re]) => re.test(u));
  return hit ? hit[1](opts) : real(url, opts);
};

app.graph.clear();
const n = window.LiteGraph.createNode("SGPublishVersion");
app.graph.add(n);
const w = (name) => n.widgets.find((x) => x.name === name);
w("project").value = "Chariot";
w("project").callback("Chariot");
await wait(1200);

// A link, picked the way an operator picks one, as a saved graph stores it.
const row = [...document.querySelectorAll(".sg-dom")]
  .find((d) => (d.querySelector(".sg-lab")?.textContent || "").trim() === "link");
row.querySelector("button").click();
await wait(700);
document.querySelector('.sg-pop-list [role="option"]').click();
await wait(900);
const before = ["link", "task", "status"].map((k) => `${k}=${w(k).value}`).join(" ");

expired = true;                       // the login expires while the graph is open
n.widgets.find((x) => x.name === "Sync from SG").callback();
await wait(1200);

const after = ["link", "task", "status"].map((k) => `${k}=${w(k).value}`).join(" ");
const said = [...document.querySelectorAll(".sg-err")].map((e) => e.textContent.trim());
const ok = before === after && said.some((s) => s === EXPIRED);
return { verdict: `${ok ? "PASS" : "FAIL"} kept [${after}] panel says "${said[0] || ""}"` };

// Checks that Enter pressed before the response to a keystroke arrives does not pick the previous
// search's row.
// Answers the /sg routes here. No site is read.
//   tools/qa_node.py --start --repo . --node SGPublishVersion --drive tools/drive_picker_enter.js
const real = window.fetch.bind(window);
const json = (body) => new Response(JSON.stringify(body),
  { status: 200, headers: { "Content-Type": "application/json" } });
const PROJECTS = [{ label: "Barbarian", id: 1, code: "BRB", image: "" },
                  { label: "Chariot", id: 2, code: "CHR", image: "" },
                  { label: "Zebra", id: 3, code: "ZBR", image: "" }];
window.fetch = (url, opts) => {
  const u = String(url?.url ?? url);
  if (!/\/sg\//.test(u)) return real(url, opts);
  if (/projects/.test(u)) return json({ items: PROJECTS, default: 3 });
  if (/profile/.test(u)) return json({ link_type: "Shot" });
  if (/preview_code/.test(u)) return json({ code: "zbr_010_v001", templates: [] });
  return json({ items: [] });
};

app.graph.clear();
const n = window.LiteGraph.createNode("SGPublishVersion");
app.graph.add(n);
const project = n.widgets.find((x) => x.name === "project");
project.value = "Zebra";
project.callback("Zebra");            // a known project to start from
await wait(1200);

const row = [...document.querySelectorAll(".sg-dom")]
  .find((d) => (d.querySelector(".sg-lab")?.textContent || "").trim() === "project");
row.querySelector("button").click();
await wait(700);                       // the first search is drawn: Barbarian is the highlighted row

const input = document.querySelector(".sg-pop-input");
const enter = () => input.dispatchEvent(
  new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
input.value = "cha";
input.dispatchEvent(new Event("input", { bubbles: true }));
enter();                               // inside the debounce, over the previous search's rows
await wait(60);
const during = project.value;

await wait(800);                       // the response for "cha" is drawn
enter();
await wait(300);
const settled = project.value;

const ok = during === "Zebra" && settled === "Chariot";
return { verdict: `${ok ? "PASS" : "FAIL"} inside the debounce="${during}" after it="${settled}"` };

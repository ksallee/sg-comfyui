// Checks the Task picker on SG Publish and takes one chosen Task through a Run.
// PASS needs four results: the picker offers each Task the widget lists, one is chosen, the panel
// names it before the Run, and the Version the Run files resolves by that Task.
// Needs the sandbox project and Shot sh010, which has six Tasks.
// Publishes one 512x512 frame to the sandbox project.
//   tools/qa_node.py --start --repo <checkout> --drive tools/drive_task_options.js
const pause = (ms) => wait(ms);
const ctl = (label) => [...document.querySelectorAll(".sg-dom")]
  .find((d) => (d.querySelector(".sg-lab")?.textContent || "").trim().toLowerCase() === label);
const options = () => [...document.querySelectorAll('[role="option"]')];
const rowName = (r) => (r.querySelector(".sg-pop-name")?.textContent || r.textContent || "").trim();
const rowStep = (r) => (r.querySelector(".sg-pop-meta")?.textContent || "").trim();
// Both boxes of the readout, the fold included. textContent, because a closed fold has no
// innerText.
const panel = () => [...document.querySelectorAll(".sg-panel")]
  .map((p) => p.textContent || "").join(" ").replace(/\s+/g, " ");

const openPicker = async (label) => {
  const c = ctl(label);
  if (!c) return false;
  c.querySelector("button").click();
  for (let i = 0; i < 40 && !options().length; i++) await pause(250);
  return true;
};

const pick = async (label, term, want) => {
  if (!await openPicker(label)) return false;
  const inp = document.querySelector(".sg-pop-input");
  if (inp && term) { inp.value = term; inp.dispatchEvent(new Event("input", { bubbles: true })); }
  // A row is clicked by the index it had when the list was drawn, so wait for the response to the
  // typed term before reading the rows.
  const busy = () => document.querySelector(".sg-pop-busy")?.hidden === false;
  for (let i = 0; i < 60 && busy(); i++) await pause(250);
  let hit = null;
  for (let i = 0; i < 40 && !hit; i++) {
    await pause(250);
    hit = options().find((r) => rowName(r).toLowerCase().includes(want.toLowerCase()));
  }
  hit?.click();
  await pause(1200);
  return !!hit;
};

app.graph.clear();
await pause(300);
const img = LiteGraph.createNode("EmptyImage");
img.pos = [40, 240];
app.graph.add(img);
for (const [k, v] of [["width", 512], ["height", 512], ["batch_size", 1], ["color", 3368601]]) {
  const x = img.widgets.find((y) => y.name === k);
  if (x) x.value = v;
}
const pub = LiteGraph.createNode("SGPublishVersion");
pub.pos = [420, 120];
app.graph.add(pub);
img.connect(0, pub, 0);
app.canvas.centerOnNode(pub);
app.canvas.ds.state.scale = 0.9;
app.canvas.setDirty(true, true);
await pause(1500);
// The field rows are inside ComfyUI's advanced fold, and a closed fold renders none of them.
document.querySelector('[data-testid="advanced-inputs-button"]')?.click();
await pause(1200);

const w = (n) => pub.widgets.find((x) => x.name === n);
await pick("project", "", "sandbox");
await pick("link", "sh010", "sh010");
await pause(3500);
const unset = /No task picked\./.test(panel());

// What the widget lists against what the picker offers. The hidden combo is the widget the graph
// saves, so its options are the list a picked value comes from.
const task = w("task");
const held = (task.options?.values || []).slice();
await openPicker("task");
const offered = options().map((r) => ({ name: rowName(r), step: rowStep(r) }));
const names = offered.map((r) => r.name);
const missing = held.filter((v) => !names.includes(v));
const extra = names.filter((v) => !held.includes(v));

const wanted = offered.find((r) => r.name !== "(none)");
options().find((r) => rowName(r) === wanted?.name)?.click();
await pause(1200);
w("root_name").value = "task_pick_check";
w("root_name").callback?.("task_pick_check");
await pause(5000);
const chosen = !!wanted && task.value === wanted.name;
// Two spans with no space between them, so the label runs straight into the value.
const onPanel = /sg_task\s*Task \d+/.test(panel());

await app.queuePrompt(0, 1);
for (let i = 0; i < 120 && !/last run/i.test(panel()); i++) await pause(1000);
await pause(4000);
const href = [...document.querySelectorAll("a.sg-a")].map((a) => a.href)
  .find((h) => /\/detail\/Version\/\d+/.test(h)) || "";
const published = Number((href.match(/\/detail\/Version\/(\d+)/) || [])[1] || 0);

// The Version the Run filed, asked for by that Task alone. The load node's resolver returns the
// newest Version on the link that names it.
const q = new URLSearchParams({ project: w("project").value, link: w("link").value,
                                task: task.value });
const found = await (await fetch(`/sg/resolve?${q}`)).json();
const onVersion = published > 0 && Number(found.id) === published;

const pass = unset && !missing.length && !extra.length && chosen && onPanel && onVersion;
return {
  verdict: `${pass ? "PASS" : "FAIL"} the widget lists ${held.length}, the picker offers `
    + `${offered.length}; picked ${task.value}; Version ${published} resolves by that Task as `
    + `${found.id}`,
  held, offered, missing, extra, unset, chosen, onPanel, onVersion, published,
  code: w("code_template")?.value || "",
};

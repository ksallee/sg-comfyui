// Checks the completion in the template fields: the tokens after a brace, the hop into a linked
// type's own fields, and the Default row. Leaves the popup open for a screenshot.
// Answers the /sg routes here. No site is read.
//   uv run --with playwright --python 3.11 python tools/qa_node.py --start --port 8189 \
//     --node SGPublishVersion --drive tools/drive_template_completion.js --shot 01_node.png
const real = window.fetch.bind(window);
const json = (body) => new Response(JSON.stringify(body),
  { status: 200, headers: { "Content-Type": "application/json" } });
const ROOT_TEMPLATE = "{entity}_{sg_task.Task.step.Step.short_name}";
// `{entity}` as the route answers it: the picked link's type when the URL names one, else the
// types the project links to, for the operator to pick the hop.
const TOKENS = (linkType) => [
  { token: "{entity}", note: "The name of the Shot or Asset this node is linked to.",
    type: linkType, types: linkType ? [linkType] : ["Shot", "Asset"] },
  { token: "{sg_task}", note: "The name of the Task this node is linked to.", type: "Task" },
  { token: "{sg_task.Task.step.Step.short_name}",
    note: "The pipeline step of that Task, short, such as RTO.", type: "" },
  { token: "{sg_task.Task.step}",
    note: "The pipeline step of that Task in full, such as Roto.", type: "Step" },
  { token: "{project}", note: "The name of the project.", type: "Project" },
];
// As the route returns them: one type at a time, by display name.
const FIELDS = {
  Task: [
    { name: "task_assignees", display_name: "Assigned To", data_type: "multi_entity",
      valid_types: ["HumanUser"] },
    { name: "step", display_name: "Pipeline Step", data_type: "entity", valid_types: ["Step"] },
    { name: "content", display_name: "Task Name", data_type: "text", valid_types: [] },
  ],
  Step: [
    { name: "short_name", display_name: "Short Name", data_type: "text", valid_types: [] },
    { name: "code", display_name: "Step Name", data_type: "text", valid_types: [] },
  ],
  Shot: [{ name: "code", display_name: "Shot Code", data_type: "text", valid_types: [] }],
  Asset: [
    { name: "sg_asset_type", display_name: "Asset Type", data_type: "list", valid_types: [] },
    { name: "code", display_name: "Asset Name", data_type: "text", valid_types: [] },
  ],
};
window.fetch = (url, opts) => {
  const u = String(url?.url ?? url);
  if (!/\/sg\//.test(u)) return real(url, opts);
  if (/projects/.test(u)) return json({ items: [{ label: "Chariot", id: 1 }], default: 1 });
  if (/profile/.test(u)) return json({ link_type: "Shot" });
  if (/tokens/.test(u)) {
    return json({ items: TOKENS(decodeURIComponent(u.split("link_type=")[1] || "")) });
  }
  if (/schema_fields/.test(u)) {
    return json({ items: FIELDS[decodeURIComponent(u.split("type=")[1] || "")] || [] });
  }
  if (/preview_code/.test(u)) {
    return json({ code: "chr_010_comp_v001", latest: null,
                  settings: { root_name: ROOT_TEMPLATE,
                              code_template: "{root_name}_v{version:03d}" } });
  }
  return json({ items: [] });
};

app.graph.clear();
const n = window.LiteGraph.createNode("SGPublishVersion");
app.graph.add(n);
const project = n.widgets.find((x) => x.name === "project");
project.value = "Chariot";             // a known project, so the first preview answers
project.callback("Chariot");
await wait(2000);

const input = document.querySelector('input[aria-label="root_name"]');
if (!input) return { error: "no root_name input on the node" };

const key = (name) => input.dispatchEvent(
  new KeyboardEvent("keydown", { key: name, bubbles: true }));
const enter = (text) => {
  input.focus();
  input.value = text;
  input.setSelectionRange(text.length, text.length);
  input.dispatchEvent(new Event("input", { bubbles: true }));
};
const labels = () => [...document.querySelectorAll(".sg-pop [role=option] .sg-tok-name")]
  .map((e) => e.textContent.trim());
const widget = () => n.widgets.find((x) => x.name === "root_name").value;

// The tokens whose path matches what is typed, and the Default row under them.
enter("{sg");
await wait(700);
const tokenRows = labels();

// Enter takes the highlighted row.
key("Enter");
await wait(300);
const picked = widget();

// A token that names an entity descends into that type's own fields.
enter("{sg_task.");
await wait(500);
const taskRows = labels();

// The right arrow travels one hop further, and the path is spelled in full whatever was typed.
const stepRow = [...document.querySelectorAll(".sg-pop [role=option]")]
  .find((e) => e.querySelector(".sg-tok-name").textContent.trim() === "step");
stepRow?.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));
key("ArrowRight");
await wait(500);
const hopped = input.value;
const stepRows = labels();

// The last row is the template Settings has in force, and it replaces the whole field.
enter("{");
await wait(400);
const withDefault = labels();
const defaultRow = [...document.querySelectorAll(".sg-pop [role=option]")]
  .find((e) => e.querySelector(".sg-tok-name").textContent.trim() === "Default");
defaultRow?.click();
await wait(400);
const fromDefault = widget();

// No link picked: `{entity.` offers the types the project links to, and picking one is the hop.
enter("{entity.");
await wait(500);
const typeRows = labels();
const assetRow = [...document.querySelectorAll(".sg-pop [role=option]")]
  .find((e) => e.querySelector(".sg-tok-name").textContent.trim() === "Asset");
assetRow?.click();
await wait(500);
const viaType = input.value;
const assetRows = labels();

// An Asset picked on the link: `{entity.` is that type's fields, with no type to pick.
n.widgets.find((x) => x.name === "link").value = "bunny (Asset)";
enter("{entity.");
await wait(500);
const pickedRows = labels();
n.widgets.find((x) => x.name === "link").value = "";

// Escape closes it.
enter("{sg");
await wait(500);
key("Escape");
await wait(200);
const closed = document.querySelectorAll(".sg-pop").length;

// The Run bar, the canvas controls and the toasts are not part of the frame.
for (const sel of ["#comfyui-body-bottom", ".actionbar", "[class*='actionbar']",
                   "[class*='graph-canvas-menu']", "[class*='canvas-menu']",
                   "[class*='selection-toolbox']", ".p-buttongroup", ".p-toast"]) {
  document.querySelectorAll(sel).forEach((e) => { e.style.display = "none"; });
}
// The node at the top left of the canvas, at its own scale, so the frame is the node and the popup.
app.canvas.ds.scale = 1;
app.canvas.ds.offset = [140 - n.pos[0], 110 - n.pos[1]];
app.canvas.setDirty(true, true);
await wait(400);

// The field is left with a brace open, for the shot.
enter("{sg");
await wait(500);

const checks = [
  ["the tokens after {sg", tokenRows.join(" ") === "{sg_task} {sg_task.Task.step.Step.short_name} "
    + "{sg_task.Task.step} Default"],
  ["Escape closes the popup", closed === 0],
  ["Enter takes the highlighted token", picked === "{sg_task}"],
  ["a link lists the type's own fields",
   taskRows.join(" ") === "task_assignees step content Default"],
  ["the hop spells the path in full", hopped === "{sg_task.Task.step.Step."],
  ["the hop lists the step's fields", stepRows.join(" ") === "short_name code Default"],
  ["Default is listed whatever is typed", withDefault[withDefault.length - 1] === "Default"],
  ["Default replaces the field", fromDefault === ROOT_TEMPLATE],
  ["no link picked lists the project's types", typeRows.join(" ") === "Shot Asset Default"],
  ["a picked type is the hop", viaType === "{entity.Asset." && assetRows.join(" ") === "sg_asset_type code Default"],
  ["the picked link's type wins", pickedRows.join(" ") === "sg_asset_type code Default"],
];
const bad = checks.filter(([, ok]) => !ok).map(([what]) => what);
return {
  verdict: bad.length ? `FAIL ${bad.join("; ")}` : "PASS",
  tokenRows, picked, taskRows, hopped, stepRows, fromDefault, typeRows, viaType, assetRows,
  pickedRows,
};

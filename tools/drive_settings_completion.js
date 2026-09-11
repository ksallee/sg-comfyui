// Checks the completion in the Settings template rows, and leaves the popup open for a screenshot.
// Answers the /sg routes here. No site is read.
//   uv run --with playwright --python 3.11 python tools/qa_node.py --start --port 8189 \
//     --drive tools/drive_settings_completion.js --shot 02_settings.png
const real = window.fetch.bind(window);
const json = (body) => new Response(JSON.stringify(body),
  { status: 200, headers: { "Content-Type": "application/json" } });
const ROOT_TEMPLATE = "{entity}_{sg_task.Task.step.Step.short_name}";
const TOKENS = [
  { token: "{entity}", note: "The name of the Shot or Asset this node is linked to.", type: "Shot" },
  { token: "{sg_task}", note: "The name of the Task this node is linked to.", type: "Task" },
  { token: "{sg_task.Task.step.Step.short_name}",
    note: "The pipeline step of that Task, short, such as RTO.", type: "" },
  { token: "{sg_task.Task.step.Step.code}",
    note: "The pipeline step of that Task in full, such as Roto.", type: "" },
  { token: "{project}", note: "The name of the project.", type: "Project" },
];
window.fetch = (url, opts) => {
  const u = String(url?.url ?? url);
  if (!/\/sg\//.test(u)) return real(url, opts);
  if (/session/.test(u)) return json({ how: "script", script_name: "comfyui", alive: true });
  if (/tokens/.test(u)) return json({ items: TOKENS });
  if (/preview_template/.test(u)) return json({ example: "sh010_RTO" });
  if (/defaults/.test(u)) {
    return json({ values: {}, projects: [{ label: "Chariot", id: 1 }], storages: [], statuses: [],
                  placeholders: { root_name: ROOT_TEMPLATE,
                                  code_template: "{root_name}_v{version:03d}" } });
  }
  return json({ items: [] });
};

await wait(600);
// The Run bar, the canvas controls and the toasts are not part of the frame.
for (const sel of ["#comfyui-body-top", "#comfyui-body-bottom", ".actionbar", "[class*='actionbar']",
                   "[class*='canvas-menu']", ".p-buttongroup", ".p-toast"]) {
  document.querySelectorAll(sel).forEach((e) => { e.style.display = "none"; });
}
await app.extensionManager.command.execute("Comfy.ShowSettingsDialog");
await wait(1400);
const dialog = document.querySelector("[role=dialog]");
if (!dialog) return { error: "no settings dialog" };
const nav = [...dialog.querySelectorAll("nav *")]
  .find((e) => !e.children.length && (e.textContent || "").trim() === "SG")
  ?.closest("div.cursor-pointer");
if (!nav) return { error: "no SG page in the settings nav" };
nav.click();
await wait(1600);

// The Root name row: the one filled with the template in force for it.
const input = [...dialog.querySelectorAll(".sg-set input.p-inputtext")]
  .find((i) => i.value === ROOT_TEMPLATE);
if (!input) return { error: "no Root name row" };
input.scrollIntoView({ block: "center" });
await wait(600);

input.focus();
input.value = "{";
input.setSelectionRange(1, 1);
input.dispatchEvent(new Event("input", { bubbles: true }));
await wait(700);

const labels = [...document.querySelectorAll(".sg-pop [role=option] .sg-tok-name")]
  .map((e) => e.textContent.trim());
const ok = labels.length === TOKENS.length + 1 && labels[labels.length - 1] === "Default";
const r = dialog.getBoundingClientRect();
return {
  verdict: ok ? "PASS" : `FAIL rows=[${labels}]`,
  labels,
  rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
};

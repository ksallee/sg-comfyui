// Measures the Task list against the Task dropdown on SG Publish.
// A combo is drawn from the node definition, where `task` is declared as `(none)` alone. The list
// the frontend fetches for the picked link never reaches it.
// Needs the sandbox project and Shot sh010, which has six Tasks.
//   tools/qa_node.py --start --repo . --node SGPublishVersion --drive tools/drive_task_options.js
const pause = (ms) => wait(ms);
const ctl = (label) => [...document.querySelectorAll(".sg-dom")]
  .find((d) => (d.querySelector(".sg-lab")?.textContent || "").trim().toLowerCase() === label);
const pick = async (label, term, want) => {
  const c = ctl(label);
  if (!c) return false;
  c.querySelector("button")?.click();
  await pause(900);
  const inp = document.querySelector(".sg-pop-input");
  if (inp && term) { inp.value = term; inp.dispatchEvent(new Event("input", { bubbles: true })); }
  let hit = null;
  for (let i = 0; i < 40 && !hit; i++) {
    await pause(250);
    hit = [...document.querySelectorAll('[role="option"]')]
      .find((r) => (r.textContent || "").toLowerCase().includes(want.toLowerCase()));
  }
  hit?.click();
  await pause(900);
  return !!hit;
};

await pause(1500);
await pick("project", "sand", "sandbox");
await pick("link", "sh010", "sh010");
await pause(2500);

const task = node.widgets.find((x) => x.name === "task");
const values = task.options?.values || [];
const row = [...document.querySelectorAll('[data-testid="node-widget"]')]
  .find((r) => (r.querySelector('[data-testid="widget-layout-field-label"]')?.textContent || "")
    .trim() === "task");
const trigger = row?.querySelector('[data-testid="widget-select-default-trigger"]');
if (!trigger) return { verdict: "SKIP no task combo on the node (Nodes 2.0 off?)" };
trigger.click();
await pause(1500);
const offered = [...document.querySelectorAll('[role="option"]')].map((o) => (o.textContent || "").trim());
const bug = values.length > offered.length;
return {
  verdict: `${bug ? "BUG" : "OK"} the widget holds ${values.length}, the dropdown offers ${offered.length}`,
  values, offered,
};

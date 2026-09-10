// Captures the link and the Task being picked on SG Publish, and the panel rows filling.
// The project is what Settings fills in, so the clip opens on it and goes straight to the link.
// Needs the sandbox project and Shot sh010, which has six Tasks.
//   tools/capture.py --node SGPublishVersion --drive tools/drive_clip_01_publish_pick.js --out 01
await settle(300);
await settleSize(node);
await frameAll(50);
await pause(1400);

// The first characters, typed. The list narrows as they land.
await pick("link", "sh01", "sh010");
await settleSize(node);
await pause(1000);

// The first Task on this link, whatever the project calls it. "(none)" heads the list.
const pickFirstTask = async () => {
  await click(ctl("task").querySelector("button"), 700);
  let rows = [];
  for (let i = 0; i < 40 && rows.length < 2; i++) {
    await pause(250);
    rows = [...document.querySelectorAll('[role="option"]')];
  }
  const hit = rows.find((r) => (r.textContent || "").trim() !== "(none)");
  await click(hit, 700);
  return !!hit;
};
await pickFirstTask();

await settleSize(node);
await frameAll(50);
await pause(2400);

return {
  picked: ["project", "link", "task"].map((k) =>
    `${k}=${node.widgets.find((x) => x.name === k).value}`).join(" "),
  panel: (document.querySelector(".sg-panel")?.innerText || "").replace(/\n/g, " | ").slice(0, 300),
};

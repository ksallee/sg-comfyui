// Captures the project and the link being picked on SG Publish, and the panel rows filling.
// Needs the sandbox project and Shot sh010.
//   tools/capture.py --node SGPublishVersion --drive tools/drive_clip_01_publish_pick.js --out 01
await settle(300);
document.querySelector('[data-testid="advanced-inputs-button"]')?.click();
await settleSize(node);
await frameAll(50);
await pause(300);

await pick("project", "sand", "sandbox");
// No term on the link. The list is already loaded. A typed term is a fresh search on the site.
await pick("link", "", "sh010");
// No Task is picked. The Task list the link brings never reaches its dropdown.
// `drive_task_options.js` measures that.
await settleSize(node);
await frameAll(50);
await pause(2000);

return {
  picked: ["project", "link"].map((k) =>
    `${k}=${node.widgets.find((x) => x.name === k).value}`).join(" "),
  panel: (document.querySelector(".sg-panel")?.innerText || "").replace(/\n/g, " | ").slice(0, 300),
};

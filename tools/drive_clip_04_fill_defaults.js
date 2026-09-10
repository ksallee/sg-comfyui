// Captures Fill from SG defaults writing the Settings templates into the node.
// Needs the sandbox project and Shot sh010.
//   tools/capture.py --node SGPublishVersion --drive tools/drive_clip_04_fill_defaults.js --out 04
await settle(300);
document.querySelector('[data-testid="advanced-inputs-button"]')?.click();
const w = (n) => node.widgets.find((x) => x.name === n);
w("link").value = "sh010 (Shot)";
w("project").value = "sg-comfyui Sandbox"; w("project").callback?.(w("project").value);
await settleSize(node);
await frameAll(50);
await pause(1200);

await click([...document.querySelectorAll("button")]
  .find((b) => (b.textContent || "").trim() === "Fill from SG defaults"), 700);
for (let i = 0; i < 30 && !w("root_name").value; i++) await pause(200);
await pause(2000);

return {
  root_name: w("root_name").value,
  code_template: w("code_template").value,
  panel: (document.querySelector(".sg-panel")?.innerText || "").replace(/\n/g, " | ").slice(0, 240),
};

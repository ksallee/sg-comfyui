// Opens Settings, then SG, and puts one row of that page at the top of the dialog for a screenshot.
// Returns the dialog's rectangle in CSS pixels, so the shot can be cropped to it.
// Needs ANCHOR prepended: the label of the row to scroll to, for example "Log in".
//
//   { printf 'const ANCHOR = "Log in";\n'; cat tools/drive_settings_rows.js; } > /tmp/d.js
//   uv run --with playwright --python 3.11 python tools/qa_node.py --start \
//     --repo ~/dev/sg-comfyui --scale 2 --viewport 1280x900 --drive /tmp/d.js --shot out.png

await wait(600);
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

const leaves = [...dialog.querySelectorAll("*")].filter((e) => !e.children.length);
const label = leaves.find((e) => (e.textContent || "").trim() === ANCHOR)
  // A row label with a tooltip icon beside it is not a leaf. Take the shallowest match instead.
  || [...dialog.querySelectorAll("*")]
    .filter((e) => (e.textContent || "").trim() === ANCHOR)
    .sort((a, b) => b.querySelectorAll("*").length - a.querySelectorAll("*").length).pop();
if (!label) {
  return { error: `no row labelled ${ANCHOR}`,
           labels: leaves.map((e) => (e.textContent || "").trim()).filter(Boolean) };
}
label.scrollIntoView({ block: "start" });
await wait(1200);

const r = dialog.getBoundingClientRect();
return {
  anchor: ANCHOR,
  rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
  headings: [...dialog.querySelectorAll("*")]
    .filter((e) => !e.children.length && e.getBoundingClientRect().top >= r.top
      && e.getBoundingClientRect().bottom <= r.bottom)
    .map((e) => (e.textContent || "").trim()).filter(Boolean).slice(0, 60),
};

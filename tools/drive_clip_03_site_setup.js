// Captures SG Site Setup reading how many of the nine provenance fields exist, and the Create press.
// Answers /sg/fields from here, in the shapes the route sends. No site is asked. Nothing is created.
//   tools/capture.py --drive tools/drive_clip_03_site_setup.js --out 03
const NINE = ["AI Generator", "AI Model", "AI Prompt", "AI Negative Prompt", "AI Seed",
  "AI Sampler", "AI Steps", "AI CFG", "AI Generated From"];
const named = (d) => ({ display: d, name: "sg_" + d.toLowerCase().replace(/[^a-z0-9]/g, "_") });
const json = (body) => new Response(JSON.stringify(body),
  { headers: { "Content-Type": "application/json" } });
let created = false;
const real = window.fetch.bind(window);
window.fetch = (url, opts) => {
  const u = String(url?.url ?? url);
  if (!/\/sg\/fields/.test(u)) return real(url, opts);
  if (((opts && opts.method) || "GET") === "POST") {
    created = true;
    return Promise.resolve(json({
      rows: NINE.slice(3).map((d) => ({ ...named(d), state: "created" })),
      present: 3, created: 6, failed: 0, total: 9,
    }));
  }
  return Promise.resolve(json(created
    ? { present: NINE.map(named), missing: [], total: 9 }
    : { present: NINE.slice(0, 3).map(named), missing: NINE.slice(3).map(named), total: 9 }));
};

await settle(300);
await app.extensionManager.command.execute("Comfy.ShowSettingsDialog");
await pause(1400);
const nav = [...document.querySelectorAll("[role=dialog] nav *")]
  .find((e) => !e.children.length && (e.textContent || "").trim() === "SG")
  ?.closest("div.cursor-pointer");
await click(nav, 550);
await pause(1200);

const row = () => [...document.querySelectorAll(".sg-set")]
  .find((e) => [...e.querySelectorAll("button")]
    .some((b) => b.textContent === "Create provenance fields"));
const el = row();
if (!el) return { error: "no Provenance fields row in the dialog" };
await scrollTo(el);

const value = () => el.querySelector(".sg-text").textContent.trim();
for (let i = 0; i < 40 && !/exist on this site/.test(value()); i++) await pause(200);
await pause(900);

await click([...el.querySelectorAll("button")]
  .find((b) => b.textContent === "Create provenance fields"), 600);
for (let i = 0; i < 40 && !/9 of 9/.test(value()); i++) await pause(200);
const last = [...el.querySelectorAll(".sg-rows > *")].pop();
if (last) await scrollTo(last);
await pause(2000);

return { readout: value(), rows: [...el.querySelectorAll(".sg-rows > *")].map((e) => e.textContent.trim()) };

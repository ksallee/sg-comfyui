// Captures a login expiring while the graph is open: the sentence on the panel, the link kept.
// Answers every /sg route from here. No site is asked.
//   tools/capture.py --node SGPublishVersion --drive tools/drive_clip_05_expired_login.js --out 05
const EXPIRED = "Your login has expired. Log in again under Settings, then SG.";
let expired = false;
const real = window.fetch.bind(window);
const json = (body) => new Response(JSON.stringify(body),
  { headers: { "Content-Type": "application/json" } });
const ROUTES = [
  [/\/sg\/projects/, () => ({ items: [{ label: "Chariot", id: 1, code: "CHR", image: "" }], default: 1 })],
  [/\/sg\/profile/, () => ({ link_type: "Shot" })],
  [/\/sg\/statuses/, () => ({ items: [{ label: "Pending Review", rgb: "155,187,89" }] })],
  [/\/sg\/entities/, () => (expired ? { items: [], error: EXPIRED }
    : { items: [{ label: "chr_010 (Shot)", id: 11 }, { label: "chr_020 (Shot)", id: 12 }] })],
  [/\/sg\/tasks/, () => ({ items: [{ label: "Comp", id: 5 }] })],
  [/\/sg\/preview_code/, () => ({ code: "chr_010_comp_v004", templates: [], latest: null })],
  [/\/sg\/preview_publish/, () => ({ fields: [], sources: [] })],
];
window.fetch = (url, opts) => {
  const u = String(url?.url ?? url);
  const hit = ROUTES.find(([re]) => re.test(u));
  return hit ? Promise.resolve(json(hit[1]())) : real(url, opts);
};

const w = (n) => node.widgets.find((x) => x.name === n);
w("project").value = "Chariot"; w("project").callback?.("Chariot");
await settle(300);
await pause(900);
await frameAll(50);
await pause(500);

// Pick the link, which is what a saved graph carries.
await pick("link", "", "chr_010");
await pause(900);

expired = true;                       // the login goes while the graph is open
await click(node.widgets.find((x) => x.name === "Sync from SG")?.element
  || [...document.querySelectorAll("button")]
    .find((b) => (b.textContent || "").trim() === "Sync from SG"), 600);
for (let i = 0; i < 30 && !document.querySelector(".sg-err"); i++) await pause(200);
await pause(2200);

return {
  kept: ["link", "task", "status"].map((k) => `${k}=${w(k).value}`).join(" "),
  said: [...document.querySelectorAll(".sg-err")].map((e) => e.textContent.trim()),
};

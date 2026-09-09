// The SG Site Setup group, one state per run: a state name is prepended to this file, so one drive
// covers all five and each run leaves one screenshot.
//
//   for s in not_connected nine_of_nine three_of_nine refused restart; do
//     { printf 'const STATE = "%s";\n' "$s"; cat tools/drive_site_setup_states.js; } |
//     uv run --with playwright --python 3.11 python tools/qa_node.py --port 8188 --drive - \
//       --shot ~/Desktop/sg-site-setup-screenshots/$s.png
//   done
//
// `nine_of_nine` asks the real site and presses Create, which is safe: ensure reads the schema first
// and creates only what is missing (probe 019). The other four answer from here, so they need no
// site at all.

const REFUSAL = "You do not have permission to create custom fields on this site.";
const ADVICE = "Ask an admin to press this button, or run the command in INSTALL.md with a script "
  + "key that can create fields.";
const NINE = ["AI Generator", "AI Model", "AI Prompt", "AI Negative Prompt", "AI Seed",
  "AI Sampler", "AI Steps", "AI CFG", "AI Generated From"];
const named = (d) => ({ display: d, name: "sg_" + d.toLowerCase().replace(/[^a-z0-9]/g, "_") });

// Everything but `nine_of_nine` answers one route from here, in the shape that route really sends.
const CANNED = {
  not_connected: (u, m) => /\/sg\/session/.test(u) && m !== "POST"
    ? { body: { how: "none", site: "", who: "", alive: false, script_name: "", has_key: false,
                script_source: "", login: "", typed_script_name: "" } } : null,
  three_of_nine: (u, m) => /\/sg\/fields/.test(u) && m !== "POST"
    ? { body: { present: NINE.slice(0, 3).map(named), missing: NINE.slice(3).map(named), total: 9 } }
    : null,
  refused: (u, m) => !/\/sg\/fields/.test(u) ? null
    : m === "POST"
      ? { body: { rows: NINE.map((d) => ({ ...named(d), state: "failed", why: REFUSAL })),
                  present: 0, created: 0, failed: 9, total: 9, advice: ADVICE } }
      : { body: { present: [], missing: NINE.map(named), total: 9 } },
  // A pack updated in place: /sg/session is registered and /sg/fields is not, until the restart.
  restart: (u) => /\/sg\/fields/.test(u)
    ? { html: "<html><body>404: Not Found</body></html>", status: 404 } : null,
};

const canned = CANNED[STATE];
if (canned) {
  const real = window.fetch.bind(window);
  window.fetch = (url, opts) => {
    const hit = canned(String(url?.url ?? url), (opts && opts.method) || "GET");
    if (!hit) return real(url, opts);
    return Promise.resolve(hit.html
      ? new Response(hit.html, { status: hit.status, headers: { "Content-Type": "text/html" } })
      : new Response(JSON.stringify(hit.body), { headers: { "Content-Type": "application/json" } }));
  };
}

// The dialog, then the SG page in its left-hand nav.
await app.extensionManager.command.execute("Comfy.ShowSettingsDialog");
await wait(1200);
[...document.querySelectorAll("[role=dialog] nav *")]
  .find((e) => !e.children.length && (e.textContent || "").trim() === "SG")
  ?.closest("div.cursor-pointer")?.click();
await wait(1500);

const row = () => [...document.querySelectorAll(".sg-set")]
  .find((e) => [...e.querySelectorAll("button")].some((b) => b.textContent === "Create provenance fields"));
const el = row();
if (!el) return { verdict: "FAIL no Provenance fields row in the dialog" };
el.scrollIntoView({ block: "center" });

const btn = [...el.querySelectorAll("button")].find((b) => b.textContent === "Create provenance fields");
const value = () => el.querySelector(".sg-text").textContent.trim();
const note = () => (el.querySelector(".sg-note") || {}).textContent?.trim() || "";
const results = () => [...el.querySelectorAll(".sg-rows > *")].map((e) => e.textContent.trim());
const until = async (fn, ms = 20000) => {
  for (let i = 0; i < ms / 250; i++) { if (fn()) return true; await wait(250); }
  return false;
};

if (STATE === "not_connected") {
  await until(() => value() !== "Checking…");
  const ok = value() === "Not connected. Log in, or enter a script name and application key."
    && btn.disabled;
  return { verdict: `${ok ? "PASS" : "FAIL"} not connected: "${value()}", button ${btn.disabled ? "disabled" : "ENABLED"}` };
}

if (STATE === "restart") {
  const said = "The running ComfyUI predates this version of the pack. Restart ComfyUI, then reload this page.";
  await until(() => value() === said);
  return { verdict: `${value() === said ? "PASS" : "FAIL"} restart sentence: "${value()}"` };
}

await until(() => /exist on this site/.test(value()));

if (STATE === "three_of_nine") {
  const ok = value() === "3 of 9 exist on this site."
    && NINE.slice(3).every((d) => note().includes(d));
  return { verdict: `${ok ? "PASS" : "FAIL"} "${value()}" ${note()}` };
}

btn.click();
await until(() => results().length >= 9, 60000);
await until(() => !btn.disabled, 60000);
const lines = results();
// The result runs past the foot of the dialog, and the screenshot is what gets reviewed.
[...el.querySelectorAll(".sg-rows > *")].pop()?.scrollIntoView({ block: "center" });
await wait(400);

if (STATE === "refused") {
  const ok = lines.length === 10 && lines.slice(0, 9).every((l) => l.endsWith(REFUSAL))
    && lines[9] === ADVICE;
  return { verdict: `${ok ? "PASS" : "FAIL"} refused: "${lines[0]}" then "${lines[9]}"` };
}

// nine_of_nine: the site really answered, and pressing Create created nothing.
await until(() => value() === "9 of 9 exist on this site.");
const made = lines.filter((l) => / created\.$/.test(l)).length;
const had = lines.filter((l) => / already exists\.$/.test(l)).length;
const ok = had === 9 && made === 0 && value() === "9 of 9 exist on this site.";
return { verdict: `${ok ? "PASS" : "FAIL"} ${had} present ${made} created — "${value()}"` };

// A publish node listens for three run events. Removing it must take all three with it.
//   tools/qa_node.py --start --repo . --node SGPublishVersion --drive tools/drive_listener_leak.js
const real = window.fetch.bind(window);
const json = (body) => new Response(JSON.stringify(body),
  { status: 200, headers: { "Content-Type": "application/json" } });
window.fetch = (url, opts) => {
  const u = String(url?.url ?? url);
  if (!/\/sg\//.test(u)) return real(url, opts);
  if (/projects/.test(u)) return json({ items: [{ label: "Chariot", id: 1 }], default: 1 });
  if (/profile/.test(u)) return json({ link_type: "Shot" });
  if (/preview_code/.test(u)) return json({ code: "chr_010_v001", templates: [] });
  return json({ items: [] });
};

// Counted at the source: every add and every remove on the api, by event name.
const WATCHED = ["execution_start", "execution_cached", "executed"];
const added = [], removed = [];
const add = app.api.addEventListener.bind(app.api);
const drop = app.api.removeEventListener.bind(app.api);
app.api.addEventListener = (name, fn, opts) => { added.push(name); return add(name, fn, opts); };
app.api.removeEventListener = (name, fn, opts) => { removed.push(name); return drop(name, fn, opts); };

app.graph.clear();
const n = window.LiteGraph.createNode("SGPublishVersion");
app.graph.add(n);
await wait(1200);
const mine = WATCHED.filter((e) => added.includes(e));

app.graph.remove(n);                  // the workflow was closed
await wait(400);
// And nothing left listening throws on the next run's events.
let threw = "";
try {
  app.api.dispatchEvent(new CustomEvent("execution_start", { detail: {} }));
  app.api.dispatchEvent(new CustomEvent("executed", { detail: { node: String(n.id), output: {} } }));
} catch (e) { threw = String(e); }
await wait(200);

const gone = WATCHED.filter((e) => removed.includes(e));
const ok = mine.length === 3 && gone.length === 3 && !threw;
return { verdict: `${ok ? "PASS" : "FAIL"} added=[${mine}] removed=[${gone}] threw="${threw}"` };

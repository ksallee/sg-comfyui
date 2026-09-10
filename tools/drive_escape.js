// Checks that a hostile label, href or status icon is drawn as text: nothing executable and nothing
// positioned reaches the page, and a malformed sprite does not stop the redraw.
// Answers the /sg routes here. No site is read.
//   tools/qa_node.py --start --repo . --node SGLoadVersion --drive tools/drive_escape.js
const real = window.fetch.bind(window);
const json = (body) => new Response(JSON.stringify(body),
  { status: 200, headers: { "Content-Type": "application/json" } });
const HOSTILE_LABEL = '<img src=x onerror="window.__pwned=1">';
const HOSTILE_ICON = { kind: "text",
  html: '<span style="position:fixed;inset:0;background:red">x</span>'
      + '<script>window.__pwned = 1<\/script>' };
const BAD_SPRITE = { kind: "sprite", url: "https://example.invalid/sheet.png",
                     offset: "nope", size: null };
window.fetch = (url, opts) => {
  const u = String(url?.url ?? url);
  if (!/\/sg\//.test(u)) return real(url, opts);
  if (/projects/.test(u)) return json({ items: [{ label: "Chariot", id: 1 }], default: 1 });
  if (/statuses/.test(u)) return json({ items: [
    { label: HOSTILE_LABEL, icon: HOSTILE_ICON, rgb: "javascript:alert(1)" },
    { label: "rev", icon: BAD_SPRITE, rgb: "1,2,3" }] });
  if (/entities/.test(u)) return json({ items: [{ label: "chr_010 (Shot)", id: 11 }] });
  if (/resolve/.test(u)) return json({ id: 0, why: "<b>nothing</b> matched",
    candidates: [{ code: '<script>window.__pwned = 1<\/script>',
                   status: { label: HOSTILE_LABEL, icon: BAD_SPRITE, rgb: "not a colour" } }] });
  return json({ items: [] });
};

app.graph.clear();
const n = window.LiteGraph.createNode("SGLoadVersion");
app.graph.add(n);
const project = n.widgets.find((x) => x.name === "project");
project.value = "Chariot";
project.callback("Chariot");
await wait(1800);

const chips = document.querySelector(".sg-chips");
const panel = document.querySelector(".sg-panel");
const injected = document.querySelectorAll(".sg-chips script, .sg-panel script").length;
// A dot or a pill takes a colour from the node. Nothing the site sent may set a position.
const positioned = [...document.querySelectorAll(".sg-chips [style], .sg-panel [style]")]
  .filter((e) => /position|inset|z-index/i.test(e.getAttribute("style") || "")).length;
const literal = (chips?.textContent || "").includes(HOSTILE_LABEL);
const drew = !!chips?.querySelector(".sg-dot") && !!panel?.querySelector(".sg-cand");
const ok = !window.__pwned && injected === 0 && positioned === 0 && literal && drew;
return { verdict: `${ok ? "PASS" : "FAIL"} pwned=${!!window.__pwned} scripts=${injected} `
  + `styled=${positioned} label drawn as text=${literal} sprite fell back and panel drew=${drew}` };

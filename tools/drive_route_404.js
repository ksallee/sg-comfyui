// Checks the sentence the node draws when the /sg routes are not registered, as after the pack is
// updated without a restart.
// Answers the /sg routes here with a 404 page, as the server does. No site is read.
//   tools/qa_node.py --start --repo . --node SGPublishVersion --drive tools/drive_route_404.js
const real = window.fetch.bind(window);
window.fetch = (url, opts) => {
  const u = String(url?.url ?? url);
  return /\/sg\//.test(u)
    ? Promise.resolve(new Response("<html><body>404: Not Found</body></html>",
        { status: 404, headers: { "Content-Type": "text/html" } }))
    : real(url, opts);
};

app.graph.clear();
const n = window.LiteGraph.createNode("SGPublishVersion");
app.graph.add(n);
await wait(1500);

const said = [...document.querySelectorAll(".sg-err")].map((e) => e.textContent.trim());
const ok = said.some((s) => s === "The running ComfyUI predates this version of the pack. "
  + "Restart ComfyUI, then reload this page.")
  && !said.some((s) => /SyntaxError|Unexpected token/.test(s));
return { verdict: `${ok ? "PASS" : "FAIL"} panel says "${said[0] || ""}"` };

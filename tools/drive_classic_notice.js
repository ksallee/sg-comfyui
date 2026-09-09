// The notice a node draws when Nodes 2.0 is off, and what a copy of that node is titled.
//   tools/qa_node.py --start --repo . --no-vue --node SGPublishVersion \
//     --drive tools/drive_classic_notice.js
app.graph.clear();
const n = window.LiteGraph.createNode("SGPublishVersion");
app.graph.add(n);
await wait(600);

const labels = n.widgets.filter((x) => x.type === "button").map((x) => x.name);
const notice = labels.includes("Nodes 2.0 is off. Click to open Settings, then Nodes 2.0, and turn "
  + "on Modern Node Design.");
const classic = labels.includes("The lists on this node do not update on the classic canvas.");

// Paste creates the node with the copied title, which is where a second suffix used to land.
const copy = window.LiteGraph.createNode(n.type, n.title);
app.graph.add(copy);
copy.pos = [60, 420];
await wait(300);
const suffixes = (copy.title.match(/\(needs Nodes 2\.0\)/g) || []).length;
app.graph.remove(copy);                // one node left on the canvas, for the screenshot
await wait(300);

const ok = notice && classic && suffixes === 1;
return { verdict: `${ok ? "PASS" : "FAIL"} notice=${notice} classic line=${classic} `
  + `copy titled "${copy.title}"` };

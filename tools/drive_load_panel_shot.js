// Frames one SG Load pinned to a Version so its panel rows fill the shot.
// Needs PIN prepended: the Version id to pin. Reads the Version, runs nothing.
//
//   { printf 'const PIN = 31992;\n'; cat tools/drive_load_panel_shot.js; } > /tmp/d.js
//   uv run --with playwright --python 3.11 python tools/qa_node.py --start \
//     --repo ~/dev/sg-comfyui --scale 2 --viewport 620x900 --drive /tmp/d.js --shot out.png

app.graph.clear();
await wait(400);
const ld = LiteGraph.createNode("SGLoadVersion");
ld.pos = [0, 0];
app.graph.add(ld);
const pin = ld.widgets.find((w) => w.name === "pin_version_id");
pin.value = PIN;
pin.callback?.(PIN);
app.canvas.setDirty(true, true);

const body = () => document.querySelector(".sg-panel .sg-body")?.innerText || "";
for (let i = 0; i < 60 && !/sampler/.test(body()); i++) await wait(500);
await wait(1500);

// The minimap and the toasts are chrome, not the picture.
document.querySelectorAll(".p-toast-close-button").forEach((b) => b.click());
const minimap = document.querySelector(".comfyui-minimap, [class*=minimap]");
if (minimap) minimap.style.display = "none";
await wait(300);

// Fill the canvas with the node, a small margin around it. The canvas is sized in device pixels
// and the graph transform is in CSS pixels, so the fit is measured on the element's client size.
const [nw, nh] = ld.size;
const cw = app.canvas.canvas.clientWidth, ch = app.canvas.canvas.clientHeight;
const s = Math.min(cw / (nw + 30), ch / (nh + 60));
app.canvas.ds.state.scale = s;
app.canvas.ds.state.offset = [(cw / s - nw) / 2, (ch / s - nh) / 2 + 15];
app.canvas.setDirty(true, true);
await wait(1500);

// Where the node landed on the page, so the shot can be cropped to it.
const o = app.canvas.ds.state.offset;
const at = app.canvas.canvas.getBoundingClientRect();
return {
  scale: s,
  rect: { x: Math.round(at.left + o[0] * s), y: Math.round(at.top + o[1] * s),
          w: Math.round(nw * s), h: Math.round(nh * s) },
  panel: body().replace(/\n/g, " | "),
};

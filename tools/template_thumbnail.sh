#!/usr/bin/env bash
# Writes the card image for one shipped template: load it in a real ComfyUI, frame the graph, crop
# to it.
# A custom node pack's template card is a static <name>.jpg beside the <name>.json.
# Requires playwright, as tools/smoke.py does.
#
#     tools/template_thumbnail.sh 00_example "$SCRATCH" "$PWD"
set -e
NAME="$1"; S="$2"; REPO="$3"
cat > "$S/drive_$NAME.js" <<JS
const g = await (await fetch("/api/workflow_templates/sg-comfyui/$NAME.json")).json();
await app.loadGraphData(g);
await wait(3500);
// The editor's right-hand splitter panel overlays the canvas, so the drawable width stops at its
// left edge. Fit to that, not to the canvas element, or a wide graph renders under the panel.
let limit = window.innerWidth;
for (const el of document.querySelectorAll("[class*='p-splitterpanel']")) {
  const r = el.getBoundingClientRect();
  if (r.width > 40 && r.height > 200 && r.left > window.innerWidth * 0.5) limit = Math.min(limit, r.left);
}
const ns0 = app.graph._nodes; let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
for (const n of ns0) { const [x,y]=n.pos,[w,h]=n.size;
  x0=Math.min(x0,x); y0=Math.min(y0,y-30); x1=Math.max(x1,x+w); y1=Math.max(y1,y+h); }
// Fit against the visible region, not the canvas element, which runs under the panel.
const ds=app.canvas.ds, r=app.canvas.canvas.getBoundingClientRect();
// The canvas is full-bleed and the editor's chrome overlays it: tab strip and Run bar across the
// top, icon rail down the left, zoom bar along the bottom, splitter panel on the right. These
// insets are the drawable area.
const VIS = {l: r.left + 78, t: r.top + 118, r: limit - 12, b: r.bottom - 78};
const m = 16, availW = (VIS.r - VIS.l) - m*2, availH = (VIS.b - VIS.t) - m*2;
const s = Math.min(availW / (x1 - x0), availH / (y1 - y0));
ds.scale = s;
ds.offset[0] = (VIS.l - r.left + m) / s - x0;
ds.offset[1] = (VIS.t - r.top + m) / s - y0;
if (app.canvas?.setDirty) app.canvas.setDirty(true, true);
await wait(1800);
const P=(gx,gy)=>[r.left+(gx+ds.offset[0])*ds.scale, r.top+(gy+ds.offset[1])*ds.scale];
const [ax,ay]=P(x0,y0),[bx,by]=P(x1,y1);
return {box:[Math.round(ax),Math.round(ay),Math.round(bx),Math.round(by)],
        rect:[Math.round(VIS.l),Math.round(VIS.t),Math.round(VIS.r),Math.round(VIS.b)]};
JS
cd "$REPO"
uv run --with playwright --python 3.11 python tools/qa_node.py --port 8188 \
  --drive "$S/drive_$NAME.js" --shot "$S/$NAME.png" --viewport 2800x1500 \
  | ./.venv/bin/python -c "import json,sys; d=json.load(sys.stdin); print(json.dumps([d['box'],d['rect']]))" > "$S/$NAME.box"
./.venv/bin/python - "$NAME" "$S" <<'PY'
import json, sys
from PIL import Image
name, S = sys.argv[1], sys.argv[2]
box, rect = json.load(open(f"{S}/{name}.box"))
im = Image.open(f"{S}/{name}.png").convert("RGB")
pad = 20
clipped = box[2] > rect[2] or box[3] > rect[3]
c = im.crop((max(box[0]-pad, rect[0]), max(box[1]-pad, rect[1]),
             min(box[2]+pad, rect[2]), min(box[3]+pad, rect[3])))
c = c.resize((900, int(900*c.height/c.width)), Image.LANCZOS)
c.save(f"example_workflows/{name}.jpg", "JPEG", quality=88, optimize=True)
print(f"  {name}.jpg {c.size}{'   CLIPPED' if clipped else '   full graph'}")
PY

// Opens the properties panel on the Info tab for the placed node and widens it to 780 CSS pixels,
// for the README pictures of each node's inputs. Nothing is run.
// Returns `rect`, the panel and its table in CSS pixels, and `lines`, each description's line count.
// The viewport is tall enough that `scrolled` comes back false, or the table is cut off.
//   uv run --with playwright --python 3.11 python tools/qa_node.py --start --port 8189 \
//     --node SGPublishVersion --scale 2 --viewport 2000x1400 --drive tools/drive_info_tab.js \
//     --shot /tmp/publish.png
//   uv run --with Pillow --python 3.11 python -c "from PIL import Image; x,y,w,h = 1220,38,780,995; \
//     Image.open('/tmp/publish.png').crop((2*x,2*y,2*(x+w),2*(y+h))).save('docs/images/sg-publish-info.png')"
// The same two commands with --node SGLoadVersion, --viewport 2000x1600 and h = 1268 write docs/images/sg-load-info.png.
const WIDTH = 780;

app.canvas.selectNode(node);
await wait(600);
document.querySelector("[aria-label='Toggle properties panel']")?.click();
await wait(1200);
[...document.querySelectorAll("[role=tab]")]
  .find((b) => (b.textContent || "").trim() === "Info")?.click();
await wait(800);

// The panel is one pane of a PrimeVue splitter, sized by flex-basis. The pane beside it holds the
// canvas and the Run bar, whose min-content width stops the panel at 650 unless it is released.
const panel = document.querySelector("[data-testid=properties-panel]");
const pane = panel.parentElement;
const middle = [...pane.parentElement.children].find((e) => e.classList.contains("p-splitterpanel-nested"));
middle.style.minWidth = "0px";
middle.style.overflow = "hidden";
pane.style.flex = `0 0 ${WIDTH}px`;
window.dispatchEvent(new Event("resize"));
await wait(1500);

document.querySelectorAll(".p-toast-close-button").forEach((b) => b.click());
await wait(400);

// Crop to the table, not to the pane: the pane runs to the bottom of the window whatever it holds.
// A node with outputs draws a second table, whose header row holds no cell to measure.
const rows = [...panel.querySelectorAll("tr")].filter((tr) => tr.querySelectorAll("td").length);
const p = panel.getBoundingClientRect();
const end = rows[rows.length - 1].getBoundingClientRect().bottom + 16;
// The description cell's own line height and padding, so the count comes from this shot.
const lines = rows.map((tr) => {
  const cells = tr.querySelectorAll("td");
  const d = cells[cells.length - 1];
  const cs = getComputedStyle(d);
  const inner = d.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
  return [cells[0].innerText.trim(), Math.round(inner / parseFloat(cs.lineHeight))];
});
return {
  rect: [Math.round(p.left), Math.round(p.top), Math.round(p.width), Math.round(end - p.top)],
  scrolled: panel.querySelector(".overflow-y-auto")?.scrollHeight
            > panel.querySelector(".overflow-y-auto")?.clientHeight,
  lines,
};

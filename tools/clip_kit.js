// The pointer, the pacing and the framing the drive_clip_*.js files use.
// tools/capture.py prepends this file to the drive.
// A CDP screencast emits a frame when the page paints, so the pointer's animation is what keeps
// frames coming. A still moment costs one frame, held for as long as it lasted.
const pause = (ms) => wait(ms);

// Toasts appear over the top-right corner on their own clock. Hide them.
const CLIP_STYLE = document.createElement("style");
CLIP_STYLE.textContent = '[class*="toast"] { display: none !important; }';
document.head.appendChild(CLIP_STYLE);

// ComfyUI's run card has no class of its own, so it is found by its text.
const hideRunCards = () => {
  for (const e of document.querySelectorAll("div.flex.justify-end")) {
    if (/^Job \w+$/.test((e.textContent || "").trim())) e.style.display = "none";
  }
};
new MutationObserver(hideRunCards).observe(document.body, { childList: true, subtree: true });
hideRunCards();

const CUR = document.createElement("div");
CUR.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24">'
  + '<path d="M5 2l14 9-6.2 1.1L16.4 19l-2.7 1.3-3.5-6.9L5 17z" fill="#fff" stroke="#111"'
  + ' stroke-width="1.5" stroke-linejoin="round"/></svg>';
CUR.style.cssText = "position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;"
  + "filter:drop-shadow(0 2px 4px rgba(0,0,0,.55));will-change:transform";
document.body.appendChild(CUR);

let cx = 60, cy = 60;
const at = (x, y) => { cx = x; cy = y; CUR.style.transform = `translate(${x}px,${y}px)`; };
at(cx, cy);

const paint = () => new Promise((r) => requestAnimationFrame(r));

// Move the pointer to x, y over ms, one step per animation frame.
const move = async (x, y, ms = 850) => {
  const x0 = cx, y0 = cy, t0 = performance.now();
  for (;;) {
    const t = Math.min(1, (performance.now() - t0) / ms);
    const e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    at(x0 + (x - x0) * e, y0 + (y - y0) * e);
    if (t >= 1) return;
    await paint();
  }
};

// Where to put the pointer on an element: the top of a tall control, not its middle.
const aim = (el) => {
  const r = el.getBoundingClientRect();
  return [r.left + Math.min(r.width / 2, 90), r.top + Math.min(r.height / 2, 16)];
};

const press = async () => {
  CUR.animate([{ transform: CUR.style.transform + " scale(1)" },
               { transform: CUR.style.transform + " scale(0.82)" },
               { transform: CUR.style.transform + " scale(1)" }], 240);
  await pause(300);
};

// Move to the element, show the press, click it, wait.
// The pause after a click is set here, for the clicks in every clip.
const click = async (el, ms = 850) => {
  if (!el) return false;
  const [x, y] = aim(el);
  await move(x, y, ms);
  await press();
  el.click();
  await pause(900);
  return true;
};

const type = async (inp, text, ms = 55) => {
  for (const ch of text) {
    inp.value += ch;
    inp.dispatchEvent(new Event("input", { bubbles: true }));
    await pause(ms);
  }
};

// One node row by its label. The pickers, the ticks and the fold all draw as .sg-dom.
const ctl = (label) => [...document.querySelectorAll(".sg-dom")]
  .find((d) => (d.querySelector(".sg-lab")?.textContent || "").trim().toLowerCase() === label);

// Open a picker, type a term, click the row whose text contains `want`.
// The list is fetched per keystroke and the unfiltered set is on screen until the filtered one is
// drawn, so a row is matched by text and not by position.
const pick = async (label, term, want) => {
  const c = ctl(label);
  if (!c) return false;
  await click(c.querySelector("button"), 700);
  let inp = null;
  for (let i = 0; i < 30 && !inp; i++) {
    await pause(150);
    inp = document.querySelector(".sg-pop-input");
  }
  if (inp && term) await type(inp, term);
  // A row is clicked by the index it had when the list was drawn. Wait for the response to the last
  // keystroke, or the index points into the list that keystroke replaced.
  const busy = () => document.querySelector(".sg-pop-busy")?.hidden === false;
  for (let i = 0; i < 60 && busy(); i++) await pause(250);
  let hit = null;
  for (let i = 0; i < 60 && !hit; i++) {
    await pause(250);
    hit = [...document.querySelectorAll('[role="option"]')]
      .find((r) => (r.textContent || "").toLowerCase().includes(want.toLowerCase()));
  }
  await click(hit, 700);
  // Clicking the row that is already the value leaves the list open. Close it.
  const open = document.querySelector(".sg-pop-input");
  if (open) {
    open.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await pause(250);
  }
  return !!hit;
};

// Wait for a node's height to stop changing.
// A fold or a picker relays the node out for a frame or two. Framing before that stops leaves the
// bottom of the node off screen.
const settleSize = async (n, ms = 3000) => {
  await pause(800);                 // a fold has not started to open at the moment it is clicked
  let last = -1;
  for (let t = 0; t < ms; t += 200) {
    await pause(200);
    if (n.size[1] === last) return;
    last = n.size[1];
  }
};

// Pick a value from ComfyUI's own select, which draws a fixed combo such as `format`.
// The site-backed rows are pickers: use `pick`.
const pickCombo = async (label, want) => {
  const row = [...document.querySelectorAll('[data-testid="node-widget"]')]
    .find((r) => (r.querySelector('[data-testid="widget-layout-field-label"]')?.textContent || "")
      .trim() === label);
  const trigger = row?.querySelector('[data-testid="widget-select-default-trigger"]');
  if (!trigger) return false;
  await click(trigger, 700);
  let hit = null;
  for (let i = 0; i < 30 && !hit; i++) {
    await pause(200);
    hit = [...document.querySelectorAll('[role="option"], [role="listbox"] li')]
      .find((o) => (o.textContent || "").trim() === want);
  }
  await click(hit, 700);
  return !!hit;
};

// The node's header in the editor's DOM, found by its title.
const nodeTitle = (text) => [...document.querySelectorAll('[data-testid="node-title"]')]
  .find((e) => (e.textContent || "").includes(text));

// Select one node and run up to it from the selection toolbox's button.
// That button runs one node rather than the graph.
const runNode = async (n, title) => {
  await move(...aim(nodeTitle(title) || app.canvas.canvas), 850);
  await press();
  app.canvas.selectNodes([n]);
  app.canvas.setDirty(true, true);
  await pause(1100);
  const exec = [...document.querySelectorAll("button")]
    .find((b) => /Execute to selected output nodes/i.test(b.getAttribute("aria-label") || ""));
  return click(exec, 700);
};

// Wait for the queue to empty.
const ranOut = async (tries = 150) => {
  for (let i = 0; i < tries; i++) {
    await pause(400);
    const q = await (await fetch("/queue")).json();
    if (i > 3 && !q.queue_running?.length && !q.queue_pending?.length) return;
  }
};

// Centre one node with room around it.
const frameNode = async (node, scale = 0.9) => {
  app.canvas.centerOnNode(node);
  app.canvas.ds.state.scale = scale;
  app.canvas.setDirty(true, true);
  await pause(500);
};

// The canvas size in CSS pixels.
// LiteGraph sizes its canvas in device pixels and keeps its pan offset in CSS pixels, so a capture
// above a device pixel ratio of 1 frames nothing unless the size is divided by the ratio.
const viewSize = () => {
  const d = window.devicePixelRatio || 1;
  return [app.canvas.canvas.width / d, app.canvas.canvas.height / d];
};

// All the nodes on the canvas, centred.
const frameAll = async (pad = 90) => {
  const ns = app.graph.nodes;
  const x0 = Math.min(...ns.map((n) => n.pos[0])) - pad;
  const y0 = Math.min(...ns.map((n) => n.pos[1])) - pad - 40;
  const x1 = Math.max(...ns.map((n) => n.pos[0] + (n.size?.[0] || 260))) + pad;
  const y1 = Math.max(...ns.map((n) => n.pos[1] + (n.size?.[1] || 120))) + pad;
  const [cw, ch] = viewSize();
  const s = Math.min(cw / (x1 - x0), ch / (y1 - y0), 1);
  app.canvas.ds.state.scale = s;
  app.canvas.ds.state.offset = [-x0 + ((cw / s) - (x1 - x0)) / 2, -y0 + ((ch / s) - (y1 - y0)) / 2];
  app.canvas.setDirty(true, true);
  await pause(500);
};

// Scroll a row into view and wait for the scroll to finish.
const scrollTo = async (el, ms = 1200) => {
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  await pause(ms);
};

// Settle the canvas: clear the first load's red badge and the frame counter.
// The counter is drawn on the canvas, not in the DOM. CSS cannot reach it.
const settle = async (ms = 700) => {
  app.canvas.show_info = false;
  for (const n of app.graph.nodes) n.has_errors = false;
  app.canvas.setDirty(true, true);
  await pause(ms);
};

// ComfyUI's Run button. It runs the graph, not one node.
const runButton = () => document.querySelector('[data-testid="queue-button"]')
  || [...document.querySelectorAll("button")].find((b) => /^\s*Run\s*$/.test(b.textContent || ""));

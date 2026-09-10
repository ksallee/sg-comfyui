// Records a tour of the node's controls for the README video.
// Needs the sandbox project and a link whose name contains demo.
// Paced for watching, not for asserting on: each step pauses long enough to read.
//   tools/qa_node.py --start --node SGPublishVersion --drive tools/drive_ui_tour.js --video t.webm
const pause = (ms) => wait(ms);
const seen = [];
const ctl = (label) => [...document.querySelectorAll(".sg-dom")]
  .find(d => (d.querySelector(".sg-lab")?.textContent || "").trim().toLowerCase() === label);
// Open one picker, type a term one character at a time, and take the first row offered. The
// timings are per picker, because each picker is watched for a different length of time.
const pick = async (label, term, {ms, settle, after}) => {
  const c = ctl(label);
  if (!c) return;
  c.querySelector("button")?.click(); await pause(900);
  const inp = document.querySelector(".sg-pop-input");
  if (inp) {
    for (const ch of term) { inp.value += ch;
      inp.dispatchEvent(new Event("input", {bubbles:true})); await pause(ms); }
    await pause(settle);
    const rows = document.querySelectorAll('[role="option"]');
    seen.push(label + " options: " + rows.length + " -> "
              + (rows[0]?.textContent||"").trim().slice(0,40));
    rows[0]?.click();
  }
  await pause(after);
};

await pause(1200);

// 1. the project picker, which searches rather than scrolls
await pick("project", "sandbox", {ms: 130, settle: 1100, after: 1400});

// 2. the link picker: the same control, searching the entity type the profile names
await pick("link", "demo", {ms: 150, settle: 1400, after: 1500});

// 3. the tick that decides whether files are written to disk
const files = [...document.querySelectorAll(".sg-dom")]
  .find(d => (d.textContent || "").includes("Create Published Files"));
files?.querySelector("input,button,[role=switch]")?.click();
await pause(1600);

// 4. the panel before any Run: the name the next Run would write, the latest Version published
// here, and the files it wrote
await pause(4500);
seen.push("anchors: " + [...document.querySelectorAll("a.sg-a")]
  .map(a => `${a.textContent.trim().slice(0,46)} -> ${a.href.slice(0,60)}`).join("  |  "));
return { steps: seen };

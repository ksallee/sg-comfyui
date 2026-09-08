// A tour of the node's own controls, for the README video. The body of an async function, run as
//   tools/qa_node.py --start --node FPTPublishVersion --drive tools/drive_ui_tour.js --video t.webm
// Deliberately slow: this is watched, not asserted on, so every step pauses long enough to read.
const pause = (ms) => wait(ms);
const seen = [];
const ctl = (label) => [...document.querySelectorAll(".fpt-dom")]
  .find(d => (d.querySelector(".fpt-lab")?.textContent || "").trim().toLowerCase() === label);
// Open one picker, type a term a character at a time, and take the first row offered. The timings
// are per picker because each one is watched for a different length of time.
const pick = async (label, term, {ms, settle, after}) => {
  const c = ctl(label);
  if (!c) return;
  c.querySelector("button")?.click(); await pause(900);
  const inp = document.querySelector(".fpt-pop-input");
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

// 1. the project picker: a studio site has hundreds, so it searches rather than scrolls
await pick("project", "sandbox", {ms: 130, settle: 1100, after: 1400});

// 2. the link picker: same control, and it now searches the entity type the profile named
await pick("link", "demo", {ms: 150, settle: 1400, after: 1500});

// 3. the one tick that decides whether anything lands on disk
const files = [...document.querySelectorAll(".fpt-dom")]
  .find(d => (d.textContent || "").includes("Create Published Files"));
files?.querySelector("input,button,[role=switch]")?.click();
await pause(1600);

// 4. the panel already knows what is on the site: the name the next Run would write, the latest
// Version published here, and the files it wrote — all before anything is run.
await pause(4500);
seen.push("anchors: " + [...document.querySelectorAll("a.fpt-a")]
  .map(a => `${a.textContent.trim().slice(0,46)} -> ${a.href.slice(0,60)}`).join("  |  "));
return { steps: seen };

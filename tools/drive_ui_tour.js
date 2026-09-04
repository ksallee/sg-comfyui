// A tour of the node's own controls, for the README video. Deliberately slow: this is watched, not
// asserted on, so every step pauses long enough to read before the next one moves.
const pause = (ms) => wait(ms);
const seen = [];
const ctl = (label) => [...document.querySelectorAll(".fpt-dom")]
  .find(d => (d.querySelector(".fpt-lab")?.textContent || "").trim().toLowerCase() === label);

await pause(1200);

// 1. the project picker: a studio site has hundreds, so it searches rather than scrolls
const proj = ctl("project");
if (proj) {
  proj.querySelector("button")?.click(); await pause(900);
  const inp = document.querySelector(".fpt-pop-input");
  if (inp) {
    for (const ch of "sandbox") { inp.value += ch;
      inp.dispatchEvent(new Event("input", {bubbles:true})); await pause(130); }
    await pause(1100);
    const rows = document.querySelectorAll('[role="option"]');
    seen.push("project options: " + rows.length + " -> " + (rows[0]?.textContent||"").trim().slice(0,40));
    rows[0]?.click();
  }
  await pause(1400);
}

// 2. the link picker: same control, and it now searches the entity type the profile named
const link = ctl("link");
if (link) {
  link.querySelector("button")?.click(); await pause(900);
  const inp = document.querySelector(".fpt-pop-input");
  if (inp) {
    for (const ch of "demo") { inp.value += ch;
      inp.dispatchEvent(new Event("input", {bubbles:true})); await pause(150); }
    await pause(1400);
    const rows = document.querySelectorAll('[role="option"]');
    seen.push("link options: " + rows.length + " -> " + (rows[0]?.textContent||"").trim().slice(0,40));
    rows[0]?.click();
  }
  await pause(1500);
}

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

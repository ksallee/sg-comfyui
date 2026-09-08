/* Who this ComfyUI publishes as, and the button that changes it.
 *
 * One row above the pickers on both nodes. Signed in, it names the person and the site; not signed
 * in, it takes the site address and starts the App Session Launcher flow (probe 052): the server asks
 * the site for an approval page, this opens it in a new tab, where the operator is already logged
 * into Flow PT, and the row polls until they click approve. A script key from the environment shows
 * as the script's name, and the button is still offered, because a person beats a machine.
 */
import { domRow, styleOnce, esc } from "./fpt_dom_widgets.js";

const CSS = `
.fpt-signin { font: 11px ui-monospace, SFMono-Regular, Menlo, monospace; color: #cfd3d8;
              display: flex; flex-wrap: wrap; align-items: center; gap: 6px; width: 100%;
              box-sizing: border-box; padding: 2px 0; }
.fpt-signin * { box-sizing: border-box; }
.fpt-signin .fpt-who { flex: 1 1 auto; min-width: 0; overflow-wrap: anywhere; }
.fpt-signin .fpt-who.fpt-off { color: #e0b155; }
.fpt-signin input { flex: 1 1 200px; min-width: 0; font: inherit; color: #e8ebee; background: #1b1d21;
                    border: 1px solid #35393f; border-radius: 4px; padding: 3px 6px; }
.fpt-signin button { font: inherit; color: #e8ebee; background: #2b2f35; border: 1px solid #35393f;
                     border-radius: 4px; padding: 3px 8px; cursor: pointer; white-space: nowrap; }
.fpt-signin button:hover { background: #353a41; }
.fpt-signin .fpt-note { flex: 1 1 100%; color: #7f868f; }
`;

/** One route, decoded. A failed request answers in a shape the row can show. */
async function call(url, init) {
  try {
    const r = await fetch(url, init);
    return await r.json();
  } catch (e) {
    return { error: `The ComfyUI server did not answer. ${e}` };
  }
}

const POLL_MS = 2000;      // the interval the site's own flow uses
const GIVE_UP_MS = 6 * 60 * 1000;   // the site forgets an unapproved request after about five minutes

/** Add the sign-in row to a node. `onChange` runs after a sign-in or sign-out, so the node can
 *  reload everything the site answers differently for a different caller (probe 027). */
export function addSignIn(node, onChange) {
  styleOnce("fpt-signin", CSS);
  const root = document.createElement("div");
  root.className = "fpt-signin";
  const { relayout } = domRow(node, "fpt_signin", { control: root });

  let status = null;
  let polling = 0;

  const draw = (html) => { root.innerHTML = html; relayout(); };

  const render = () => {
    const s = status || {};
    const site = s.site || "";
    if (s.how === "person" && s.alive) {
      draw(`<span class="fpt-who">Signed in as ${esc(s.who)} on ${esc(site)}.</span>` +
           `<button data-act="out">Sign out</button>`);
    } else if (s.how === "script") {
      draw(`<span class="fpt-who">Publishing as script ${esc(s.who)} on ${esc(site)}.</span>` +
           `<button data-act="in">Sign in as yourself</button>`);
    } else {
      const why = s.how === "person"
        ? "Your Flow Production Tracking sign-in has expired. Sign in again."
        : "Not signed in to Flow Production Tracking.";
      draw(`<span class="fpt-who fpt-off">${esc(why)}</span>` +
           `<input type="url" placeholder="https://yourstudio.shotgrid.autodesk.com" ` +
           `value="${esc(site)}" spellcheck="false">` +
           `<button data-act="in">Sign in</button>`);
    }
  };

  const note = (text) => {
    let n = root.querySelector(".fpt-note");
    if (!n) {
      n = document.createElement("span");
      n.className = "fpt-note";
      root.appendChild(n);
    }
    n.textContent = text;
    relayout();
  };

  const load = async () => {
    status = await call("/fpt/session");
    render();
  };

  const signIn = async () => {
    const input = root.querySelector("input");
    const site = input ? input.value.trim() : (status && status.site) || "";
    // Opened on the click, before any await, so the browser treats it as the operator's own tab
    // rather than a pop-up; the address is filled in once the site has issued it.
    const tab = window.open("", "_blank");
    const d = await call("/fpt/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ site }),
    });
    if (!d.url) {
      tab && tab.close();
      note(d.error || "The site did not issue a sign-in page. Check the address, then try again.");
      return;
    }
    if (tab) tab.location = d.url; else window.open(d.url, "_blank");
    note("Approve the sign-in in the tab that opened, then come back here.");
    const mine = ++polling;
    const started = Date.now();
    while (mine === polling && Date.now() - started < GIVE_UP_MS) {
      await new Promise((r) => setTimeout(r, POLL_MS));
      const p = await call(`/fpt/login?request_id=${encodeURIComponent(d.request_id)}`);
      if (p.state === "approved") {
        await load();
        onChange?.();
        return;
      }
      if (p.state === "gone") {
        note("That sign-in page has expired. Click Sign in again.");
        return;
      }
    }
    if (mine === polling) note("Nobody approved the sign-in. Click Sign in to get a new page.");
  };

  const signOut = async () => {
    polling++;
    await call("/fpt/logout", { method: "POST" });
    await load();
    onChange?.();
  };

  root.addEventListener("click", (ev) => {
    const act = ev.target && ev.target.dataset && ev.target.dataset.act;
    if (act === "in") signIn();
    if (act === "out") signOut();
  });
  root.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && ev.target.tagName === "INPUT") signIn();
  });

  load();
  return { reload: load };
}

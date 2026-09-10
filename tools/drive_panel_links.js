// Checks that the panel renders the Version and the file path from a publish as anchors, not as
// escaped text.
// The payload below is a fixture. No site is read.
//   tools/qa_node.py --start --node SGPublishVersion --drive tools/drive_panel_links.js
const n = app.graph.nodes.find(x => x.type === "SGPublishVersion");
if (!n) return { error: "no publish node in graph" };
app.api.dispatchEvent(new CustomEvent("executed", { detail: {
  node: String(n.id),
  output: {
    text: ["demo_01_roto_matte_v006 -> Version 31875",
           "3 frames: demo_01_roto_matte_v006.%04d.png -> PublishedFile 6871"],
    published: [{
      code: "demo_01_roto_matte_v006", id: 31875, link: "Shot demo_01_roto", status: "",
      outputs: ["sg_ai_generator","sg_ai_model","sg_ai_prompt"],
      media: "3 frames at 25 fps — encoded by ComfyUI",
      site_url: "https://kevinsallee.shotgrid.autodesk.com",
      files: [{ kind: "frames", count: 3,
                path: "/Volumes/FPT/demo_01_roto/matte/v006/demo_01_roto_matte_v006.%04d.png" }]
    }]
  }
}}));
await wait(700);
const anchors = [...document.querySelectorAll("a.sg-a")].map(a => ({ text: a.textContent, href: a.href }));
return { anchors, count: anchors.length };

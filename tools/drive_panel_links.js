// Feed the panel exactly what the node returned from the real publish, and confirm it renders
// the Version and the file path as anchors rather than escaped text.
const n = app.graph.nodes.find(x => x.type === "FPTPublishVersion");
if (!n) return { error: "no publish node in graph" };
app.api.dispatchEvent(new CustomEvent("executed", { detail: {
  node: String(n.id),
  output: {
    text: ["demo_01_roto_matte_v006 -> Version 31875",
           "3 frames: demo_01_roto_matte_v006.%04d.png -> PublishedFile 6871"],
    published: [{
      code: "demo_01_roto_matte_v006", id: 31875, link: "Shot demo_01_roto", status: "",
      outputs: ["sg_ai_generator","sg_ai_model","sg_ai_prompt"],
      media: "3 frames at 25 fps — encoded by ComfyUI — VideoInput.save_to",
      site_url: "https://kevinsallee.shotgrid.autodesk.com",
      files: [{ kind: "frames", count: 3,
                path: "/Volumes/FPT/demo_01_roto/matte/v006/demo_01_roto_matte_v006.%04d.png" }]
    }]
  }
}}));
await wait(700);
const anchors = [...document.querySelectorAll("a.fpt-a")].map(a => ({ text: a.textContent, href: a.href }));
return { anchors, count: anchors.length };

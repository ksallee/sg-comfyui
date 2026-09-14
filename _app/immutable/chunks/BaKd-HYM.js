const n=`### ComfyUI Manager

Open **Manager**, then **Custom Nodes Manager**. Search for \`Flow Production Tracking\`. Press
**Install**. Restart ComfyUI.

### The Registry

Coming soon.

### A checkout

\`\`\`sh
cd ComfyUI/custom_nodes
git clone https://github.com/ksallee/sg-comfyui.git
cd sg-comfyui
<comfy-python> -m pip install -r requirements.txt
\`\`\`

Restart ComfyUI.

\`<comfy-python>\` is the interpreter ComfyUI runs on. Check the install with it:

\`\`\`sh
<comfy-python> tools/doctor.py
\`\`\`
`,t=`| requirement | value |
|---|---|
| ComfyUI | 0.34.0 or newer |
| Python | 3.11 |
| Site | a Flow Production Tracking site you can log into |
| Client | \`sg-groundtruth\`, installed by \`requirements.txt\` |
`;export{n as i,t as r};

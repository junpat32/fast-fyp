// Copies FAST's app icon, splash and favicon from the art kit's output (../assets/app, made by
// tools/asset_generation/app_icons.py, D-91) into this project, which app.json must reference from
// inside the project. The kit stays the one source: run `npm run sync-art` after the art changes.
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const kit = join(here, "..", "..", "assets", "app");
const out = join(here, "..", "assets", "images");
const files = { "icon.png": "fast-icon.png", "adaptive-icon.png": "fast-adaptive-icon.png",
                "splash.png": "fast-splash.png", "favicon.png": "fast-favicon.png" };

mkdirSync(out, { recursive: true });
for (const [from, to] of Object.entries(files)) {
  copyFileSync(join(kit, from), join(out, to));
  console.log(`${from} -> assets/images/${to}`);
}

// The web build only (Claude's screen checks in the browser): Skia draws there with CanvasKit, which
// loads canvaskit.wasm from public/ (components/home/scene-host.web.tsx, D-113). The phone doesn't use it.
const wasm = join(here, "..", "node_modules", "canvaskit-wasm", "bin", "full", "canvaskit.wasm");
mkdirSync(join(here, "..", "public"), { recursive: true });
copyFileSync(wasm, join(here, "..", "public", "canvaskit.wasm"));
console.log("canvaskit.wasm -> public/canvaskit.wasm");

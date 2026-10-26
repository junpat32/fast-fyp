"""Build the kit: every piece x {afternoon, morning, night} -> PNG, plus manifest and palettes.

    .venv\\Scripts\\python -m tools.asset_generation.build      # build + validate + previews

Output: assets/isometric/<time>/<folder>/<name>.png, assets/isometric/manifest.json,
assets/isometric/palettes.json, assets/isometric/characters.json (avatars, skin tones, glasses),
assets/isometric/scenes/home_g0..4.json and room.json (layout for the app);
previews in tools/asset_generation/previews/.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from .characters import characters_json
from .geometry import CELL_H, CELL_W, struct_canvas
from .palette import NAMES, TIMES, palettes, to_rgba
from .kit import APPROVED, BATCH1, PIECES
from .scenes import LEVEL_NAMES, room_json, scene_json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "isometric"
PREVIEWS = Path(__file__).resolve().parent / "previews"


def render_all() -> dict:
    return {p.name: p.render() for p in PIECES}


def save_png(rgba, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(path, format="PNG", optimize=False)


def build(out: Path = OUT) -> dict:
    rendered = render_all()
    entries = []
    for k, p in enumerate(PIECES):
        idx = rendered[p.name]
        files = {}
        for t in TIMES:
            rel = Path(t) / p.folder / f"{p.name}.png"
            save_png(to_rgba(idx, t), out / rel)
            files[t] = rel.as_posix()
        tile = p.kind == "tile"
        w, h, origin = (CELL_W, CELL_H, (0, 0)) if tile else struct_canvas(p.cells)
        assert idx.shape == (h, w), f"{p.name}: rendered {idx.shape}, expected {(h, w)}"
        entries.append({
            "name": p.name, "folder": p.folder, "kind": p.kind,
            "canvas": [w, h], "footprint_origin": list(origin),
            "cells": list(p.cells), "files": files, "placeholder": False, "note": p.note,
            "batch": 1 if k < BATCH1 else 2,
            "approved": k < BATCH1 or p.name in APPROVED,      # batch 2: drafts until Patrick approves
        })
    manifest = {
        "kit": "FAST isometric kit: batch 1 (structural + terrain + neighbourhood) and batch 2 (room furniture, "
               "interactive objects and decorations, bed plants, the tree, garden decorations, six avatars, "
               "chickens; D-84 to D-86)",
        "status": "final art for the FYP (D-54, D-55); code-generated, declared in docs/ai_use_log.md. "
                  "Batch-2 pieces are drafts ('approved': false) until Patrick approves the previews",
        "specs": ["docs/assets/FAST_ART_STYLE_GUIDE.md", "docs/assets/FAST_CODE_ASSET_SPEC.md",
                  "DECISIONS D-51 to D-59"],
        "grid": {"cell": [CELL_W, CELL_H],
                 "diamond_rows": "y = 0..31: x from 31-2j to 32+2j, j = min(y, 31-y) (D-57)",
                 "placement": "draw at map_origin + ((gx-gy)*32, (gx+gy)*16) - footprint_origin, where "
                              "(gx, gy) is the piece's back cell; ground tiles first, then the neighbourhood "
                              "(behind the home plot), then the home plot's structures back-to-front by gx+gy"},
        "times": {"morning": "06:00-11:59", "afternoon": "12:00-18:59", "night": "19:00-05:59"},
        "palette_order": NAMES,
        "pieces": entries,
    }
    manifest["scenes"] = {}
    (out / "scenes").mkdir(parents=True, exist_ok=True)
    for level in LEVEL_NAMES:
        rel = f"scenes/home_g{level}.json"
        (out / rel).write_text(json.dumps(scene_json(level)), encoding="utf-8")
        manifest["scenes"][str(level)] = rel
    (out / "scenes" / "room.json").write_text(json.dumps(room_json()), encoding="utf-8")
    manifest["scenes"]["room"] = "scenes/room.json"
    (out / "characters.json").write_text(json.dumps(characters_json(), indent=1), encoding="utf-8")
    manifest["characters"] = "characters.json"            # avatars' frames, skin tones, glasses (D-86)
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out / "palettes.json").write_text(json.dumps(palettes(), indent=2), encoding="utf-8")
    return manifest


def main():
    from . import preview, validate
    manifest = build()
    n = len(manifest["pieces"])
    print(f"built {n} pieces x {len(TIMES)} times = {n * len(TIMES)} PNGs -> {OUT}")
    ok = validate.main()
    preview.main()
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()

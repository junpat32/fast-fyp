"""Automated validation (style guide §14, asset spec 'Validation Requirements').

Checks every PNG in the manifest, reading the files back from disk:
  V1  file exists, PNG, RGBA, canvas size as in the manifest
  V2  alpha is only 0 or 255 (no half-transparent edges)
  V3  every opaque colour is in that time's palette (so no anti-aliasing / stray colours)
  V4  ground tiles: opaque pixels == the D-57 diamond, pixel for pixel
  V5  the diamond tiles the plane with no gaps and no overlaps (independent check, D-57)
  V6  structures: wall heights (96 px back walls, 12 px cut-away front), nothing below the footprint
  V7  lighting: the lit (left-facing) wall face is brighter than the shaded (right-facing) one
  V8  lowercase snake_case names, files in the folder the manifest says
  V9  rebuilding gives byte-identical files (deterministic)
Report: tools/asset_generation/previews/validation_report.md
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from .palette import TIMES, palettes

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "assets" / "isometric"
REPORT = Path(__file__).resolve().parent / "previews" / "validation_report.md"


def diamond_rows() -> np.ndarray:
    """D-57 diamond written out independently of geometry.py."""
    m = np.zeros((32, 64), bool)
    for y in range(32):
        j = min(y, 31 - y)
        m[y, 31 - 2 * j:32 + 2 * j + 1] = True
    return m


def tiles_perfectly(mask: np.ndarray, n: int = 8) -> bool:
    H, W = 32 * (n + 2), 64 * (n + 2)
    cover = np.zeros((H, W), int)
    for gx in range(n):
        for gy in range(n):
            x, y = (gx - gy) * 32 + W // 2 - 32, (gx + gy) * 16 + 16
            cover[y:y + 32, x:x + 64] += mask
    inner = cover[32 * 3:32 * 5, W // 2 - 64:W // 2 + 64]
    return bool(inner.min() == 1 and inner.max() == 1)


def _hex_set(time):
    return {tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for h in palettes()[time].values()}


def _lum(rgb):
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


def check(manifest: dict, kit: Path = KIT) -> list[tuple[str, str, bool, str]]:
    res = []
    add = lambda cid, what, ok, note="": res.append((cid, what, bool(ok), note))   # noqa: E731
    dm = diamond_rows()
    add("V5", "diamond tiles with no gaps or overlaps", tiles_perfectly(dm), "8x8 tiled patch, every pixel covered once")
    pal = {t: _hex_set(t) for t in TIMES}
    snake = re.compile(r"^[a-z][a-z0-9_]*$")
    for e in manifest["pieces"]:
        name = e["name"]
        add("V8", f"{name}: snake_case name", snake.match(name))
        for t, rel in e["files"].items():
            p = kit / rel
            if not p.exists():
                add("V1", f"{name} [{t}] exists", False, rel)
                continue
            img = Image.open(p)
            ok1 = img.format == "PNG" and img.mode == "RGBA" and list(img.size) == e["canvas"]
            add("V1", f"{name} [{t}] PNG RGBA {e['canvas'][0]}x{e['canvas'][1]}", ok1, f"{img.mode} {img.size}")
            add("V8", f"{name} [{t}] folder", rel == f"{t}/{e['folder']}/{name}.png", rel)
            a = np.asarray(img.convert("RGBA"))
            alpha = a[..., 3]
            add("V2", f"{name} [{t}] alpha only 0/255", np.isin(alpha, (0, 255)).all())
            cols = {tuple(c) for c in a[alpha == 255][:, :3].tolist()}
            stray = cols - pal[t]
            add("V3", f"{name} [{t}] palette colours only", not stray, f"{len(stray)} stray" if stray else "")
            if t != "afternoon":
                continue
            opaque = alpha == 255
            if e["kind"] == "tile":
                add("V4", f"{name}: footprint == D-57 diamond", (opaque == dm).all(),
                    f"{int((opaque != dm).sum())} pixels differ" if (opaque != dm).any() else "")
            else:
                fx, fy = e["footprint_origin"]
                # pieces on the cell's bottom edges legitimately reach past it: the outside corner's
                # 4 px wall (a + b up to 36) and the outer border corner's half-width edge (up to 33)
                allow = 4 if "outside_corner" in name else 2 if "border_corner_outer" in name else 0
                below = opaque[fy + 16 * sum(e["cells"]) + allow:, :]     # footprint bottom: 32 px for 1 x 1
                add("V6", f"{name}: nothing below the footprint", not below.any())
                if name in ("wall_left", "wall_right", "wall_cutaway_front_left", "wall_cutaway_front_right"):
                    want = 12 if "cutaway" in name else 96
                    col = fx + (16 if name.endswith("left") else 48)          # a column through the face
                    rows = np.flatnonzero(opaque[:, col])
                    span = rows.max() - rows.min() + 1
                    add("V6", f"{name}: height {want} px (+ cap/outline)", want <= span <= want + 4, f"{span} px")
    # V7 lighting on the inside corner: right half (lit face) brighter than left half (shaded face)
    e = next(p for p in manifest["pieces"] if p["name"] == "wall_inside_corner")
    a = np.asarray(Image.open(kit / e["files"]["afternoon"]).convert("RGBA"))
    fx, fy = e["footprint_origin"]
    mid = slice(fy - 60, fy - 20)
    lum = lambda reg: np.mean([_lum(c) for c in reg.reshape(-1, 4)[reg.reshape(-1, 4)[:, 3] == 255][:, :3]])  # noqa: E731
    left, right = lum(a[mid, fx + 4:fx + 28]), lum(a[mid, fx + 36:fx + 60])
    add("V7", "lit (left-facing) wall brighter than shaded (right-facing)", right > left,
        f"lit {right:.0f} vs shaded {left:.0f}")
    return res


def deterministic() -> bool:
    from .build import build
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        build(Path(d1))
        build(Path(d2))
        files = sorted(p.relative_to(d1) for p in Path(d1).rglob("*.png"))
        return all((Path(d1) / f).read_bytes() == (Path(d2) / f).read_bytes() for f in files)


def main() -> bool:
    manifest = json.loads((KIT / "manifest.json").read_text(encoding="utf-8"))
    res = check(manifest)
    res.append(("V9", "rebuild is byte-identical", deterministic(), ""))
    fails = [r for r in res if not r[2]]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Asset validation report", "",
             f"**{len(res) - len(fails)} / {len(res)} checks passed.**", "",
             "| Check | What | Result | Note |", "|---|---|---|---|"]
    lines += [f"| {c} | {w} | {'PASS' if ok else '**FAIL**'} | {n} |" for c, w, ok, n in res]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"validation: {len(res) - len(fails)}/{len(res)} passed" + (f"; FAILED: {[f[1] for f in fails][:8]}" if fails else ""))
    return not fails


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)

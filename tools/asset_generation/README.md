# FAST isometric asset generator (T-22)

Code-generated **final** game art for the FYP (D-54, D-55). Every pixel comes from the Python
in this folder; there is no image model and no external image. Specs: `docs/assets/*`,
DECISIONS D-51 to D-57, `docs/game_design.md` §12.

```bash
.venv\Scripts\python -m tools.asset_generation.build
.venv\Scripts\python -m pytest tests/test_assets.py -q
```

`build` renders every piece for morning, afternoon and night, writes
`assets/isometric/<time>/<folder>/<name>.png` with `manifest.json` and `palettes.json`, runs the
validator and redraws the previews. It is light: Pillow and NumPy only, a few seconds, safe on
the 4 GB laptop.

## Files

| File | What it does |
|---|---|
| `palette.py` | 31 named colours (style guide + a few in the same families); morning and night are colour transforms of the afternoon set, plus lit windows at night (D-52) |
| `geometry.py` | Exact isometric projection, the D-57 diamond, `Box` drawing with lighting, the depth-buffered `Face` renderer (sloped roofs, wheels), outlines |
| `pieces.py` | Textures and the 48 batch-1 pieces (`PIECES`): 41 structural/terrain + 6 neighbourhood + the chicken coop |
| `creatures.py` | Animated animals as part-based pixel templates (D-66); the test chicken and its GIFs |
| `scenes.py` | The home layout (D-58, D-59): 7 × 7 room, fixed neighbours behind and to both sides, garden growing down the screen, per garden level 0–4 |
| `build.py` | Renders all pieces, writes PNGs + manifest + palettes |
| `validate.py` | 9 automated checks (V1–V9) → `previews/validation_report.md` |
| `preview.py` | Contact sheet; phone-screen scene (G3, with and without grid) at true phone pixels; garden levels 0–4; time of day |

## Previews (`previews/`)

| File | What it shows |
|---|---|
| `alignment_test.png`, `alignment_test_grid.png` | G3 home scene at 1080 × 2400, exactly what the Redmi shows at 2× (copy it to the phone to view it full screen) |
| `garden_levels.png` | Before the garden, then G1–G4: the tended garden growing to fill the screen |
| `time_of_day.png` | Morning, afternoon, night (G3) |
| `garden_growth.png` | The bed growing after G4: 6 months, 12 months, complete (D-61) |
| `contact_sheet.png` | Every piece: one-cell pieces at 3×, multi-cell pieces at 1× |

## Geometry (the invariants)

- One cell is a 64 × 32 diamond. Row `y` (0–31) covers `x = 31−2j … 32+2j`, `j = min(y, 31−y)`
  (D-57): 1,024 pixels, and it tiles at (±32, ±16) with no gaps or overlaps.
- Ground point `(a, b)` at height `h` → screen `x = 32 + 2a − 2b`, `y = a + b − h`, with
  `a, b ∈ [0, 16)` inside a cell. Pixels are sampled at their centres, which reproduces the
  diamond exactly and never lands on a boundary, so there are no rounding ties.
- Pieces are drawn as **palette indices** (−1 = transparent) and only then mapped to colours:
  no anti-aliasing and no stray colours are possible.
- Lighting: top lightest, the face pointing down-left lighter, the face pointing down-right darker.
- **World scale:** 1 cell = 1 m. A ground unit is ~2.24 px on screen but a height unit is 1 px,
  so 1 m of height = 39 px (the 96 px walls are 2.45 m). Anything round (wheels) needs different
  radii along the ground and up, or it looks squashed (`M_H`, `M_G` in `pieces.py`). Doors are
  80 px (2.05 m); window tops line up with them (D-60).
- **Layout for the app:** `build` also writes `assets/isometric/scenes/home_g0..4.json` from
  `scenes.py` (ground, neighbourhood and structures as `[gx, gy, piece]` in drawing order);
  `test_exported_scenes_match_the_layout` keeps them in step with the previews. In the app the
  scene opens fitted to the width at 2×, pinch to 3× and drag (D-60).
- **Bed growth (D-61, D-63, D-68):** the bed is a rectangle alongside the straight path (along gy
  from the garden door), growing with time only: 2 × 2 dug starter bed at G1, 2 × 3, 3 × 3, 3 × 4
  at G2–G4, then one row per qualifying month to 5 × 6 (4 steps, `BED_SIZE` / `BED_GROWTH` in
  `scenes.py`). `previews/garden_journey.png` shows the whole sequence. A path loop goes all the way
  round the bed (`bed_loop`, D-64). `home_g4.json` has `bed_growth`: for step k, paint
  `bed_growth[0..k-1].cells` as `garden_soil_improved`, then `bed_growth[k-1].loop` as
  `path_nice_paved`, and swap all `garden_border_*` structures for `bed_growth[k-1].edging`. `previews/garden_growth.png`
  shows 6 months, 9 months and complete.
- **Animal homes (D-67):** each layout file has `animal_homes` (e.g. the chicken coop, its cell,
  size and the `sleep_cell` where the animals sleep at night). The app adds a home only for the
  animals the user has chosen, then sorts structures by their front cell. The previews assume
  chickens from G2.
- Boxes are drawn in painter's order. Shapes boxes can't make use `Face` (a flat quad or
  triangle) with a depth buffer: for every pixel the renderer solves where its line of sight meets
  the face (one 3 × 3 system per face) and keeps the nearest.
- Textures depend only on the position inside a cell, so neighbouring tiles join seamlessly.
  Ground that covers large areas (wild ground, lawns, soil) uses pixel-scale noise only: any
  bigger feature repeats every tile and shows as a lattice across a full screen.

## Placement in the app

| Kind | Canvas | `footprint_origin` |
|---|---|---|
| Ground tile (floor, terrain, path) | 64 × 32 | (0, 0) |
| Structure (wall, trim, border, planter, fence, 1 × 1 prop) | 80 × 152 | (8, 112) |
| Multi-cell structure, W × D cells (houses 5 × 5, motorbike and washing line 1 × 2) | 32(W+D)+16 × 120+16(W+D) | (32(D−1)+8, 112) |

Draw each asset at `map_origin + ((gx − gy)·32, (gx + gy)·16) − footprint_origin`, where
`(gx, gy)` is the piece's back cell. Draw all ground tiles first, then the neighbourhood (it is
entirely behind the home plot, sorted by its front cell), then the home plot's structures back to
front by `gx + gy`. The manifest repeats this rule.

Neighbours are **fixed scenery** (D-59): `scenes.py` gives them the same houses, porches and props
at every level, and `test_neighbourhood_is_fixed` checks it.

Walls, cut-away front walls and borders are **run pieces**. Their outline is only on the top
edge, and it is computed as if the previous piece in the run were present. Without that, the back
end of each cap gets outlined and shows as a small tick in the middle of the wall top at every
join (`test_run_has_one_continuous_top_outline` guards this). A wall run should start at
`wall_inside_corner`. Without one, the first piece's back cap end has no outline.

| Piece family | Where it sits |
|---|---|
| Back walls (`wall_left/right`, doors, windows) | Outside the room, on the cell's top edges (thickness reaches behind the cell) |
| Front walls (`wall_cutaway_front_*`) | Inside the room, on the cell's bottom edges, 12 px high; draw after anything else in the same cell |
| Fences, borders | **Centred on the cell edge.** Fence posts at cell corners are shared, so the end post of one piece is the start post of the next; borders overlap by half a unit. A bed's front edges use straights placed on the cells in front of it, and its corners close by themselves |

## Adding a piece

1. Add a `_p(name, folder, kind, render_fn, note)` entry to `PIECES` in `pieces.py`
   (lowercase snake_case; `kind` is `"tile"` or `"struct"`).
2. Use palette names from `palette.py` only. For a new colour, add it to `BASE`; morning and
   night follow automatically.
3. Rebuild, check `validation: N/N passed`, and look at `previews/contact_sheet.png`.
4. Run `pytest tests/test_assets.py`. `test_files_on_disk_match_the_code` fails if you forgot to
   rebuild. Update the name count in `test_names_are_unique_snake_case`.

## Validation (V1–V9)

V1 PNG, RGBA and size · V2 alpha only 0/255 · V3 palette colours only · V4 ground tiles equal the
D-57 diamond exactly · V5 the diamond tiles with no gaps or overlaps · V6 wall heights (96 px back,
12 px front) and nothing below the footprint · V7 the lit wall face is brighter than the shaded one · V8
snake_case names in the right folders · V9 a rebuild is byte-identical.

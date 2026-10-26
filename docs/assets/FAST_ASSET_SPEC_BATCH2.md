# FAST asset spec, batch 2: furniture, interactive objects, garden, characters

**Binding spec** for T-22 batch 2 (D-72). It replaces the three AI-prompt drafts
(`docs/assets/archive/FAST_AI_*_PROMPT.md`): their lists are merged here, corrected to match
FAST's decisions, and turned into exact numbers. All art is **made in code** in the same style
as batch 1 (D-55, D-83): no image generation. **Restarted 2026-10-14 (D-84)** in
`tools/asset_generation/furniture.py`; Patrick approves the previews.

Batch 2 starts **after T-14b** (F2). Game rules behind these assets: `docs/game_design.md` v1.6.

---

## 1. Technical standard (binding for every asset; same as batch 1)

| Item | Rule |
|---|---|
| View | 2D isometric pixel art, 2:1. Ground point (a, b, h) → screen x = 32 + 2a − 2b, y = a + b − h |
| Grid | 64 × 32 cells, the D-57 diamond; 1 cell = **1 m**; 16 ground units per cell |
| Height | **39 px per metre** (D-59). Round things use different radii along the ground and up |
| Canvas | 1 × 1: 80 × 152, base point (8, 112). W × D cells: 32(W+D)+16 × 120+16(W+D), base point (32(D−1)+8, 112). Wall items: the wall pieces' canvas |
| Light | From the **upper left**: tops lightest; faces pointing down-left lighter; faces pointing down-right darker |
| Colours | **FAST palette only** (`tools/asset_generation/palette.py`); new colours are added there in families, never ad hoc |
| Outline | 1 px: `outline` (#49311F) for the room; `outline_soft` (#5B3D28) for garden, props, animals and characters |
| Pixels | 1 art pixel = 1 image pixel; **no anti-aliasing**; alpha only 0 or 255 |
| Time of day | Morning / afternoon / night by **palette swap** (D-52): drawn as palette indices |
| Night glow | **Lamps and lanterns** glow at night (desk lamp, floor lamp, garden lamp, lantern); windows are lit; nothing else glows (E3) |
| Shadows | **None**, except a small flat shadow under characters and animals (2 rows, `recess` colour at night-safe values) (E2) |
| Facing | Draw **one facing and flip** it for the other (C5). **Wall items** in left-wall and right-wall versions |
| Placement | By the piece's back cell; drawn back to front by its front cell (`scenes.py`) |
| Names | lowercase snake_case, folder per group, listed in `assets/isometric/manifest.json` with cells and base point |
| Validation | The existing checks V1–V9 plus tests (`tests/test_assets.py`) |

## 2. Scale table (heights at 39 px/m; footprints in cells, Claude's call, Patrick reviews: C6)

| Object | Footprint | Height |
|---|---|---|
| Character (chibi) | 1 × 1 | **56 px** (B3) |
| Chicken | 1 × 1 | 27 px (built, 1.5× real) |
| Door / window top | wall | 80 px (D-60) |
| Mattress on the floor | 1 × 2 | 8 px |
| Single bed with simple bedding | 1 × 2 | 18 px (headboard 31) |
| Folding table / coffee table | 1 × 1 | 18 px |
| Desk (compact study/work) | 1 × 1 | 29 px |
| Office chair / dining chair | 1 × 1 | 35 px (back) |
| Desk lamp | on the desk | +18 px |
| Wardrobe | 1 × 1 | 74 px |
| Crate shelf (starter, opens the assistant) | 1 × 1 | 23 px |
| Bookshelf (full, opens the assistant) | 1 × 1 | 70 px |
| Two-seat sofa | 1 × 2 | 31 px |
| Kitchen counter with sink | 1 × 1 | 35 px |
| Compact fridge | 1 × 1 | 55 px |
| Stove | 1 × 1 | 35 px |
| Storage cabinet | 1 × 1 | 35 px |
| Dining table | 1 × 1 | 29 px |
| Shoe rack (by the entrance door) | 1 × 1 | 23 px |
| Floor lamp | 1 × 1 | 62 px |
| Potted plant / big plant | 1 × 1 | 27 / 59 px |
| Rug | 2 × 2 floor overlay | 1 px |
| Wall items (wall shelf, budget board, wall art, curtains, window view) | wall | between 40 and 80 px up the wall |
| Garden bench | 1 × 2 | 18 px (back 31) |
| Garden lamp / lantern | 1 × 1 | 47 / 20 px |
| Bird bath / fountain | 1 × 1 / 2 × 2 | 31 / 39 px |
| Garden arch | 1 × 2 | 86 px |
| Outdoor table / chair | 1 × 1 | 29 / 35 px |
| Mailbox / bicycle rack | 1 × 1 / 1 × 2 | 43 / 31 px |
| Decorative stones | 1 × 1 | 12 px |
| Tree (7 stages) | 2 × 2 when grown | from a 4 px mound to ~100 px (compressed from real size, as isometric games do) |
| Bed plants (one per bed cell) | 1 × 1 | seedling 6 px · young 12 px · full 18–24 px (frangipani and torch ginger up to ~55 px; jade vine ~37 px with its trellis, D-86) |

## 3. Room: furniture by level, and decoration choices (C1, C2, C7)

**Levels** (unlocked by the cushion, game_design §7):

| Level | Unlocks at | Furniture |
|---|---|---|
| 1 Starter | Start | Mattress on the floor, folding table, worn wood floor, bare window, kitchen counter with sink, shoe rack by the door, **crate shelf** (opens the AI assistant, J1), **budget board**, **coin jar**, **savings plant** |
| 2 Settling in | 0.5 month | Single bed with simple bedding, desk, office chair, desk lamp |
| 3 Home | 1 month | Wardrobe, rug, wall shelf, potted plant, light wood floor; the garden door opens |
| 4 Comfortable | 2 months | Two-seat sofa, coffee table, **bookshelf** (the crate shelf grows into it; still opens the assistant), compact fridge, stove, curtains |
| 5 Cosy | 3 months | Wall art, floor lamp, big plant, window view |

**Decoration choices** (1 choice per 200 points, D-69): dining table + dining chair, storage cabinet,
and about **11 colour variants** of curtains, rugs, wall art, desk plants and bedding.

## 4. Interactive objects (C3, C4)

Tapping an interactive object opens its screen.

| Object | Opens | States |
|---|---|---|
| **Budget board** (wall) | Budgets | One look |
| **Coin jar** (on the folding table, later the desk) | Savings / cushion | 5 fills: game cushion 0, 0.5, 1, 2, 3+ months. It shows the **current** cushion, like the dashboard |
| **Savings plant** (pot by the window) | Savings history | Grows with the total months saved ≥ 5% of income: sprout, then 1, 2, 3, 6 months (never shrinks); droops in "really bad" months (§6) |
| **Crate shelf → bookshelf** | The **AI assistant** (Groq, ships, C3e) | Crate shelf from level 1, bookshelf from level 4 |

Dropped for now (receipt scanner station, financial-risk warning lamp): see
`docs/assets/DROPPED_ITEMS.md`.

## 5. Garden (D1–D6)

**Time** (qualifying months) decides what exists: bed size, plant tiers, animal types. **Points**
decide which plants and how many, the tree, and decorations (D-69, D-74).

**Bed plants** (one per bed cell; the user **taps a bed cell, picks a plant, and it is planted**, K1):

| Tier (unlocked by qualifying months) | Plants |
|---|---|
| 1, at the garden opening | serai, pandan, chilli |
| 2, at 4 | bunga raya, bougainvillea, ixora |
| 3, at 12 | orchids, frangipani |
| 4, at 24 | torch ginger (bunga kantan), jade vine (on its own bamboo trellis in its bed cell; the garden arch is a separate decoration, D-86) |

Each plant has **3 growth stages** (seedling, young, full) and a **drooping** version of each
(visibly droopy; never dead, never gone; §6). Plus free **seedlings** for empty bed cells (D-69).

**Growth:** bought with a choice, a plant grows through its stages on **growing days**: a day
counts when the latest monthly result is not **really bad** (D-75; was "not Red", I1). Seedling → young: **7** growing days;
young → full: **14** more (I2). The tree takes about **14 growing days per stage** (I3).

**Tree:** 7 stages (mound, sprout, sapling, young, medium, mature, flowering mature), bought with a
choice. **Shrubs and garden plants:** small, medium and full shrub, tropical leafy plant, small
flowering bush, outdoor potted plant.

**Decorations** (bought with choices): simple and improved bench, garden lamp, lantern, bird bath,
decorative stones, garden arch, outdoor table and chair, mailbox, bicycle rack, simple fountain.
Placement: the garden **highlights 2–3 suitable free spots** and the user taps one (K2); it can be
moved later the same way (K3). The spots come from `scenes.decor_spots` (`decor_free_cells` in
`home_g*.json`, D-86). The tree has one fixed 2 × 2 spot from G4. Paths and the bed are never blocked. The planter boxes and herb
planter from the old prompt are dropped: batch 1's planters cover them (D5).

## 6. "Really bad" months (D-73)

"Really bad" = **Red band AND** (ran short of money this month **or** forecast risk ≥ 2× the usual).

| What | Shows |
|---|---|
| Character ("You now") | **Concerned but hopeful**, with one next step on screen |
| Plants (bed, tree, savings plant) | **Visibly droopy**; they never die, disappear or drop a stage, and they recover **when the situation is better** |
| Animals | Unaffected: happy |
| Future Self ("You in 6 months") | **Never** concerned (D-12) |
| Levels, bed, points | Never go down |

## 7. Characters (B, L)

| Item | Spec |
|---|---|
| Style | **Chibi**, 56 px tall, friendly and ordinary young adults; casual everyday clothes (T-shirts, polo shirts, shirts, hoodies, jeans, trousers, modest skirts, sneakers, flats). No luxury, fantasy, military or costume clothes |
| Avatars | **6**, 3 feminine and 3 masculine: Malay ×2 (one wearing a **tudung**), Chinese ×2, Indian ×1, Sabah/Sarawak Bumiputera ×1. Differences come through hair, faces and everyday clothes, never costumes or caricature |
| Skin tone | A **separate choice** for any avatar: **6 tones** (palette swap of 3 skin shades) |
| Customising | Avatar + skin tone + glasses on/off (L3) |
| Built from parts | Body, head, hair or tudung, outfit, glasses, as layered pixel templates (`creatures.py` method), so 6 avatars share one set of poses |
| Directions | Two drawn (front, facing down-left; back, facing up-left), flipped for the other two |
| Frames per avatar | Idle 2 per drawn view (breathing, blink); walk **4** per drawn view; moods (relaxed, calm, focused and determined, concerned but hopeful, celebrating) on the front view; sitting (sofa: front, desk chair: back); using phone; **asleep in bed at night** (4 breathing frames each for the mattress and the bed, Patrick 2026-10-14, D-86) |
| Consistency | Same height, feet on the same base point in every frame, no cut-off hair or arms, fixed frame size (one 1 × 1 struct canvas) |

## 8. Scope (F1)

| Tier | Assets |
|---|---|
| **Must** | Room furniture for levels 1–5; 1 avatar (idle, walk, moods); bed plants (tiers 1–2 first) with stages and droop |
| **Should** | All 6 avatars and skin tones; interactive objects; decorations; tiers 3–4; chickens (D-66); sitting and using phone |
| **Could** | The tree's 7 stages; more animals |

Rough size: about 30 furniture pieces + 11 variants, 4 interactive objects with states, about 30
garden pieces, 10 bed plants × 3 stages × 2 (droop), the tree, and 6 avatars built from shared
parts (~20 frames each).

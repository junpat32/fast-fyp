# FAST Code-Generated Asset Specification

## Purpose

This document defines the **dimension-critical modular assets** for FAST.

These assets must be generated using code rather than generative image AI because they must align precisely with the game's isometric grid.

Do not generate furniture, characters, trees, flowers, decorative plants, benches, lamps, or other organic/decorative props in this task.

---

## Global Art Rules

- Game style: 2D isometric pixel art
- Isometric ratio: 2:1
- Base grid cell: **64 × 32 px**
- Output format: transparent PNG
- Pixel-art rendering only
- No antialiasing
- Use nearest-neighbour scaling only
- Use a consistent warm starter-apartment palette
- Use a consistent lighting direction across all assets
- All modular assets must align cleanly when placed next to one another
- Do not include text, labels, logos, UI elements, characters, or watermarks

### Exact Floor Diamond

A single 64 × 32 floor tile must use this footprint:

- Top: `(32, 0)`
- Right: `(63, 15)`
- Bottom: `(32, 31)`
- Left: `(0, 15)`

The tile must fit inside an exact **64 × 32 px transparent canvas** unless visible thickness requires a larger canvas.

If thickness is added, the **top diamond footprint must remain exactly 64 × 32 px**.

---

# Part A — Apartment Structural Assets

Generate the following modular apartment assets.

## Floor Tiles

Create:

1. `floor_light_wood.png`
2. `floor_light_wood_worn.png`
3. `floor_dark_wood.png`
4. `floor_kitchen_tile.png`

Requirements:

- Exact 64 × 32 top diamond footprint
- Same isometric angle
- Same plank/tile scale
- Seamless visual alignment between adjacent tiles
- Modest, affordable starter-apartment appearance
- Avoid luxurious marble or premium materials

---

## Wall System

Create reusable wall pieces matching the 64 × 32 floor grid.

Recommended wall height:

- Start with approximately **96 px vertical height**
- Keep height consistent across all full-height wall pieces

Create:

1. `wall_left.png`
2. `wall_right.png`
3. `wall_inside_corner.png`
4. `wall_outside_corner.png`
5. ~~`wall_short_divider.png`~~ (removed by Patrick at the batch-1 review, D-58; replaced by
   `wall_cutaway_front_*` low front walls)
6. `wall_doorway_open.png`
7. `wall_door_closed.png`
8. `wall_window.png`
9. `baseboard_left.png`
10. `baseboard_right.png`

### Wall style

- Cream / warm light-beige wall surface
- Simple wooden or neutral trim
- Slightly warm Southeast Asian starter-apartment atmosphere
- Clean and readable on a phone screen
- No complex decoration
- No furniture attached to walls

### Alignment

Wall bases must align with the 64 × 32 floor-grid directions.

Left-facing and right-facing wall pieces must use consistent perspective so corners connect without visible gaps.

---

# Part B — Garden Terrain System

The garden is an extension of the apartment and uses the same 64 × 32 isometric grid.

The terrain system must remain modular so many progression combinations can be created without drawing complete gardens.

## Ground Tiles

Create:

1. `garden_soil_bare.png`
2. `garden_soil_improved.png`
3. `garden_grass_basic.png`
4. `garden_grass_healthy.png`
5. `garden_grass_lush.png`

Requirements:

- Exact 64 × 32 top diamond footprint
- Compatible edges
- Same lighting and outline style as the apartment floors

---

## Path Tiles

Create:

1. `path_stepping_stone.png`
2. `path_paved.png`
3. `path_nice_paved.png`

Where useful, also provide directional/path variants needed to make connected paths.

---

## Garden Borders

Create:

1. `garden_border_straight_left.png`
2. `garden_border_straight_right.png`
3. `garden_border_corner_inner.png`
4. `garden_border_corner_outer.png`

These may use wood, stone, or modest garden edging.

---

## Planter / Flower-Bed Bases

Create:

1. `planter_bed_empty.png`
2. `planter_bed_soil.png`

Plants and flowers will be added separately as AI-generated decorative assets.

---

## Fence System

Create:

1. `fence_left.png`
2. `fence_right.png`
3. `fence_corner.png`
4. `fence_gate.png`

Use a simple modest residential design.

Do not create ornate luxury fencing.

---

# Shared Palette

Use one shared palette or palette family for all structural assets.

Suggested palette direction:

- warm light wood
- medium wood
- dark wood outline
- cream wall
- light beige
- muted grey
- soft green for garden terrain
- warm soil brown

The exact palette may be adjusted, but all generated assets must remain visually consistent.

---

# Output Structure

Create assets in:

```text
assets/
  isometric/
    apartment/
      floors/
      walls/
    garden/
      terrain/
      paths/
      borders/
      fences/
```

Each asset must be exported as an individual transparent PNG.

Also preserve the generation source code in:

```text
tools/
  asset_generation/
```

---

# Validation Requirements

Before considering an asset complete:

1. Verify PNG dimensions.
2. Verify transparency.
3. Verify the 64 × 32 footprint where applicable.
4. Verify alignment against adjacent tiles.
5. Verify no antialiasing.
6. Verify no accidental semi-transparent edge pixels.
7. Verify consistent lighting.
8. Verify consistent outline thickness.
9. Verify that wall and terrain assets work together visually.
10. Do not modify application logic while generating these assets.

---

# Non-Goals

Do not generate:

- furniture
- beds
- sofas
- desks
- appliances
- decorative plants
- trees
- flowers
- characters
- animation sprites
- UI icons
- financial screens

Those belong to separate asset-generation workflows.

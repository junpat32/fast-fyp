# FAST Art Style Guide
Version: 1.0

## 1. Purpose

This document is the master visual specification for code-generated assets in FAST (Financial Advisory and Safety Tracker).

Claude Code and any future asset-generation scripts must read this file before generating or modifying structural or terrain assets.

The goal is to keep the apartment, garden terrain, and future modular environments visually consistent even when assets are generated at different times.

This guide applies to:

- apartment floor tiles
- apartment walls
- wall corners
- doorways
- windows
- trims/baseboards
- garden ground tiles
- paths
- borders
- planter-bed bases
- fences
- other dimension-critical modular environment pieces

This guide does NOT define the final appearance of AI-generated furniture, characters, trees, flowers, shrubs, or decorative props. Those assets should visually match this guide when imported later.

---

# 2. Core Visual Direction

FAST uses:

- 2D isometric pixel art
- a 2:1 isometric perspective
- a 64 × 32 px base tile grid
- warm, clean, slightly cozy colors
- modest young-adult apartment styling
- subtle Malaysian / tropical residential context
- readable silhouettes suitable for smartphone screens
- practical rather than luxurious design
- simple, game-like pixel shading

The world should feel:

- approachable
- hopeful
- warm
- practical
- youthful
- modest
- clean
- slightly playful

The world should NOT feel:

- luxurious
- futuristic
- cyberpunk
- photorealistic
- overly cartoonish
- medieval
- fantasy-heavy
- hyper-detailed
- visually cluttered

---

# 3. Isometric Geometry

## Base Tile

The entire modular environment must use a 64 × 32 px isometric grid.

A single floor tile uses a 2:1 diamond.

Exact diamond corner coordinates for a 64 × 32 tile canvas:

- Top: `(32, 0)`
- Right: `(63, 15)`
- Bottom: `(32, 31)`
- Left: `(0, 15)`

The top surface of every single-cell terrain/floor tile must align to this geometry.

> **Correction (2026-10-13, DECISIONS D-57):** a 64×32 diamond can only tile seamlessly if its
> widest rows are 62 px. FAST therefore uses rows x = 31−2j … 32+2j (j = min(y, 31−y)): the
> top/bottom corners are as listed, and the left/right corners are at **(1, 15)** and **(62, 15)**.
> This removes a 2-px overlap between neighbouring tiles. The tiling is checked automatically.

Where an asset requires visible thickness or vertical height, the PNG canvas may be larger than 64 × 32, but the base footprint must still align exactly to the 64 × 32 diamond.

## Grid Direction

The two primary isometric ground axes are:

- down-right / up-left
- down-left / up-right

All walls, paths, borders, and fences must follow these axes.

Do not use arbitrary angles for modular structural assets.

---

# 4. Wall Geometry

Use a consistent full wall height of:

- 96 px vertical height

This height is measured vertically on screen.

The wall base must align with a valid 64 × 32 grid edge.

Full-height wall pieces must use the same height across:

- left-facing walls
- right-facing walls
- inside corners
- outside corners
- doorway walls
- door walls
- window walls

Short divider walls may use approximately:

- 48 px vertical height

Do not vary wall heights randomly.

---

# 5. Pixel-Art Rules

All generated structural assets must be true pixel art.

Requirements:

- no antialiasing
- no blurred edges
- no bicubic interpolation
- no bilinear interpolation
- use nearest-neighbour scaling only
- use integer pixel coordinates
- keep outline thickness visually consistent
- avoid subpixel placement
- avoid semi-transparent edge pixels unless deliberately required
- transparent background must remain fully transparent

Preferred outline thickness:

- 1 px for small/simple edges
- 1–2 px for major structural silhouettes where necessary

Avoid excessive black outlines. Prefer very dark warm brown or dark neutral outlines where possible.

---

# 6. Lighting

Use one consistent lighting direction:

- light comes from the upper-left/front-left area of the scene

General shading rule:

- top-facing surfaces: lightest
- left-facing surfaces: medium-light
- right-facing surfaces: medium/darker
- undersides/recesses: darkest

Do not change lighting direction between assets.

Shadows should be subtle and pixel-based.

Do not bake large environmental cast shadows into reusable modular tiles.

---

# 7. Shared Palette Direction

Use a restrained palette family rather than many unrelated colors.

Suggested base palette:

## Dark outlines / deep accents
- Deep brown: `#49311F`
- Dark neutral brown: `#5B3D28`

## Wood
- Dark wood: `#7A4E2D`
- Medium wood: `#A66E3B`
- Warm wood: `#C88A4D`
- Light wood: `#D9A467`
- Wood highlight: `#E8BE83`

## Walls
- Warm cream: `#E8DFC9`
- Light beige: `#D8CDB7`
- Wall shadow: `#B9AD98`

## Stone / neutral
- Light grey: `#C8C6BE`
- Mid grey: `#9D9B94`
- Dark grey: `#66635E`

## Garden greens
- Dark green: `#49663A`
- Mid green: `#6F8B4E`
- Grass green: `#8FAA60`
- Light green: `#AFC979`

## Soil
- Dark soil: `#6B4730`
- Mid soil: `#8A5D3B`
- Light soil: `#A87950`

These values are a starting palette, not an absolute restriction.

Claude Code may adjust colors slightly for readability, but all generated assets must remain within the same visual family.

---

# 8. Apartment Style

The apartment represents a modest starter home for a young adult.

Use:

- light or medium wood
- cream walls
- simple trims
- practical finishes
- compact proportions
- slightly warm, welcoming colors

Avoid:

- marble
- gold trim
- luxury finishes
- ornate mouldings
- expensive-looking stone
- oversized architectural features

Subtle Malaysian context may appear through:

- warm/tropical palette
- practical tiled kitchen floor
- simple apartment-style doors/windows
- compact layouts

Do not use stereotypes or excessive cultural decoration.

---

# 9. Garden Style

The garden is a long-term progression extension of the apartment.

The garden terrain should visually progress from:

1. bare / basic
2. healthier / greener
3. lush / flourishing

The terrain system must remain modular.

Ground tiles, paths, fences, and borders should be generated with code.

Organic assets such as:

- trees
- flowers
- shrubs
- decorative plants
- benches
- lanterns
- garden decorations

may be generated separately using image-generation tools and later aligned to this grid.

The garden must feel like:

- a small urban/suburban residential outdoor area
- tropical-friendly
- achievable and modest

It must not feel like:

- a farm
- a plantation
- a fantasy forest
- a huge botanical garden

---

# 10. Asset Scale

Use the 64 × 32 tile as the scale reference.

Examples:

- one ground tile = 1 × 1 grid cell
- narrow wall segment = 1 grid-edge length
- doorway wall = usually 1–2 grid-edge lengths
- fence segment = 1 grid-edge length
- planter-bed base = 1 × 1 or 2 × 1 cells
- path tile = 1 × 1 cell unless specified otherwise

Do not make structural pieces arbitrarily oversized.

---

# 11. Naming Convention

Use lowercase snake_case filenames.

Examples:

- `floor_light_wood.png`
- `wall_left.png`
- `garden_grass_basic.png`
- `path_stepping_stone.png`

Avoid:

- spaces
- uppercase filenames
- version numbers in filenames unless required
- vague names like `tile1.png`

---

# 12. Folder Structure

Use:

```text
assets/
  isometric/
    apartment/
      floors/
      walls/
      trims/
    garden/
      terrain/
      paths/
      borders/
      planters/
      fences/
```

Source-generation scripts should live in:

```text
tools/
  asset_generation/
```

Generated previews may live in:

```text
tools/
  asset_generation/
  previews/
```

Do not mix source scripts with final app assets.

---

# 13. Export Requirements

Final assets must be:

- PNG
- RGBA
- transparent where appropriate
- pixel-perfect
- saved at native resolution
- not upscaled unnecessarily
- not compressed with lossy formats

Do not export JPEG for game assets.

---

# 14. Validation Checklist

Every generated asset must be checked for:

- correct canvas dimensions
- valid transparency
- exact 64 × 32 footprint where applicable
- correct isometric perspective
- clean grid alignment
- no accidental antialiasing
- no half-transparent edge artifacts
- consistent outline style
- consistent lighting
- consistent palette
- correct filename
- correct folder location
- no unintended overlap with neighboring modular pieces

If possible, generation scripts should include automated validation.

---

# 15. Preview Requirements

Generate a preview contact sheet after producing the assets.

The preview should:

- show all generated assets together
- place assets on a neutral checkerboard or simple neutral background
- preserve native pixel scaling or use nearest-neighbour integer scaling
- label assets only in the preview image, not inside the actual asset PNGs

Also generate at least one alignment preview showing:

- multiple floor tiles connected together
- left and right walls connected to floor edges
- at least one wall corner
- garden terrain tiles connected together
- at least one path connection
- at least one fence connection

The purpose is to visually catch alignment errors before these assets are used in FAST.

---

# 16. Non-Goals

This specification does not require code generation of:

- beds
- sofas
- wardrobes
- desks
- chairs
- refrigerators
- kitchen appliances
- character sprites
- trees
- flowers
- shrubs
- decorative garden props
- UI icons
- HUD graphics
- financial dashboards

These will be generated or designed separately.

---

# 17. Priority

When there is a conflict between visual decoration and exact geometry:

**exact geometry wins.**

The environment must first work correctly on the 64 × 32 grid.

Visual polish may be added afterward without breaking alignment.

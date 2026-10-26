"""The whole kit in build order: batch 1 (pieces.py, 48 pieces) then batch 2 (D-84, D-86):
furniture.py (with the room decorations), garden_plants.py, characters.py, creatures.py (chickens),
garden_decor.py, garden_tree.py.
Kept separate so neither module imports the other."""
from .characters import AVATAR_PIECES
from .creatures import ANIMAL_PIECES
from .furniture import APPROVED as _STEP1
from .furniture import DECORATIONS, FURNITURE
from .garden_decor import GARDEN_DECOR_PIECES
from .garden_plants import PLANT_PIECES, TIER_1_2
from .garden_tree import TREE_PIECES
from .pieces import PIECES as _BATCH1_PIECES

BATCH1 = len(_BATCH1_PIECES)
PIECES = _BATCH1_PIECES + FURNITURE + PLANT_PIECES + AVATAR_PIECES + ANIMAL_PIECES + GARDEN_DECOR_PIECES + TREE_PIECES
# Batch-2 pieces Patrick has approved: step 1, room level 1 (D-84); with "yes, proceed to avatars 2-6"
# (2026-10-14, D-86) steps 2-4: room levels 2-5, the tier 1-2 bed plants and avatar 1's 17 frames
# (unchanged, pixel for pixel, by the move to shared parts). Its new poses are drafts like the rest.
_DECOR = {p.name for p in DECORATIONS}
_AVATAR_1 = {f"avatar_01_{v}_{f}" for v in ("front", "back") for f in ("idle_0", "idle_1", "walk_0", "walk_1",
                                                                     "walk_2", "walk_3")} \
    | {f"avatar_01_mood_{m}" for m in ("relaxed", "calm", "focused", "concerned_hopeful", "celebrating")}
# The idle frames for the Home scene (D-116): breathing and blinking in every mood, all six avatars;
# Patrick: "approved" (2026-10-20, from the animated preview idle_d116.gif)
_IDLE = {f"avatar_0{a}_mood_{m}_{k}" for a in range(1, 7)
         for m in ("relaxed", "calm", "focused", "concerned_hopeful", "celebrating") for k in ("breathe", "blink")}
APPROVED = (_STEP1 | {p.name for p in FURNITURE if p.name not in _DECOR} | _AVATAR_1 | _IDLE
            | {p.name for p in PLANT_PIECES if p.name.startswith(tuple(f"plant_{n}_" for n in TIER_1_2))
               or p.name.startswith("plant_free_seedling")})

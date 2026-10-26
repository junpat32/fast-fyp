// The art kit's layouts for the home scene (assets/isometric/scenes, made by the kit's build, D-88) and
// the game's decoration lists (shared/game.json): the same files the art previews and the engine use
// (rule 5). Metro reaches them through metro.config.js (watchFolders).
import room from '../../../assets/isometric/scenes/room.json';
import g0 from '../../../assets/isometric/scenes/home_g0.json';
import g1 from '../../../assets/isometric/scenes/home_g1.json';
import g2 from '../../../assets/isometric/scenes/home_g2.json';
import g3 from '../../../assets/isometric/scenes/home_g3.json';
import g4 from '../../../assets/isometric/scenes/home_g4.json';
import characters from '../../../assets/isometric/characters.json';
import game from '../../../shared/game.json';

import type { Characters } from '@/lib/character';
import type { Lists } from '@/lib/home';
import type { Geometry, RoomJson, SceneJson } from '@/lib/scene';

import { KIT_GEOM } from './art-index';

export const ROOM = room as unknown as RoomJson;
/** The avatars' frames, skin tones and glasses rule (characters.json; the character sheet, D-125). */
export const CHARACTERS = characters as unknown as Characters;
export const SCENES = [g0, g1, g2, g3, g4] as unknown as SceneJson[];
export const LISTS: Lists = {
  roomDecor: game.decorations.room, gardenDecor: game.decorations.garden, pieces: KIT_GEOM,
};
export const GEOMETRY: Geometry = Object.fromEntries(
  Object.entries(KIT_GEOM).map(([n, [fx, fy, w, h]]) => [n, [fx, fy, w, h]]));

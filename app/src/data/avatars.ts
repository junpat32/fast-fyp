/**
 * The six characters (assets: avatar_01 to avatar_06), as the sign-up's character step describes them.
 * Which one a person uses is in their profile (profiles.avatar, D-124); the study personas' choices are
 * in their data (tools/personas/build.py), so there is no second list here.
 */
export const AVATARS: { avatar: number; look: string }[] = [
  { avatar: 1, look: 'Short hair, green T-shirt' },
  { avatar: 2, look: 'Tudung, long skirt' },
  { avatar: 3, look: 'Side parting, polo shirt' },
  { avatar: 4, look: 'Bob with a fringe, mustard T-shirt' },
  { avatar: 5, look: 'Ponytail, terracotta T-shirt' },
  { avatar: 6, look: 'Wavy hair, sage hoodie' },
];

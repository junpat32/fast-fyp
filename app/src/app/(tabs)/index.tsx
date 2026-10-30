import type { Transforms3d } from '@shopify/react-native-skia';
import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { useDerivedValue, useSharedValue, withTiming } from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiError } from '@/api/client';
import { Badges, EarnedMedals } from '@/components/badges';
import { SceneHost } from '@/components/home/scene-host';
import { ThingCard } from '@/components/home/thing-card';
import { PlantIcon } from '@/components/sprite';
import { StudyBar } from '@/components/study-bar';
import { Tap } from '@/components/tap';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useApi } from '@/data/api-context';
import { KIT_BOX, KIT_GEOM } from '@/data/art-index';
import { GAME_RULES } from '@/data/game-rules';
import { GEOMETRY, LISTS, ROOM, SCENES } from '@/data/kit';
import { useScheme } from '@/data/scheme';
import { useRequest } from '@/data/use-request';
import { useTheme } from '@/hooks/use-theme';
import { monthWord, myDate, openMonth } from '@/lib/checkin';
import { monthTotals, rmText } from '@/lib/entry';
import { DECOR_NAMES, footprint, gardenSpot, offeredSpots, spotAt, usedCells, type C2 } from '@/lib/extras';
import { freeBedCells } from '@/lib/garden';
import { gardenLevel, homeInput } from '@/lib/home';
import { hitTest, plotBounds, type Target } from '@/lib/home-tap';
import { cellAt } from '@/lib/iso';
import { composeScene, draws, MAP_ORIGIN, VIEW_H, VIEW_W } from '@/lib/scene';

const MAX_ZOOM = 4;                                       // four times the whole-width view
const WIDTHS = Object.fromEntries(Object.entries(KIT_GEOM).map(([n, g]) => [n, g[2]]));
const SIZES: Record<string, C2> = Object.fromEntries(LISTS.gardenDecor.map((d) => [d, [KIT_GEOM[d][4], KIT_GEOM[d][5]]]));
type Placing = { item: string; moving: boolean; spots: C2[]; error: string | null };   // choosing a decoration's spot
const why = (e: unknown) => (e instanceof ApiError ? e.detail : e instanceof Error ? e.message : String(e));

/**
 * The Home screen (docs/app_plan.md §3, game_design §7-10; study task 6): the room and garden as the
 * game state builds them (GET /v1/game), full screen, in the art for the phone's time of day (D-113).
 * Pinch to zoom up to 4x, drag to move, double-tap to fit again (D-114). A tap opens an interactive
 * card (D-115): plant in an empty bed spot (D-74), dig a plant up, see how far things have grown or
 * filled, jump to Money or Add. The character and the chickens idle while the tab shows (D-116).
 * On top, the study bar (D-119); under it a small see-through pill shows the points and the badges
 * earned, and tapping it shows the levels and every badge (D-127); "More" opens the More screen.
 */
export default function HomeScreen() {
  const { api, entries, checkins, profile, look, sample, study, version, changed } = useApi();
  const avatar = look.avatar;
  const { period } = useScheme();
  const theme = useTheme();
  const router = useRouter();
  const { data: game, error, loading } = useRequest(() => api.game(), [api, version]);
  const { data: assess } = useRequest(() => api.assess(), [api, version]);
  const { data: card } = useRequest(() => api.card(), [api, version]);       // this week's what-if (D-117)
  const { data: checkedIn } = useRequest(() => checkins.list(), [checkins, version]);
  const checkinMonth = game && profile ? openMonth(game.as_of, myDate(profile.created_at)) : null;
  const checkinDue = checkinMonth !== null && !!checkedIn && !checkedIn.some((r) => r.month === checkinMonth);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [target, setTarget] = useState<Target | null>(null);
  const [highlight, setHighlight] = useState<[number, number][]>([]);
  const [monthOut, setMonthOut] = useState<string | null>(null);
  const [more, setMore] = useState(false);
  const [placing, setPlacing] = useState<Placing | null>(null);
  const [showing, setShowing] = useState(true);           // the idle animation runs only on this tab (D-116)
  useFocusEffect(useCallback(() => { setShowing(true); return () => setShowing(false); }, []));

  const scene = game ? SCENES[gardenLevel(game)] : null;
  const built = useMemo(() => {
    if (!game || !scene) return null;
    const composed = composeScene(scene, ROOM, homeInput(game, scene, period, avatar, LISTS));
    return { list: draws(composed, GEOMETRY), cells: composed.structs.map((s): [number, number] => [s.gx, s.gy]) };
  }, [game, scene, period, avatar]);

  // pan and pinch, on the UI thread; the scene starts fitted to the screen's width
  const base = size.w / VIEW_W;
  const zoom = useSharedValue(1);
  const tx = useSharedValue(0);
  const ty = useSharedValue(0);
  const pinchStart = useSharedValue({ z: 1, x: 0, y: 0, fx: 0, fy: 0 });
  const panStart = useSharedValue({ x: 0, y: 0 });
  const transform = useDerivedValue<Transforms3d>(() => [{ translateX: tx.value }, { translateY: ty.value }, { scale: base * zoom.value }]);
  useEffect(() => {                                       // another person or date: the whole home, no card open
    zoom.value = 1; tx.value = 0; ty.value = 0;
    setTarget(null);
    setHighlight([]);
    setPlacing(null);
  }, [sample?.key, study?.date, zoom, tx, ty]);

  const act = useCallback(async (a: Parameters<typeof api.gameAction>[0]) => {
    try {
      await api.gameAction(a);
      changed();                                          // the scene and pills reload from the game
      return null;
    } catch (e) {
      return why(e);
    }
  }, [api, changed]);

  /** A garden decoration (new or moving): its 2-3 spots glow, the whole garden in view (D-120, K2). */
  const startPlacing = useCallback((item: string, moving: boolean) => {
    if (!game || !scene) return;
    const spots = offeredSpots(scene.decor_free_cells, SIZES[item] ?? [1, 1], usedCells(game.decorations, SIZES, moving ? item : undefined));
    setTarget(null);
    setHighlight([]);
    setPlacing({ item, moving, spots, error: null });
    zoom.value = withTiming(1); tx.value = withTiming(0); ty.value = withTiming(0);
  }, [game, scene, zoom, tx, ty]);

  const onTap = useCallback((x: number, y: number) => {
    if (!game || !scene || !built || base === 0) return;
    const k = base * zoom.value;
    const p = { x: (x - tx.value) / k, y: (y - ty.value) / k };
    if (placing) {                                        // only a glowing spot counts while choosing one
      const spot = spotAt(cellAt(p, MAP_ORIGIN), placing.spots, SIZES[placing.item] ?? [1, 1]);
      if (!spot) return;
      act({ kind: placing.moving ? 'move_decoration' : 'decorate', item: placing.item, spot: gardenSpot(spot) })
        .then((err) => setPlacing((pl) => (err && pl ? { ...pl, error: err } : null)));
      return;
    }
    const hit = hitTest(p, built.list, {
      cells: built.cells, boxes: KIT_BOX, widths: WIDTHS, interactive: ROOM.interactive, plot: plotBounds(scene),
      room: scene.room, bed: game.garden.bed, plants: game.plants, gardenDecor: LISTS.gardenDecor,
      treeSpot: scene.tree,                                // its 2 x 2 spot: a small tree is hard to hit

    });
    setTarget(hit);
    setHighlight([]);
    setMore(false);
    if (hit?.kind === 'object' && hit.opens === 'budgets') {
      entries.month(game.as_of).then((list) => setMonthOut(rmText(monthTotals(list).out)));
    }
  }, [game, scene, built, base, zoom, tx, ty, entries, placing, act]);
  const glow = placing ? placing.spots.flatMap((s) => footprint(s, SIZES[placing.item] ?? [1, 1])) : highlight;

  const gesture = useMemo(() => {
    const { w, h } = size;
    const sw = VIEW_W * base;
    const sh = VIEW_H * base;
    const clampX = (x: number, z: number) => { 'worklet'; return Math.min(0, Math.max(w - sw * z, x)); };
    const clampY = (y: number, z: number) => { 'worklet'; return Math.min(0, Math.max(Math.min(0, h - sh * z), y)); };
    const pinch = Gesture.Pinch()
      .onStart((e) => { pinchStart.value = { z: zoom.value, x: tx.value, y: ty.value, fx: e.focalX, fy: e.focalY }; })
      .onUpdate((e) => {
        const s = pinchStart.value;
        const z = Math.min(Math.max(s.z * e.scale, 1), MAX_ZOOM);
        const k = z / s.z;                              // the point under the fingers stays under them
        zoom.value = z;
        tx.value = clampX(e.focalX - (s.fx - s.x) * k, z);
        ty.value = clampY(e.focalY - (s.fy - s.y) * k, z);
      });
    const pan = Gesture.Pan().maxPointers(1)
      .onStart(() => { panStart.value = { x: tx.value, y: ty.value }; })
      .onUpdate((e) => {
        tx.value = clampX(panStart.value.x + e.translationX, zoom.value);
        ty.value = clampY(panStart.value.y + e.translationY, zoom.value);
      });
    const fit = Gesture.Tap().numberOfTaps(2).onEnd(() => {
      zoom.value = withTiming(1); tx.value = withTiming(0); ty.value = withTiming(0);
    });
    const tap = Gesture.Tap().runOnJS(true).onEnd((e, ok) => { if (ok) onTap(e.x, e.y); });
    return Gesture.Simultaneous(pinch, pan, Gesture.Exclusive(fit, tap));
  }, [size, base, onTap, pinchStart, panStart, zoom, tx, ty]);

  return (
    <View style={[styles.container, { backgroundColor: theme.lawn }]}
          onLayout={(e) => setSize({ w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height })}>
      {built && size.w > 0 && (
        <GestureDetector gesture={gesture}>
          <View style={StyleSheet.absoluteFill} accessibilityLabel="Your home: pinch to zoom, tap a thing to learn about it">
            <SceneHost list={built.list} period={period} look={look} width={size.w} height={size.h} transform={transform}
                       highlight={glow} animate={showing} />
          </View>
        </GestureDetector>
      )}

      <SafeAreaView edges={['top']} style={styles.overlay} pointerEvents="box-none">
        <View style={styles.top} pointerEvents="box-none"><StudyBar floating /></View>
        {game && (
          <View style={styles.pills} pointerEvents="box-none">
            <Tap onPress={() => setMore(!more)} accessibilityRole="button" accessibilityState={{ expanded: more }}
                 style={[styles.pill, { backgroundColor: theme.overlay }]}>
              <PlantIcon stage={game.look.savings_plant} max={22} />
              <ThemedText type="smallBold">{game.points} points</ThemedText>
              <EarnedMedals badges={game.badges} />
              <ThemedText type="smallBold">{more ? '▴' : '▾'}</ThemedText>
            </Tap>
            <Tap onPress={() => router.navigate('/more')} accessibilityRole="button" accessibilityLabel="More: your character, badges, privacy"
                 style={[styles.pill, { backgroundColor: theme.overlay }]}>
              <ThemedText type="smallBold">More ›</ThemedText>
            </Tap>
          </View>
        )}
        {checkinDue && (
          <Tap onPress={() => router.navigate({ pathname: '/add', params: { mode: 'checkin' } })} accessibilityRole="button"
               accessibilityLabel={`The ${monthWord(checkinMonth!)} check-in is open`}
               style={[styles.pill, styles.cardPill, { backgroundColor: theme.overlay, borderColor: theme.accent }]}>
            <ThemedText type="small" style={{ color: theme.accent, fontWeight: 700 }}>
              {monthWord(checkinMonth!)} check-in is open · +{GAME_RULES.points.checkin} ›
            </ThemedText>
          </Tap>
        )}
        {card && card.answer === null && (
          <Tap onPress={() => router.navigate('/future')} accessibilityRole="button"
               accessibilityLabel="This week's what-if card is waiting on the Future tab"
               style={[styles.pill, styles.cardPill, { backgroundColor: theme.overlay, borderColor: theme.accent }]}>
            <ThemedText type="small" style={{ color: theme.accent, fontWeight: 700 }}>New this week: a what-if card ›</ThemedText>
          </Tap>
        )}
        {more && game && (
          <View style={[styles.panel, { backgroundColor: theme.overlay }]}>
            <ThemedText type="small">
              Room level {game.room_level} of 5 · {game.garden.open ? `garden level ${game.garden.level} of 4` : 'the garden opens after 3 check-ins'}
            </ThemedText>
            <ThemedText type="small">
              {game.choices.available} {game.choices.available === 1 ? 'choice' : 'choices'} to spend on plants or decorations
            </ThemedText>
            <ThemedText type="smallBold" style={styles.badges}>Badges</ThemedText>
            <Badges game={game} />
            <ThemedText type="small" themeColor="textSecondary" style={styles.badges}>
              Pinch to zoom · double-tap to see it all · tap a thing to learn about it
            </ThemedText>
            <Tap onPress={() => { setMore(false); setPlacing(null); setTarget({ kind: 'choices' }); }} accessibilityRole="button"
                 style={[styles.spend, { backgroundColor: theme.accent }]}>
              <ThemedText type="small" style={{ color: theme.onAccent, fontWeight: 700 }}>
                {game.choices.available > 0 ? `Spend a choice (${game.choices.available}) ›` : 'See what choices unlock ›'}
              </ThemedText>
            </Tap>
          </View>
        )}
        {placing && (
          <Tap onPress={() => setPlacing(null)} style={[styles.panel, { backgroundColor: theme.overlay }]} accessibilityRole="button">
            <ThemedText type="small">
              {placing.spots.length > 0
                ? `Tap a glowing spot for the ${(DECOR_NAMES[placing.item] ?? placing.item).toLowerCase()}${placing.moving ? '' : ' (1 choice)'} · tap here to stop`
                : `No free spot fits the ${(DECOR_NAMES[placing.item] ?? placing.item).toLowerCase()} right now · tap here to close`}
            </ThemedText>
            {placing.error && <ThemedText type="small" style={{ color: theme.bad }}>{placing.error}</ThemedText>}
          </Tap>
        )}
        {highlight.length > 0 && (
          <Tap onPress={() => setHighlight([])} style={[styles.panel, { backgroundColor: theme.overlay }]} accessibilityRole="button">
            <ThemedText type="small">Tap a glowing spot in the bed to plant there · tap here to stop</ThemedText>
          </Tap>
        )}
        {loading && <ActivityIndicator style={styles.loading} />}
        {error && <ThemedText style={[styles.panel, { color: theme.bad, backgroundColor: theme.background }]}>
          Couldn't load your home: {error}</ThemedText>}
      </SafeAreaView>

      {target && game && (
        <ThingCard key={JSON.stringify(target)} target={target} game={game} assess={assess} look={look}
                   night={period === 'night'} monthOut={monthOut}
                   onPlant={(cell, item) => act({ kind: 'plant', cell, item })}
                   onDig={(cell) => act({ kind: 'dig', cell })}
                   onAction={act}
                   onPlace={startPlacing}
                   onShowBed={() => { setHighlight(freeBedCells(game)); setTarget(null); }}
                   onGo={(tab) => { setTarget(null); router.navigate(`/${tab}`); }}
                   onClose={() => setTarget(null)} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, overflow: 'hidden' },
  overlay: { paddingHorizontal: Spacing.three, gap: Spacing.two },
  top: { marginTop: Spacing.two },
  pill: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two, borderRadius: Spacing.four,
          paddingHorizontal: Spacing.three, minHeight: 36 },
  pills: { flexDirection: 'row', justifyContent: 'space-between', gap: Spacing.two },
  badges: { marginTop: Spacing.one },
  spend: { borderRadius: Spacing.three, minHeight: 40, alignItems: 'center', justifyContent: 'center', marginTop: Spacing.one },
  panel: { borderRadius: Spacing.three, padding: Spacing.three, gap: Spacing.one },
  cardPill: { alignSelf: 'flex-start', borderWidth: 1 },
  loading: { marginTop: Spacing.four },
});

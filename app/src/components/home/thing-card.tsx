import { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import Animated, { ZoomIn } from 'react-native-reanimated';

import type { GameAction } from '@/api/client';
import type { AssessResponse, GameResponse } from '@/api/types';
import type { Look } from '@/lib/character';
import { Portrait, Sprite } from '@/components/sprite';
import { Tap } from '@/components/tap';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { GAME_RULES } from '@/data/game-rules';
import { useTheme } from '@/hooks/use-theme';
import {
  animalStatus, DECOR_NAMES, roomOptions, roomSpot, treeStatus, type ExtrasRules, type Status,
} from '@/lib/extras';
import type { Mood } from '@/lib/future';
import {
  freeBedCells, growthLine, PLANT_NAMES, plantOptions, pointsToNextChoice, type GardenRules,
} from '@/lib/garden';
import { cardFor, type CardRules, type Target } from '@/lib/home-tap';
import { cushionProgress, milestoneLine } from '@/lib/rewards';

const RULES = GAME_RULES as unknown as GardenRules & CardRules & ExtrasRules;
const MOODS = ['relaxed', 'calm', 'focused', 'concerned_hopeful', 'celebrating'];
const short = (plant: string) => (PLANT_NAMES[plant] ?? plant).split(' (')[0];

type Props = {
  target: Target;
  game: GameResponse;
  assess: AssessResponse | null;
  look: Look;                                               // the character: avatar, skin tone, glasses (D-125)
  night: boolean;
  monthOut: string | null;                                  // this month's money out (the Add list)
  onPlant: (cell: [number, number], item: string) => Promise<string | null>;   // null = done, else why not
  onDig: (cell: [number, number]) => Promise<string | null>;
  onAction: (a: GameAction) => Promise<string | null>;      // the Home extras (D-120): null = done, else why not
  onPlace: (item: string, moving: boolean) => void;         // a garden decoration: pick its spot on the scene
  onShowBed: () => void;
  onGo: (screen: 'money' | 'add' | 'budgets' | 'helper') => void;
  onClose: () => void;
};

/**
 * The card a tap on the Home scene opens (D-114, made interactive and gamified in D-115, the extras
 * in D-120): what the thing is, how far it has grown or filled, and what you can do with it.
 * Guardrails (D-107): every number and reward is the game's own (game.json), nothing is random,
 * compared with others or taken away; planting and the extras spend choices the user already earned.
 */
export function ThingCard(p: Props) {
  const t = useTheme();
  const card = cardFor(p.target, p.game, RULES, p.night);
  return (
    <View style={[styles.card, { backgroundColor: t.background, borderColor: t.line }]}>
      <View style={styles.head}>
        <ThemedText type="smallBold" style={styles.title}>{card.title}</ThemedText>
        <Tap onPress={p.onClose} hitSlop={12} accessibilityRole="button" accessibilityLabel="Close">
          <ThemedText type="default" themeColor="textSecondary">✕</ThemedText>
        </Tap>
      </View>
      <ScrollView style={styles.scroll} contentContainerStyle={styles.body}>
        <Body {...p} lines={card.lines} />
      </ScrollView>
    </View>
  );
}

function Body(p: Props & { lines: string[] }) {
  const { target, game } = p;
  const lines = <>{p.lines.map((l) => <ThemedText key={l} type="small">{l}</ThemedText>)}</>;
  switch (target.kind) {
    case 'bed':
      return <PlantHere {...p} cell={target.cell} />;
    case 'plant':
      return <PlantDetail {...p} cell={target.cell} />;
    case 'garden': {
      const free = freeBedCells(game).length;
      return (
        <>
          {lines}
          <GardenTrack game={game} />
          {game.garden.open && (free > 0
            ? <Action label={`Show where I can plant (${free} ${free === 1 ? 'spot' : 'spots'})`} onPress={p.onShowBed} />
            : <ThemedText type="small" themeColor="textSecondary">Every spot in the bed is growing something.</ThemedText>)}
        </>
      );
    }
    case 'object':
      if (target.opens === 'savings') return <CoinJar {...p} lines={lines} />;
      if (target.opens === 'savings_history') return <SavingsPlant {...p} lines={lines} />;
      if (target.opens === 'budgets') {
        return (
          <>
            {lines}
            {p.monthOut && <ThemedText type="smallBold">This month so far: {p.monthOut} out</ThemedText>}
            <Action label="Open budgets" onPress={() => p.onGo('budgets')} />
            <Action label="Add an entry" onPress={() => p.onGo('add')} quiet />
          </>
        );
      }
      return <>{lines}<Action label="Ask the money helper" onPress={() => p.onGo('helper')} /></>;
    case 'choices':
      return <Choices {...p} />;
    case 'tree':
      return <TreeDetail {...p} />;
    case 'animal':
      return <Chickens {...p} />;
    case 'decoration':
      return (
        <View style={styles.side}>
          <Sprite name={`decor_${target.item}`} min={36} max={56} />
          <View style={styles.sideText}>
            {lines}
            <Action label="Move it" onPress={() => p.onPlace(target.item, true)} />
          </View>
        </View>
      );
    case 'character': {
      const mood = (MOODS.includes(game.look.mood) ? game.look.mood : 'calm') as Mood;
      const step = p.assess?.advice[0]?.short;
      return (
        <View style={styles.side}>
          <Portrait look={p.look} mood={mood} label="You" />
          <View style={styles.sideText}>
            {lines}
            {step && <ThemedText type="small"><ThemedText type="smallBold">Your next step: </ThemedText>{step}</ThemedText>}
            <Action label="Open Money" onPress={() => p.onGo('money')} />
          </View>
        </View>
      );
    }
    default:
      return lines;
  }
}

/** The seed picker: unlocked plants to plant now, the rest shown as what's still to come. */
function PlantHere(p: Props & { cell: [number, number]; lines: string[] }) {
  const t = useTheme();
  const [planted, setPlanted] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (planted) {
    return (
      <View style={styles.done}>
        <Animated.View entering={ZoomIn.springify()}><Sprite name={`crop_${planted}_seedling`} min={40} max={64} /></Animated.View>
        <ThemedText type="smallBold">Planted: a {short(planted).toLowerCase()} seedling</ThemedText>
        <ThemedText type="small" themeColor="textSecondary">{growthLine(0, RULES)}.</ThemedText>
      </View>
    );
  }
  const game = p.game;
  const options = plantOptions(game, RULES);
  const canPay = game.choices.available > 0;
  const plant = async (item: string) => {
    setBusy(true);
    const why = await p.onPlant(p.cell, item);
    setBusy(false);
    if (why) setError(why);
    else setPlanted(item);
  };
  return (
    <>
      {p.lines.map((l) => <ThemedText key={l} type="small">{l}</ThemedText>)}
      <ThemedText type="small" themeColor="textSecondary">
        {canPay ? `${game.choices.available} ${game.choices.available === 1 ? 'choice' : 'choices'} to spend`
          : `No choice to spend yet: ${pointsToNextChoice(game.points, RULES)} more points for the next one`}
        {game.seed_box.length ? ` · ${game.seed_box.length} waiting in your seed box, free` : ''}
      </ThemedText>
      <View style={styles.grid}>
        {options.map((o) => {
          const can = o.unlocked && (o.free || canPay) && !busy;
          return (
            <Tap key={o.plant} disabled={!can} onPress={() => plant(o.plant)} accessibilityRole="button"
                 accessibilityState={{ disabled: !can }}
                 accessibilityLabel={`${short(o.plant)}: ${!o.unlocked ? `unlocks after ${o.unlockInMonths} more counted months`
                   : o.free ? 'free from your seed box' : 'one choice'}`}
                 style={[styles.tile, { backgroundColor: t.card, borderColor: can ? t.accent : t.line, opacity: o.unlocked ? 1 : 0.5 }]}>
              <Sprite name={`crop_${o.plant}_full`} min={24} max={40} />
              <ThemedText type="small" style={styles.tileName} numberOfLines={1}>{short(o.plant)}</ThemedText>
              <ThemedText type="small" style={[styles.tileCost, { color: o.unlocked ? t.accent : t.textSecondary }]}>
                {!o.unlocked ? `in ${o.unlockInMonths} mo` : o.free ? 'free' : '1 choice'}
              </ThemedText>
            </Tap>
          );
        })}
      </View>
      <ThemedText type="small" themeColor="textSecondary">More plants unlock as you keep a cushion, month after month.</ThemedText>
      {error && <ThemedText type="small" style={{ color: t.bad }}>{error}</ThemedText>}
    </>
  );
}

/** A plant: how far it has grown, and digging it up (into the seed box, to plant again for free). */
function PlantDetail(p: Props & { cell: [number, number]; lines: string[] }) {
  const t = useTheme();
  const [confirm, setConfirm] = useState(false);
  const [dug, setDug] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const plant = p.game.plants.find((x) => x.cell[0] === p.cell[0] && x.cell[1] === p.cell[1]);
  if (dug || !plant) {
    return <ThemedText type="small">{dug ? 'Dug up: it waits in your seed box, to plant again for free.' : 'Nothing grows here now.'}</ThemedText>;
  }
  const stages = ['seedling', 'young', 'full'];
  const dig = async () => {
    if (!confirm) { setConfirm(true); return; }
    const why = await p.onDig(p.cell);
    if (why) setError(why);
    else setDug(true);
  };
  return (
    <View style={styles.side}>
      <Sprite name={`crop_${plant.plant}_${plant.stage}`} min={40} max={64} />
      <View style={styles.sideText}>
        <View style={styles.track}>
          {stages.map((s) => (
            <View key={s} style={[styles.step, { backgroundColor: stages.indexOf(s) <= stages.indexOf(plant.stage) ? t.reward : t.line }]} />
          ))}
        </View>
        <ThemedText type="small" themeColor="textSecondary">Seedling · young · full grown</ThemedText>
        <ThemedText type="smallBold">{growthLine(plant.growing_days, RULES)}</ThemedText>
        {p.lines.slice(1).map((l) => <ThemedText key={l} type="small">{l}</ThemedText>)}
        <Action label={confirm ? 'Tap again to dig it up' : 'Dig up (it waits in your seed box)'} onPress={dig} quiet />
        {error && <ThemedText type="small" style={{ color: t.bad }}>{error}</ThemedText>}
      </View>
    </View>
  );
}

/** One game action from a card: busy while it runs, then what happened (a small celebration) or why not. */
function useRun(onAction: Props['onAction']) {
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<{ sprite: string; text: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const run = async (a: GameAction, sprite: string, text: string) => {
    setBusy(true);
    setError(null);
    const why = await onAction(a);
    setBusy(false);
    if (why) setError(why);
    else setDone({ sprite, text });
  };
  return { busy, done, error, run };
}

function Done({ done, error }: { done: { sprite: string; text: string } | null; error: string | null }) {
  const t = useTheme();
  return (
    <>
      {done && (
        <View style={styles.doneRow}>
          <Animated.View entering={ZoomIn.springify()}><Sprite name={done.sprite} min={32} max={48} /></Animated.View>
          <ThemedText type="smallBold" style={styles.flex}>{done.text}</ThemedText>
        </View>
      )}
      {error && <ThemedText type="small" style={{ color: t.bad }}>{error}</ThemedText>}
    </>
  );
}

const choiceLine = (g: GameResponse) => (g.choices.available > 0
  ? `${g.choices.available} ${g.choices.available === 1 ? 'choice' : 'choices'} to spend`
  : `No choice to spend yet: ${pointsToNextChoice(g.points, RULES)} more points for the next one`);

/** What a locked extra is waiting for, in the game's own numbers (`closed`: before the garden opens). */
function waitLine(s: Status, what: string, closed: string): string {
  if (s.kind !== 'locked') return '';
  return s.months === null ? closed : `${what} after ${s.months} more counted ${s.months === 1 ? 'month' : 'months'}.`;
}
const opens = `when your garden opens, after your first ${RULES.garden.opens_after_check_ins} check-ins`;
const TREE_CLOSED = `It comes with the top garden level, ${RULES.garden.level_at_qualifying_months[String(RULES.garden.tree_from_garden_level)]} counted months after your garden opens.`;
const HENS_CLOSED = `A place for an animal opens ${RULES.garden.animal_slots_at_qualifying_months[0]} counted months after your garden opens.`;

/** "Spend a choice": the room's and the garden's decorations, the tree and the chickens (D-120). */
function Choices(p: Props & { lines: string[] }) {
  const t = useTheme();
  const g = p.game;
  const { busy, done, error, run } = useRun(p.onAction);
  const canPay = g.choices.available > 0;
  const tree = treeStatus(g, RULES);
  const hens = animalStatus(g, RULES, 'chicken');
  const name = (item: string) => DECOR_NAMES[item] ?? item;
  return (
    <>
      <Done done={done} error={error} />
      {p.lines.map((l) => <ThemedText key={l} type="small">{l}</ThemedText>)}
      <ThemedText type="smallBold" style={{ color: canPay ? t.accent : t.textSecondary }}>{choiceLine(g)}</ThemedText>

      <ThemedText type="smallBold" style={styles.section}>Your room</ThemedText>
      <View style={styles.grid}>
        {roomOptions(g, RULES).map((o) => (
          <Tile key={o.item} sprite={`decor_${o.item}`} name={name(o.item)} cost={o.owned ? '✓ yours' : '1 choice'}
                enabled={!o.owned && canPay && !busy} owned={o.owned}
                onPress={() => run({ kind: 'decorate', item: o.item, spot: roomSpot(o.item) }, `decor_${o.item}`,
                  `In your room now: ${name(o.item)}${o.hides ? ` (your ${name(o.hides).toLowerCase()} are put away)` : ''}.`)} />
        ))}
      </View>
      <ThemedText type="small" themeColor="textSecondary">A new curtain or rug takes the place of the one up now.</ThemedText>

      <ThemedText type="smallBold" style={styles.section}>Your garden</ThemedText>
      {!g.garden.open ? (
        <ThemedText type="small" themeColor="textSecondary">Garden things come {opens}.</ThemedText>
      ) : (
        <>
          <View style={styles.grid}>
            {RULES.decorations.garden.map((item) => {
              const owned = item in g.decorations;
              return (
                <Tile key={item} sprite={`decor_${item}`} name={name(item)} cost={owned ? 'Move' : '1 choice'}
                      enabled={(owned || canPay) && !busy} owned={owned} onPress={() => p.onPlace(item, owned)} />
              );
            })}
          </View>
          <ThemedText type="small" themeColor="textSecondary">Pick one, then tap a glowing spot in the garden.</ThemedText>
        </>
      )}

      <ThemedText type="smallBold" style={styles.section}>Tree and animals</ThemedText>
      <ExtraRow sprite={`tree_${g.tree ? g.tree.stage : RULES.growth.tree_stages - 1}`} faded={!g.tree}
                title={g.tree ? `Your tree · stage ${g.tree.stage + 1} of ${RULES.growth.tree_stages}` : 'A tree'}
                line={g.tree ? 'Growing on its spot, for good.' : tree.kind === 'ready' ? 'It has a spot ready, right of the bed.'
                  : waitLine(tree, 'It comes with the top garden level,', TREE_CLOSED)}
                action={tree.kind === 'ready' ? 'Plant it · 1 choice' : null} enabled={canPay && !busy}
                onPress={() => run({ kind: 'buy_tree' }, 'tree_0', 'Planted: your tree. Watch it grow, stage by stage.')} />
      <ExtraRow sprite="chicken" faded={hens.kind === 'locked'}
                title={hens.kind === 'have' ? `Chickens · ${hens.count} of ${hens.max}` : 'Chickens'}
                line={hens.kind === 'have' ? 'They never get hungry or sick, and never leave.'
                  : hens.kind === 'ready' ? 'Your garden has a place for an animal.' : waitLine(hens, 'A place for an animal opens', HENS_CLOSED)}
                action={hens.kind === 'ready' ? 'Choose chickens · free' : hens.kind === 'have' && hens.count < hens.max ? 'Add one · 1 choice' : null}
                enabled={(hens.kind === 'ready' || canPay) && !busy}
                onPress={() => run(hens.kind === 'ready' ? { kind: 'choose_animal', item: 'chicken' } : { kind: 'add_animal', item: 'chicken' },
                  'chicken', hens.kind === 'ready' ? 'Your chickens have moved in, with their coop.' : 'Another chicken has joined.')} />
    </>
  );
}

/** The tree, or its empty spot from the top garden level: its 7 stages, or planting it. */
function TreeDetail(p: Props & { lines: string[] }) {
  const t = useTheme();
  const g = p.game;
  const { busy, done, error, run } = useRun(p.onAction);
  const status = treeStatus(g, RULES);
  const stages = RULES.growth.tree_stages;
  if (!g.tree) {
    return (
      <>
        <Done done={done} error={error} />
        {!done && <ThemedText type="small">{status.kind === 'ready' ? 'This spot is waiting for your tree.'
          : waitLine(status, 'It comes with the top garden level,', TREE_CLOSED)}</ThemedText>}
        {!done && status.kind === 'ready' && (
          <>
            <ThemedText type="small" themeColor="textSecondary">{choiceLine(g)}</ThemedText>
            <Action label="Plant the tree here · 1 choice" disabled={busy || g.choices.available < 1}
                    onPress={() => run({ kind: 'buy_tree' }, 'tree_0', 'Planted: your tree. Watch it grow, stage by stage.')} />
          </>
        )}
      </>
    );
  }
  return (
    <View style={styles.side}>
      <Sprite name={`tree_${g.tree.stage}`} min={40} max={72} />
      <View style={styles.sideText}>
        <Done done={done} error={error} />
        <View style={styles.track}>
          {Array.from({ length: stages }, (_, s) => (
            <View key={s} style={[styles.step, { backgroundColor: s <= g.tree!.stage ? t.reward : t.line }]} />
          ))}
        </View>
        <ThemedText type="smallBold">Stage {g.tree.stage + 1} of {stages}</ThemedText>
        {p.lines.map((l) => <ThemedText key={l} type="small">{l}</ThemedText>)}
        <ThemedText type="small" themeColor="textSecondary">
          A new stage about every {RULES.growth.tree_stage_growing_days} growing days.
        </ThemedText>
      </View>
    </View>
  );
}

/** The chickens (or their coop): how many, and one more for a choice. */
function Chickens(p: Props & { lines: string[] }) {
  const g = p.game;
  const { busy, done, error, run } = useRun(p.onAction);
  const s = animalStatus(g, RULES, 'chicken');
  const count = s.kind === 'have' ? s.count : 0;
  const max = RULES.garden.max_animals_per_type;
  return (
    <View style={styles.side}>
      <Sprite name="chicken" min={36} max={56} />
      <View style={styles.sideText}>
        <ThemedText type="smallBold">{count} of {max} chickens</ThemedText>
        {p.lines.map((l) => <ThemedText key={l} type="small">{l}</ThemedText>)}
        <Done done={done} error={error} />
        {count < max ? (
          <>
            <ThemedText type="small" themeColor="textSecondary">{choiceLine(g)}</ThemedText>
            <Action label="Add a chicken · 1 choice" disabled={busy || g.choices.available < 1}
                    onPress={() => run({ kind: 'add_animal', item: 'chicken' }, 'chicken', 'Another chicken has joined.')} />
          </>
        ) : <ThemedText type="small" themeColor="textSecondary">A full flock: {max} is the most.</ThemedText>}
      </View>
    </View>
  );
}

function Tile({ sprite, name, cost, enabled, owned, onPress }: {
  sprite: string; name: string; cost: string; enabled: boolean; owned: boolean; onPress: () => void;
}) {
  const t = useTheme();
  return (
    <Tap disabled={!enabled} onPress={onPress} accessibilityRole="button" accessibilityState={{ disabled: !enabled }}
         accessibilityLabel={`${name}: ${cost === '1 choice' ? 'one choice' : cost.replace('✓ ', '')}`}
         style={[styles.tile, { backgroundColor: t.card, borderColor: enabled ? t.accent : t.line, opacity: enabled || owned ? 1 : 0.5 }]}>
      <View style={styles.tileArt}><Sprite name={sprite} min={24} max={40} /></View>
      <ThemedText type="small" style={[styles.tileName, styles.center]} numberOfLines={2}>{name}</ThemedText>
      <ThemedText type="small" style={[styles.tileCost, { color: owned ? t.reward : enabled ? t.accent : t.textSecondary }]}>{cost}</ThemedText>
    </Tap>
  );
}

function ExtraRow({ sprite, title, line, action, enabled, faded, onPress }: {
  sprite: string; title: string; line: string; action: string | null; enabled: boolean; faded: boolean; onPress: () => void;
}) {
  const t = useTheme();
  return (
    <View style={[styles.extra, { backgroundColor: t.card }]}>
      <View style={[styles.tileArt, { opacity: faded ? 0.45 : 1 }]}><Sprite name={sprite} min={28} max={44} /></View>
      <View style={styles.sideText}>
        <ThemedText type="smallBold">{title}</ThemedText>
        {line !== '' && <ThemedText type="small" themeColor="textSecondary">{line}</ThemedText>}
        {action && <Action label={action} onPress={onPress} disabled={!enabled} />}
      </View>
    </View>
  );
}

function GardenTrack({ game }: { game: GameResponse }) {
  const t = useTheme();
  const levels = Object.entries(RULES.garden.level_at_qualifying_months).map(([lv, m]) => [Number(lv), m] as const);
  const next = levels.find(([lv]) => lv > game.garden.level);
  if (!game.garden.open || !next) return null;
  const prev = levels.find(([lv]) => lv === game.garden.level)?.[1] ?? 0;
  const fill = Math.min(Math.max((game.garden.qualifying_months - prev) / Math.max(next[1] - prev, 1), 0), 1);
  return (
    <View style={styles.trackWrap}>
      <View style={[styles.bar, { backgroundColor: t.line }]}>
        <View style={[styles.barFill, { width: `${fill * 100}%`, backgroundColor: t.reward }]} />
      </View>
      <ThemedText type="small" themeColor="textSecondary">Level {game.garden.level} → level {next[0]}</ThemedText>
    </View>
  );
}

function CoinJar(p: Props & { lines: React.ReactNode }) {
  const t = useTheme();
  const fills = RULES.coin_jar_fills_at_cushion;
  const next = cushionProgress(p.game, GAME_RULES).next;
  return (
    <View style={styles.side}>
      <Sprite name={`jar_${p.game.look.coin_jar}`} min={40} max={64} />
      <View style={styles.sideText}>
        {p.lines}
        <View style={styles.track}>
          {fills.map((m, i) => (
            <View key={m} style={styles.stepCol}>
              <View style={[styles.step, { backgroundColor: i < p.game.look.coin_jar ? t.watch : t.line }]} />
              <ThemedText type="small" themeColor="textSecondary" style={styles.stepLabel}>{m}</ThemedText>
            </View>
          ))}
        </View>
        {next && <ThemedText type="smallBold">{milestoneLine(next)}</ThemedText>}
        <Action label="See my cushion" onPress={() => p.onGo('money')} />
      </View>
    </View>
  );
}

function SavingsPlant(p: Props & { lines: React.ReactNode }) {
  const t = useTheme();
  const stages = RULES.savings_plant_stages_at_saved_months.length;
  return (
    <>
      <View style={styles.row}>
        {Array.from({ length: stages + 1 }, (_, s) => (
          <View key={s} style={[styles.stage, { borderColor: s === p.game.look.savings_plant ? t.accent : 'transparent',
                                                opacity: s <= p.game.look.savings_plant ? 1 : 0.4 }]}>
            <Sprite name={`plant_${s}`} min={18} max={36} />
          </View>
        ))}
      </View>
      {p.lines}
      <Action label="Open Money" onPress={() => p.onGo('money')} />
    </>
  );
}

function Action({ label, onPress, disabled, quiet }: { label: string; onPress: () => void; disabled?: boolean; quiet?: boolean }) {
  const t = useTheme();
  return (
    <Tap onPress={onPress} disabled={disabled} accessibilityRole="button" accessibilityState={{ disabled }}
         style={[styles.action, quiet ? { borderColor: t.line, borderWidth: 1 } : { backgroundColor: t.accent },
                 disabled && styles.disabled]}>
      <ThemedText type="small" style={[styles.actionText, { color: quiet ? t.text : t.onAccent }]}>{label}</ThemedText>
    </Tap>
  );
}

const styles = StyleSheet.create({
  card: { position: 'absolute', left: Spacing.three, right: Spacing.three, bottom: Spacing.three, borderRadius: Spacing.three,
          borderWidth: 1, paddingTop: Spacing.three, maxHeight: '62%' },
  head: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two, paddingHorizontal: Spacing.three },
  title: { flex: 1, fontSize: 16 },
  scroll: { flexGrow: 0 },
  body: { padding: Spacing.three, paddingTop: Spacing.two, gap: Spacing.two },
  side: { flexDirection: 'row', gap: Spacing.three, alignItems: 'flex-start' },
  sideText: { flex: 1, gap: Spacing.two },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  tile: { width: '23%', minWidth: 72, flexGrow: 1, alignItems: 'center', borderRadius: Spacing.two, borderWidth: 1,
          paddingVertical: Spacing.two, gap: Spacing.half },
  tileName: { fontSize: 12, fontWeight: 600 },
  tileArt: { minHeight: 40, justifyContent: 'flex-end', alignItems: 'center' },
  section: { marginTop: Spacing.two },
  extra: { flexDirection: 'row', gap: Spacing.three, alignItems: 'center', borderRadius: Spacing.two, padding: Spacing.two },
  doneRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three },
  flex: { flex: 1 },
  center: { textAlign: 'center', lineHeight: 15 },
  tileCost: { fontSize: 11, fontWeight: 600 },
  done: { alignItems: 'center', gap: Spacing.two, paddingVertical: Spacing.two },
  track: { flexDirection: 'row', gap: Spacing.one },
  trackWrap: { gap: Spacing.one },
  step: { flex: 1, height: 8, borderRadius: 4 },
  stepCol: { flex: 1, gap: Spacing.half },
  stepLabel: { fontSize: 11, textAlign: 'center' },
  bar: { height: 8, borderRadius: 4, overflow: 'hidden' },
  barFill: { height: 8, borderRadius: 4 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' },
  stage: { borderWidth: 2, borderRadius: Spacing.two, padding: Spacing.half, alignItems: 'center', justifyContent: 'flex-end', minHeight: 48 },
  action: { borderRadius: Spacing.three, minHeight: 44, alignItems: 'center', justifyContent: 'center', paddingHorizontal: Spacing.three },
  actionText: { fontWeight: 700 },
  disabled: { opacity: 0.45 },
});

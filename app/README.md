# FAST app (T-16)

The Expo (React Native) app of FAST: login, onboarding, add transactions, the Money screen (band,
health score, forecast with reasons, advice), the isometric home scene, the Future Self. The plan is
`../docs/app_plan.md` (screens, data flow, build order, what the user study needs on screen).

| | |
|---|---|
| Expo SDK | **58** (Expo 58.0.21, React Native 0.88, React 19.3, Expo Router 58, Reanimated 4.7, Skia 2.14, TypeScript 6): the version the Play Store's Expo Go runs (D-105, D-149). On Windows PowerShell start Metro with `npx.cmd expo start` if `npx` is blocked by the script policy |
| Routes | `src/app/` (every file is a screen; four tabs: Home, Money, Add, Future) |
| Logic without React Native | `src/lib/` (isometric placement, drawing order, time of day, band wording), tested by Node |
| Shared with the Python side | `../shared/` (thresholds, game rules) and `../assets/` (the art kit), read directly through Metro (`metro.config.js`): never copied by hand |

## Commands (from this folder; Node 24 LTS)

```bash
npm test              # the logic tests (Node's built-in runner, no extra install)
npm run typecheck     # TypeScript, the app and the tests
npm run sync-art      # copy the app icon and splash from ../assets/app after the art changes
npx expo start        # the development server; open it in Expo Go on the phone (same Wi-Fi)
npx expo install <p>  # add a package at the version that matches the SDK (not plain npm install)
```

On the 4 GB laptop, close the browser before `npx expo start` (Metro needs the memory). In Expo Go:
"Enter URL manually" → `exp://<laptop's Wi-Fi address>:8081` (same Wi-Fi as the phone).

## Notes

- The drawing order (`src/lib/depthSort.ts`) is a port of `tools/asset_generation/scenes.py`
  `depth_sort`; `src/lib/__tests__/fixtures/depth_sort.json` comes from the Python original
  (`python -m tools.app_fixtures`), and the test requires the same order.
- Tab icons are placeholders from the Expo template until FAST's own are drawn (T-22).
- `npm audit` reports issues in React Native's development tools; don't run `npm audit fix --force`
  (it breaks the SDK's version set). The phone app itself doesn't ship those tools.
- Secrets never go in the app (CLAUDE.md rule 7): only the Supabase URL, its public key and the API's
  address, as `EXPO_PUBLIC_*` values, once the Supabase project exists.

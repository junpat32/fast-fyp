// Metro (Expo's bundler) only sees files inside this project unless told otherwise. FAST's app reads
// two folders of the main repository directly, so they stay the single source (CLAUDE.md rule 5):
//   ../shared  thresholds.json and game.json (the same constants the Python engine uses)
//   ../assets  the isometric art kit (manifest.json, scenes, characters, PNGs)
const path = require("path");
const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);
config.watchFolders = [path.resolve(__dirname, "../shared"), path.resolve(__dirname, "../assets")];
// Files in those folders look for packages in app/node_modules too: since SDK 58 (React Native 0.88) every
// image asks for "react-native/asset-registry" from its own folder, and ../assets has no node_modules (D-149).
config.resolver.nodeModulesPaths = [path.resolve(__dirname, "node_modules")];

module.exports = config;

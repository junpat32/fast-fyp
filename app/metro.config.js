// Metro (Expo's bundler) only sees files inside this project unless told otherwise. FAST's app reads
// two folders of the main repository directly, so they stay the single source (CLAUDE.md rule 5):
//   ../shared  thresholds.json and game.json (the same constants the Python engine uses)
//   ../assets  the isometric art kit (manifest.json, scenes, characters, PNGs)
const path = require("path");
const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);
config.watchFolders = [path.resolve(__dirname, "../shared"), path.resolve(__dirname, "../assets")];

module.exports = config;

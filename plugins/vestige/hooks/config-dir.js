// config-dir: where the user's own vestige files live when the kit runs as a
// plugin. The plugin directory is a cache that is replaced on every update, so
// anything the user owns (the calibrated rule table, logs, guess-gate config)
// lives under the Claude config dir instead:
//   $CLAUDE_CONFIG_DIR (or ~/.claude)/vestige-patterns.js   calibrated rules
//   $CLAUDE_CONFIG_DIR (or ~/.claude)/vestige-scan.log      hit log
//   $CLAUDE_CONFIG_DIR (or ~/.claude)/guess-scan.log        guess-scan log
//   $CLAUDE_CONFIG_DIR (or ~/.claude)/guess-gate.json       guess-scan config

const fs = require('fs');
const path = require('path');
const os = require('os');

const configDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');

// The calibrated table wins when it exists. Otherwise the starter table that
// ships with the plugin is used.
function loadPatterns() {
  const userTable = path.join(configDir, 'vestige-patterns.js');
  if (fs.existsSync(userTable)) {
    try { return require(userTable); } catch (e) { /* broken user table: fall back */ }
  }
  return require('./vestige-patterns');
}

module.exports = { configDir, loadPatterns };

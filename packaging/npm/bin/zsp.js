#!/usr/bin/env node
/**
 * Thin launcher: hands off to the native binary that postinstall fetched,
 * forwarding arguments, stdio and the exit code unchanged.
 */

'use strict';

const path = require('path');
const fs = require('fs');
const { spawnSync } = require('child_process');

const binary = path.join(
  __dirname,
  process.platform === 'win32' ? 'zsp.exe' : 'zsp'
);

if (!fs.existsSync(binary)) {
  console.error(
    'zsp: binary missing — the postinstall step did not complete.\n' +
    'Reinstall with:  npm install -g zsp\n' +
    'Or use the Python package:  pipx install zsp'
  );
  process.exit(1);
}

// stdio: 'inherit' keeps the interactive login prompts working.
const result = spawnSync(binary, process.argv.slice(2), { stdio: 'inherit' });

if (result.error) {
  console.error(`zsp: ${result.error.message}`);
  process.exit(1);
}
process.exit(result.status === null ? 1 : result.status);

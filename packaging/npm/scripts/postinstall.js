#!/usr/bin/env node
/**
 * Downloads the prebuilt zsp binary for this platform.
 *
 * zsp is written in Python, but shipping a wrapper that shells out to a
 * system `python3` makes installation fail on machines without it. Fetching
 * the self-contained binary instead means npm users need nothing but node.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const https = require('https');
const crypto = require('crypto');
const { execSync } = require('child_process');

const REPO = 'sudoSharun/zsp';
const VERSION = require('../package.json').version;
const BIN_DIR = path.join(__dirname, '..', 'bin');

const TARGETS = {
  'darwin-arm64': 'macos-arm64',
  'darwin-x64': 'macos-x64',
  'linux-x64': 'linux-x64',
  'linux-arm64': 'linux-arm64',
  'win32-x64': 'windows-x64',
};

function target() {
  const key = `${process.platform}-${process.arch}`;
  const name = TARGETS[key];
  if (!name) {
    throw new Error(
      `No prebuilt zsp binary for ${key}.\n` +
      `Install from PyPI instead:  pipx install zsp`
    );
  }
  return name;
}

function download(url, destination, redirects = 0) {
  return new Promise((resolve, reject) => {
    if (redirects > 5) return reject(new Error('Too many redirects'));

    https.get(url, { headers: { 'User-Agent': 'zsp-npm-installer' } }, (response) => {
      // GitHub Releases redirect to a CDN.
      if ([301, 302, 307, 308].includes(response.statusCode)) {
        response.resume();
        return resolve(download(response.headers.location, destination, redirects + 1));
      }
      if (response.statusCode !== 200) {
        response.resume();
        return reject(new Error(`Download failed: HTTP ${response.statusCode} for ${url}`));
      }

      const file = fs.createWriteStream(destination);
      response.pipe(file);
      file.on('finish', () => file.close(resolve));
      file.on('error', reject);
    }).on('error', reject);
  });
}

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

async function main() {
  const platform = target();
  const isWindows = process.platform === 'win32';
  const archive = isWindows
    ? `zsp-${VERSION}-${platform}.zip`
    : `zsp-${VERSION}-${platform}.tar.gz`;
  const url = `https://github.com/${REPO}/releases/download/v${VERSION}/${archive}`;

  fs.mkdirSync(BIN_DIR, { recursive: true });
  const archivePath = path.join(BIN_DIR, archive);

  console.log(`zsp: downloading ${archive}`);
  await download(url, archivePath);

  // Verify against the checksums published with the release.
  try {
    const sumsPath = path.join(BIN_DIR, 'checksums.txt');
    await download(
      `https://github.com/${REPO}/releases/download/v${VERSION}/checksums.txt`,
      sumsPath
    );
    const expected = fs.readFileSync(sumsPath, 'utf8')
      .split('\n')
      .map((line) => line.trim().split(/\s+/))
      .find(([, name]) => name === archive);

    if (expected && expected[0] !== sha256(archivePath)) {
      throw new Error('Checksum mismatch — refusing to install.');
    }
    fs.unlinkSync(sumsPath);
  } catch (error) {
    if (String(error.message).includes('Checksum mismatch')) throw error;
    console.warn(`zsp: could not verify checksum (${error.message})`);
  }

  if (isWindows) {
    execSync(
      `powershell -NoProfile -Command "Expand-Archive -Force '${archivePath}' '${BIN_DIR}'"`,
      { stdio: 'inherit' }
    );
  } else {
    execSync(`tar -xzf "${archivePath}" -C "${BIN_DIR}"`, { stdio: 'inherit' });
    fs.chmodSync(path.join(BIN_DIR, 'zsp'), 0o755);
  }

  fs.unlinkSync(archivePath);
  console.log(`zsp ${VERSION} installed. Run "zsp login" to authenticate.`);
}

main().catch((error) => {
  console.error(`\nzsp: installation failed — ${error.message}\n`);
  console.error('Alternative:  pipx install zsp\n');
  process.exit(1);
});

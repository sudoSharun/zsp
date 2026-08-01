# Installation

`zsp` ships two ways:

- **From PyPI** — needs Python 3.9+, gets you the library too.
- **As a standalone binary** — no Python required; what Homebrew,
  Chocolatey, winget and npm install.

Pick whichever suits the machine. They are the same program.

---

## Python users

### pipx (recommended)

Installs into its own environment so it never collides with a project's
dependencies:

```bash
pipx install zsp
```

### uv

```bash
uv tool install zsp
```

### pip

```bash
pip install zsp
```

### One-off, no install

```bash
pipx run zsp items
uvx zsp items
```

---

## macOS / Linux

### Homebrew

```bash
brew tap sudoSharun/tap
brew install zsp
```

> Currently distributed through a personal tap. `homebrew-core` requires a
> project to be reasonably established (roughly 75+ stars and 30 days old),
> so that submission comes later.

Upgrade with `brew upgrade zsp`.

### Install script

```bash
curl -fsSL https://raw.githubusercontent.com/sudoSharun/zsp/main/install.sh | sh
```

Downloads the binary for your platform into `~/.local/bin`.

> Piping a script into a shell runs whatever the server sends. Read it
> first if you would rather not: the URL above opens fine in a browser, or
> download and inspect before running.

### Manual

Grab the archive for your platform from
[Releases](https://github.com/sudoSharun/zsp/releases),
extract, and put `zsp` on your `PATH`:

```bash
tar -xzf zsp-0.1.0-macos-arm64.tar.gz
sudo mv zsp /usr/local/bin/
```

---

## Windows

### winget

```powershell
winget install sudoSharun.zsp
```

### Chocolatey

```powershell
choco install zsp
```

### Scoop

```powershell
scoop bucket add sudoSharun https://github.com/sudoSharun/scoop-bucket
scoop install zsp
```

### Manual

Download `zsp-0.1.0-windows-x64.zip` from
[Releases](https://github.com/sudoSharun/zsp/releases),
extract, and add the folder to `PATH`.

---

## Node / npm

```bash
npm install -g zsp
```

The postinstall step downloads the prebuilt binary for your platform, so
**Python is not required**. This exists for teams whose tooling is already
npm-based; if you have Python, `pipx` is the more direct route.

---

## Docker

```bash
docker run --rm -it \
  -v "$HOME/.config/zsp:/root/.config/zsp" \
  ghcr.io/sudoSharun/zsp:latest items
```

Mounting `~/.config/zsp` keeps your credentials on the host and lets the
container reuse a login. Handy shell alias:

```bash
alias zsp='docker run --rm -it -v "$HOME/.config/zsp:/root/.config/zsp" ghcr.io/sudoSharun/zsp:latest'
```

`zsp login` needs a browser, so log in on the host first.

---

## From source

```bash
git clone https://github.com/sudoSharun/zsp
cd zsp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

---

## Verifying

```console
$ zsp --version
zsp 0.1.0
```

Binary releases are published with SHA256 checksums:

```bash
curl -LO https://github.com/sudoSharun/zsp/releases/download/v0.1.0/checksums.txt
sha256sum -c checksums.txt --ignore-missing
```

## Uninstalling

| Installed with | Remove |
|---|---|
| pipx | `pipx uninstall zsp` |
| uv | `uv tool uninstall zsp` |
| pip | `pip uninstall zsp` |
| Homebrew | `brew uninstall zsp` |
| Chocolatey | `choco uninstall zsp` |
| winget | `winget uninstall sudoSharun.zsp` |
| npm | `npm uninstall -g zsp` |
| script/manual | delete the binary from your `PATH` |

Credentials are separate. To remove those too:

```bash
zsp logout          # or: rm -rf ~/.config/zsp
```

## Which should I use?

| Situation | Use |
|---|---|
| You write Python | `pipx` |
| macOS, no strong preference | Homebrew |
| Windows | winget |
| CI pipeline | `pip install` pinned, or the Docker image |
| No Python and no package manager | install script or manual binary |
| Contributing | from source |

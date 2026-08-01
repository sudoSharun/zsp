#!/bin/sh
# Installs the zsp binary for the current platform.
#
#   curl -fsSL https://raw.githubusercontent.com/sudoSharun/zsp/main/install.sh | sh
#
# Environment:
#   ZSP_VERSION    version to install (default: latest release)
#   ZSP_INSTALL_DIR  target directory (default: ~/.local/bin)
#
# Downloads are checksum-verified against the release's checksums.txt.

set -eu

REPO="sudoSharun/zsp"
INSTALL_DIR="${ZSP_INSTALL_DIR:-$HOME/.local/bin}"

info() { printf '\033[0;34m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[0;33mwarning:\033[0m %s\n' "$1" >&2; }
die()  { printf '\033[0;31merror:\033[0m %s\n' "$1" >&2; exit 1; }

need() {
    command -v "$1" >/dev/null 2>&1 || die "$1 is required but not installed"
}

detect_target() {
    os=$(uname -s)
    arch=$(uname -m)

    case "$os" in
        Darwin) os_name="macos" ;;
        Linux)  os_name="linux" ;;
        *) die "Unsupported OS: $os. Try: pipx install zsp" ;;
    esac

    case "$arch" in
        x86_64|amd64) arch_name="x64" ;;
        arm64|aarch64) arch_name="arm64" ;;
        *) die "Unsupported architecture: $arch. Try: pipx install zsp" ;;
    esac

    echo "${os_name}-${arch_name}"
}

latest_version() {
    curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
        | grep '"tag_name"' \
        | head -1 \
        | sed 's/.*"tag_name": *"v\{0,1\}\([^"]*\)".*/\1/'
}

verify() {
    archive_path="$1"
    archive_name="$2"
    sums_url="$3"

    if command -v sha256sum >/dev/null 2>&1; then
        actual=$(sha256sum "$archive_path" | cut -d' ' -f1)
    elif command -v shasum >/dev/null 2>&1; then
        actual=$(shasum -a 256 "$archive_path" | cut -d' ' -f1)
    else
        warn "no sha256 tool found; skipping checksum verification"
        return 0
    fi

    expected=$(curl -fsSL "$sums_url" 2>/dev/null | grep " $archive_name\$" | cut -d' ' -f1) || true
    if [ -z "$expected" ]; then
        warn "no checksum published for $archive_name; skipping verification"
        return 0
    fi
    [ "$actual" = "$expected" ] || die "checksum mismatch — refusing to install"
    info "checksum verified"
}

main() {
    need curl
    need tar

    target=$(detect_target)
    version="${ZSP_VERSION:-$(latest_version)}"
    [ -n "$version" ] || die "could not determine the latest version"

    archive="zsp-${version}-${target}.tar.gz"
    base="https://github.com/$REPO/releases/download/v${version}"

    info "installing zsp ${version} (${target})"

    tmp=$(mktemp -d)
    # shellcheck disable=SC2064
    trap "rm -rf '$tmp'" EXIT

    curl -fsSL "$base/$archive" -o "$tmp/$archive" \
        || die "download failed — does a release exist for v${version}?"

    verify "$tmp/$archive" "$archive" "$base/checksums.txt"

    tar -xzf "$tmp/$archive" -C "$tmp"
    mkdir -p "$INSTALL_DIR"
    mv "$tmp/zsp" "$INSTALL_DIR/zsp"
    chmod +x "$INSTALL_DIR/zsp"

    info "installed to $INSTALL_DIR/zsp"

    case ":$PATH:" in
        *":$INSTALL_DIR:"*) ;;
        *)
            warn "$INSTALL_DIR is not on your PATH. Add it:"
            printf '\n    export PATH="%s:$PATH"\n\n' "$INSTALL_DIR"
            ;;
    esac

    info "next: zsp login"
}

main "$@"

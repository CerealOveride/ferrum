# Maintainer: CerealOveride <150073255+CerealOveride@users.noreply.github.com>
# Contributor packaging for Arch User Repository

pkgname=ferrum-fm
_pkgname=ferrum
pkgver=0.1.2
pkgrel=1
pkgdesc="DE-agnostic TUI file manager with SMB shares (command: fe)"
arch=('any')
url="https://github.com/CerealOveride/ferrum"
license=('MIT')
depends=(
  'python'
  'python-textual'
  'python-aiofiles'
  'python-smbprotocol'
  'python-send2trash'
  'python-keyring'
  'python-keyrings-alt'
  'python-rich'
  'python-jeepney'
  'xdg-utils'
)
optdepends=(
  'noto-fonts-emoji: emoji glyphs in the TUI'
)
makedepends=(
  'python-build'
  'python-installer'
  'python-wheel'
  'python-hatchling'
)
provides=('ferrum-fm')
conflicts=()
source=("$_pkgname-$pkgver.tar.gz::https://github.com/CerealOveride/ferrum/archive/refs/tags/v$pkgver.tar.gz")
# sha256 of GitHub's v0.1.2 tag tarball (verified 2026-10-23).
sha256sums=('4d24f8fafafe906a7aaa72e39a597cd7e0033602e2140743caffd0f92ed26e84')

build() {
  cd "$_pkgname-$pkgver"
  # Never reuse wheels that may be present in the source tree (old tarballs
  # shipped stale dist/*.whl, which caused "File already exists: usr/bin/fe").
  rm -rf dist build
  python -m build --wheel --no-isolation --outdir dist
}

package() {
  cd "$_pkgname-$pkgver"
  python -m installer --destdir="$pkgdir" "dist/ferrum_fm-$pkgver-py3-none-any.whl"
  install -Dm644 ferrum.desktop "$pkgdir/usr/share/applications/ferrum.desktop"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}

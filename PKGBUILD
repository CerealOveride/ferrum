# Maintainer: CerealOveride <150073255+CerealOveride@users.noreply.github.com>
# Contributor packaging for Arch User Repository

pkgname=ferrum-fm
_pkgname=ferrum
pkgver=0.1.1
pkgrel=2
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
  'python-setuptools'
)
provides=('ferrum-fm')
conflicts=()
source=("$_pkgname-$pkgver.tar.gz::https://github.com/CerealOveride/ferrum/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('832fd857e3c6bad2b1c8c1faea8c75c05dcb29b7bccebbdc07ee7b13efa77c6a')

build() {
  cd "$_pkgname-$pkgver"
  python -m build --wheel --no-isolation
}

package() {
  cd "$_pkgname-$pkgver"
  python -m installer --destdir="$pkgdir" dist/*.whl
  install -Dm644 ferrum.desktop "$pkgdir/usr/share/applications/ferrum.desktop"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}

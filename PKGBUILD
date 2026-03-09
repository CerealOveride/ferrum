# Maintainer: CerealOveride <150073255+CerealOveride@users.noreply.github.com>
pkgname=ferrum
pkgver=0.1.0
pkgrel=1
pkgdesc="A fast, stable, DE-agnostic TUI file manager with SMB support"
arch=('any')
url="https://github.com/CerealOveride/ferrum"
license=('MIT')
depends=(
    'python'
    'python-pip'
    'xdg-utils'
    'noto-fonts-emoji'
)
makedepends=(
    'python-build'
    'python-installer'
    'python-hatchling'
)
source=("$pkgname-$pkgver.tar.gz::https://github.com/CerealOveride/ferrum/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('bef24915e9e65f757520c636a5119ecc0e306c6ec4b2ca08362b606478c9f25a')

build() {
    cd "$pkgname-$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "$pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl

    # Install bundled wheels for PyPI-only deps
    install -dm755 "$pkgdir/usr/share/ferrum/wheels"
    install -m644 debian_deps/*.whl "$pkgdir/usr/share/ferrum/wheels/"

    # Install desktop file
    install -Dm644 ferrum.desktop "$pkgdir/usr/share/applications/ferrum.desktop"

    # Install bundled deps via pip into package dir
    pip install \
        --no-index \
        --find-links="$pkgdir/usr/share/ferrum/wheels" \
        --target="$pkgdir/usr/lib/python3/dist-packages" \
        --quiet \
        smbprotocol pyspnego textual aiofiles send2trash \
        keyring keyrings.alt rich cryptography
}

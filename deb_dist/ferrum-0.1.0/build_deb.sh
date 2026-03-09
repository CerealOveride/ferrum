#!/bin/bash
set -e

cd ~/ferrum
rm -rf dist/ deb_dist/
python3 -m build --sdist
py2dsc --maintainer "CerealOveride <150073255+CerealOveride@users.noreply.github.com>" dist/ferrum-0.1.0.tar.gz

# Inject postinst script
cp debian_scripts/postinst deb_dist/ferrum-0.1.0/debian/postinst
chmod 755 deb_dist/ferrum-0.1.0/debian/postinst

# Update postinst to use correct wheel path
sed -i 's|/usr/share/ferrum/wheels|/usr/share/ferrum/wheels|g' deb_dist/ferrum-0.1.0/debian/postinst

cd deb_dist/ferrum-0.1.0
dpkg-buildpackage -us -uc -b

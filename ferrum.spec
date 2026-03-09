Name:           ferrum
Version:        0.1.0
Release:        1%{?dist}
Summary:        A fast, stable, DE-agnostic TUI file manager with SMB support

License:        MIT
URL:            https://github.com/CerealOveride/ferrum
Source0:        https://github.com/CerealOveride/ferrum/archive/refs/tags/v%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-pip

Requires:       python3
Requires:       python3-pip
Requires:       xdg-utils

%description
Ferrum is a fast, stable, DE-agnostic TUI file manager built with Python
and Textual. It supports local and SMB filesystems, tabs, bookmarks,
preview pane, and cross-backend file operations.

%prep
%autosetup -n %{name}-%{version}

%build
python3 -m pip wheel --no-deps --wheel-dir dist .

%install
# Install the wheel
python3 -m pip install \
    --no-index \
    --no-deps \
    --root=%{buildroot} \
    --prefix=/usr \
    --force-reinstall \
    dist/ferrum-*.whl

# Install bundled dependency wheels
install -dm755 %{buildroot}/usr/share/ferrum/wheels
install -m644 debian_deps/*.whl %{buildroot}/usr/share/ferrum/wheels/

# Install desktop file
install -Dm644 ferrum.desktop %{buildroot}/usr/share/applications/ferrum.desktop

# Install license
install -Dm644 LICENSE %{buildroot}/usr/share/licenses/ferrum/LICENSE

%post
WHEELS_DIR="/usr/share/ferrum/wheels"
if [ -d "$WHEELS_DIR" ]; then
    pip3 install \
        --no-index \
        --find-links="$WHEELS_DIR" \
        --quiet \
        smbprotocol pyspnego textual aiofiles send2trash \
        keyring keyrings.alt rich cryptography \
        2>/dev/null || true
fi

%files
%{_bindir}/fe
%{_bindir}/ferrum
/usr/lib/python3/dist-packages/ferrum/
/usr/lib/python3/dist-packages/ferrum-*.dist-info/
/usr/share/ferrum/wheels/
/usr/share/applications/ferrum.desktop
/usr/share/licenses/ferrum/LICENSE

%changelog
* Mon Mar 09 2026 CerealOveride <150073255+CerealOveride@users.noreply.github.com> - 0.1.0-1
- Initial release

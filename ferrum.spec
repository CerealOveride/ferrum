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
BuildRequires:  python3-build
BuildRequires:  python3-installer

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
python3 -m build --wheel --no-isolation

%install
python3 -m installer --destdir=%{buildroot} dist/*.whl

# Install bundled wheels
install -dm755 %{buildroot}%{_datadir}/ferrum/wheels
install -m644 debian_deps/*.whl %{buildroot}%{_datadir}/ferrum/wheels/

# Install desktop file
install -Dm644 ferrum.desktop %{buildroot}%{_datadir}/applications/ferrum.desktop

%post
WHEELS_DIR="%{_datadir}/ferrum/wheels"
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
%license LICENSE
%{_bindir}/fe
%{_bindir}/ferrum
%{python3_sitelib}/ferrum/
%{python3_sitelib}/ferrum-*.dist-info/
%{_datadir}/ferrum/wheels/
%{_datadir}/applications/ferrum.desktop

%changelog
* Mon Mar 09 2026 CerealOveride <150073255+CerealOveride@users.noreply.github.com> - 0.1.0-1
- Initial release

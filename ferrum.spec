Name:           ferrum
Version:        0.1.2
Release:        1%{?dist}
Summary:        A fast, stable, DE-agnostic TUI file manager with SMB support

License:        MIT
URL:            https://github.com/CerealOveride/ferrum
Source0:        https://github.com/CerealOveride/ferrum/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros
BuildRequires:  desktop-file-utils

Requires:       xdg-utils

%description
Ferrum is a fast, stable, DE-agnostic TUI file manager built with Python
and Textual. It supports local and SMB filesystems, tabs, bookmarks,
preview pane, and cross-backend file operations.

%prep
%autosetup -n %{name}-%{version}
# Never reuse stale build artifacts that may exist in the source tree.
rm -rf dist build

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files ferrum
install -Dm644 ferrum.desktop %{buildroot}%{_datadir}/applications/ferrum.desktop

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ferrum.desktop

%files -f %{pyproject_files}
%license LICENSE
%doc README.md
%{_bindir}/fe
%{_bindir}/ferrum
%{_datadir}/applications/ferrum.desktop

%changelog
* Fri Oct 23 2026 CerealOveride <150073255+CerealOveride@users.noreply.github.com> - 0.1.2-1
- SMB: fix credential prompt loop, persist dialog username, treat
  STATUS_LOGON_FAILURE as an auth failure, prefer typed password
- Packaging: standard pyproject macros; Python deps auto-generated from metadata

* Mon Mar 09 2026 CerealOveride <150073255+CerealOveride@users.noreply.github.com> - 0.1.0-1
- Initial release

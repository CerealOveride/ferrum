# Ferrum

A fast, stable, DE-agnostic TUI file manager built with Python and Textual.

## Features

- Browse local and SMB filesystems
- Tabs with independent navigation
- Collapsible sidebar with places, bookmarks, and saved network shares
- Toggleable preview pane with syntax highlighting
- Copy, cut, paste with conflict resolution
- Trash and permanent delete with confirmation
- Rename and new directory
- Multi-file selection with space and shift+click
- SMB credentials stored in system keyring
- Persistent SMB connections across sessions

## Installation

### From pip
pip install ferrum

### On NixOS
See ferrum.nix

## Usage
fe

## Hyprland / Bare Wayland Compositor Users

The `.desktop` file uses `Terminal=true` which works with most desktop environments (GNOME, KDE, XFCE). If you're using Hyprland or another bare Wayland compositor that doesn't have a default terminal association, you may need to edit the desktop entry to explicitly specify your terminal emulator:
```
Exec=kitty fe
```

Replace `kitty` with your preferred terminal (`foot`, `alacritty`, `wezterm`, etc.).

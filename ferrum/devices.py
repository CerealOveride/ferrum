"""
Device monitor using udisks2 D-Bus API (jeepney, async).

Enumerates mounted block devices and watches for hot-plug events.
Calls on_added / on_removed synchronously from the asyncio task
so callers can use call_later() or post_message() to update the UI.
"""

import asyncio
from dataclasses import dataclass
from typing import Callable, Optional

from jeepney import DBusAddress, MatchRule, new_method_call
from jeepney.bus_messages import message_bus
from jeepney.io.asyncio import open_dbus_router
from jeepney.low_level import HeaderFields


# Filesystem types that should never appear in the sidebar.
VIRTUAL_FS_TYPES = frozenset({
    "tmpfs", "devtmpfs", "sysfs", "proc", "devpts",
    "cgroup", "cgroup2", "pstore", "efivarfs", "bpf",
    "securityfs", "hugetlbfs", "mqueue", "debugfs", "tracefs",
    "configfs", "fusectl", "fuse.gvfsd-fuse", "squashfs",
    "overlay", "ramfs", "pipefs", "sockfs", "anon_inodefs",
    "autofs", "rpc_pipefs",
})

_UDISKS2 = "org.freedesktop.UDisks2"
_OBJMGR  = "org.freedesktop.DBus.ObjectManager"
_PROPS   = "org.freedesktop.DBus.Properties"
_DRIVE   = "org.freedesktop.UDisks2.Drive"
_BLOCK   = "org.freedesktop.UDisks2.Block"
_FS      = "org.freedesktop.UDisks2.Filesystem"


@dataclass
class DeviceEntry:
    obj_path: str
    label: str
    mount_point: str
    removable: bool


# ── D-Bus value helpers ────────────────────────────────────────────────────────

def _v(prop, default=None):
    """Unwrap a (signature, value) D-Bus variant tuple."""
    if isinstance(prop, tuple) and len(prop) == 2 and isinstance(prop[0], str):
        return prop[1]
    return default if prop is None else prop


def _decode_mps(raw) -> list[str]:
    """Convert an 'aay' mount-points value to a list of str paths."""
    mps = _v(raw, [])
    if isinstance(mps, (list, tuple)):
        result = []
        for mp in mps:
            if isinstance(mp, (bytes, bytearray)):
                result.append(mp.rstrip(b"\x00").decode("utf-8", errors="replace"))
            elif isinstance(mp, str):
                result.append(mp.rstrip("\x00"))
        return result
    return []


# ── Device parsing ─────────────────────────────────────────────────────────────

def _parse_device(
    obj_path: str,
    ifaces: dict,
    drives: dict[str, bool],
) -> Optional[DeviceEntry]:
    """Return a DeviceEntry if this object should appear in the sidebar."""
    if _FS not in ifaces:
        return None

    fs    = ifaces[_FS]
    block = ifaces.get(_BLOCK, {})

    if _v(block.get("HintIgnore"), False):
        return None

    id_type = _v(block.get("IdType"), "")
    if id_type in VIRTUAL_FS_TYPES:
        return None

    mps = _decode_mps(fs.get("MountPoints"))
    if not mps:
        return None
    # Skip root filesystem
    if "/" in mps:
        return None

    drive_path = _v(block.get("Drive"), "")
    removable  = bool(drives.get(drive_path, False))

    label = (_v(block.get("IdLabel"), "")
             or _v(block.get("HintName"), ""))
    if not label:
        mp    = mps[0]
        label = mp.rstrip("/").rsplit("/", 1)[-1] or mp

    return DeviceEntry(
        obj_path=obj_path,
        label=label,
        mount_point=mps[0],
        removable=removable,
    )


# ── Monitor ────────────────────────────────────────────────────────────────────

class DeviceMonitor:
    """
    One-shot query + continuous signal watcher for udisks2 block devices.

    on_added(entry: DeviceEntry) and on_removed(obj_path: str) are called
    synchronously from the asyncio task — use Widget.call_later() to schedule
    safe Textual UI updates.
    """

    def __init__(
        self,
        on_added: Callable[[DeviceEntry], None],
        on_removed: Callable[[str], None],
    ) -> None:
        self.on_added   = on_added
        self.on_removed = on_removed

        self._task: Optional[asyncio.Task] = None
        self._drives:  dict[str, bool]        = {}   # drive obj_path → removable
        self._objects: dict[str, dict]        = {}   # block obj_path → ifaces
        self._shown:   dict[str, DeviceEntry] = {}   # currently shown entries

    # ── Public API ─────────────────────────────────────────────────────────────

    async def get_initial(self) -> list[DeviceEntry]:
        """Fetch and return the current list of visible devices."""
        async with open_dbus_router(bus="SYSTEM") as router:
            return await self._fetch_all(router)

    def start(self) -> None:
        """Start the background signal-watching task."""
        self._task = asyncio.create_task(self._run())

    def stop(self) -> None:
        """Cancel the background task."""
        if self._task:
            self._task.cancel()
            self._task = None

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _fetch_all(self, router) -> list[DeviceEntry]:
        addr  = DBusAddress("/org/freedesktop/UDisks2",
                            bus_name=_UDISKS2, interface=_OBJMGR)
        reply = await router.send_and_get_reply(new_method_call(addr, "GetManagedObjects"))
        objects: dict = reply.body[0]

        # Build drives map first so _parse_device can look up removable.
        self._drives = {}
        for path, ifaces in objects.items():
            if _DRIVE in ifaces:
                d = ifaces[_DRIVE]
                self._drives[path] = bool(_v(d.get("Removable"), False))

        # Cache all objects for PropertiesChanged diffing.
        self._objects = {path: dict(ifaces) for path, ifaces in objects.items()}

        entries: list[DeviceEntry] = []
        self._shown = {}
        for path, ifaces in objects.items():
            entry = _parse_device(path, ifaces, self._drives)
            if entry:
                self._shown[path] = entry
                entries.append(entry)

        return entries

    # ── Signal handlers ────────────────────────────────────────────────────────

    def _handle_interfaces_added(self, obj_path: str, ifaces: dict) -> None:
        # Update drives map.
        if _DRIVE in ifaces:
            d = ifaces[_DRIVE]
            self._drives[obj_path] = bool(_v(d.get("Removable"), False))

        # Merge into object cache.
        if obj_path not in self._objects:
            self._objects[obj_path] = {}
        self._objects[obj_path].update(ifaces)

        entry = _parse_device(obj_path, self._objects[obj_path], self._drives)
        if entry and obj_path not in self._shown:
            self._shown[obj_path] = entry
            self.on_added(entry)

    def _handle_interfaces_removed(self, obj_path: str, iface_names: list) -> None:
        # Remove from cache.
        if obj_path in self._objects:
            for iface in iface_names:
                self._objects[obj_path].pop(iface, None)
            if not self._objects[obj_path]:
                del self._objects[obj_path]

        self._drives.pop(obj_path, None)

        if obj_path in self._shown:
            del self._shown[obj_path]
            self.on_removed(obj_path)

    def _handle_properties_changed(
        self, obj_path: str, iface_name: str, changed: dict
    ) -> None:
        if iface_name != _FS:
            return
        if obj_path not in self._objects:
            return

        # Patch cached properties.
        if iface_name in self._objects[obj_path]:
            self._objects[obj_path][iface_name].update(changed)
        else:
            self._objects[obj_path][iface_name] = changed

        was_shown = obj_path in self._shown
        entry = _parse_device(obj_path, self._objects[obj_path], self._drives)

        if entry and not was_shown:
            self._shown[obj_path] = entry
            self.on_added(entry)
        elif not entry and was_shown:
            del self._shown[obj_path]
            self.on_removed(obj_path)

    # ── Background run loop ────────────────────────────────────────────────────

    async def _run(self) -> None:
        try:
            async with open_dbus_router(bus="SYSTEM") as router:
                # Re-seed object cache using this connection so PropertiesChanged
                # diffs have a complete baseline even without a prior get_initial().
                if not self._objects:
                    await self._fetch_all(router)

                rule_added = MatchRule(
                    type="signal", sender=_UDISKS2,
                    interface=_OBJMGR, member="InterfacesAdded",
                )
                rule_removed = MatchRule(
                    type="signal", sender=_UDISKS2,
                    interface=_OBJMGR, member="InterfacesRemoved",
                )
                rule_props = MatchRule(
                    type="signal", sender=_UDISKS2,
                    interface=_PROPS, member="PropertiesChanged",
                )

                await router.send_and_get_reply(message_bus.AddMatch(rule_added))
                await router.send_and_get_reply(message_bus.AddMatch(rule_removed))
                await router.send_and_get_reply(message_bus.AddMatch(rule_props))

                with (router.filter(rule_added)  as q_added,
                      router.filter(rule_removed) as q_removed,
                      router.filter(rule_props)   as q_props):
                    await asyncio.gather(
                        self._loop_added(q_added),
                        self._loop_removed(q_removed),
                        self._loop_props(q_props),
                    )
        except asyncio.CancelledError:
            pass
        except Exception:
            pass  # D-Bus not available or session ended

    async def _loop_added(self, queue: asyncio.Queue) -> None:
        while True:
            msg = await queue.get()
            obj_path, ifaces = msg.body
            self._handle_interfaces_added(obj_path, ifaces)

    async def _loop_removed(self, queue: asyncio.Queue) -> None:
        while True:
            msg = await queue.get()
            obj_path, iface_names = msg.body
            self._handle_interfaces_removed(obj_path, list(iface_names))

    async def _loop_props(self, queue: asyncio.Queue) -> None:
        while True:
            msg = await queue.get()
            obj_path   = msg.header.fields.get(HeaderFields.path, "")
            iface_name = msg.body[0]
            changed    = msg.body[1]
            self._handle_properties_changed(obj_path, iface_name, changed)

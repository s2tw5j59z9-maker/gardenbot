"""
GardenBot (standalone) -- Wizard101 garden auto-planter.

Hooks the running Wizard101 client. Then:
    CTRL+ALT+G  -> plant the bed you're standing in (opens menu, top-down freecam, plants all)
    CTRL+ALT+H  -> harvest every ready plant in the bed (teleports to each, taps X; loops til done)
    CTRL+ALT+S  -> scan: write _garden_scan.txt (your soil plots + sizes -- use to set SEED_SLOT)
    CTRL+ALT+K  -> quit

Setup once: open Wizard101, log in, go stand in your garden, then run this. Edit SEED_SLOT in
gardener.py so each soil size maps to the right seed slot on your Seeds tab.

USE AT YOUR OWN RISK. Automating Wizard101 violates its Terms of Service and can get the
account banned. This reads and writes the game's memory (same technique as the wizwalker /
Deimos projects it is built on). Run it only on an account you accept that risk for.
"""
import asyncio
import sys

from loguru import logger
from wizwalker import ClientHandler, Keycode, HotkeyListener, ModifierKeys

import gardener

MODS = ModifierKeys.CTRL | ModifierKeys.ALT | ModifierKeys.NOREPEAT


async def main():
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | {message}")

    handler = ClientHandler()
    clients = handler.get_new_clients()
    if not clients:
        print("No Wizard101 window found. Launch Wizard101, log in past the loading screens,")
        print("then run this again.")
        return

    client = handler.get_foreground_client() or clients[0]
    print(f"Found {len(clients)} Wizard101 client(s). Hooking the active one...")
    try:
        await client.activate_hooks()
    except Exception as e:
        print(f"\nFailed to hook Wizard101: {e}")
        print("Checklist: Wizard101 fully loaded (past loading screens); run this as the SAME")
        print("Windows user as the game; no other bot (e.g. Deimos) already hooked it. Then retry.")
        await handler.close()
        return

    print("\nHooked. Stand in your garden bed, then:")
    print("   CTRL+ALT+G = plant   CTRL+ALT+H = harvest   CTRL+ALT+S = scan soil   CTRL+ALT+K = quit\n")

    stop_event = asyncio.Event()
    busy = asyncio.Lock()

    async def _guarded(coro_fn, done_msg):
        if busy.locked():
            print("(still working on the last command...)")
            return
        async with busy:
            try:
                await coro_fn(client)
            except Exception as e:
                logger.error(f"command failed: {e}")
            if done_msg:
                print(done_msg)

    async def plant():
        await _guarded(gardener.run_diagnostic,
                       "Done. Reposition / restock, then CTRL+ALT+G again. CTRL+ALT+K to quit.\n")

    async def harvest():
        await _guarded(gardener.run_harvest,
                       "Harvest done. CTRL+ALT+H again to re-sweep, CTRL+ALT+G to plant, CTRL+ALT+K to quit.\n")

    async def scan():
        await _guarded(gardener.garden_scan,
                       f"Scan written next to gardener.py (_garden_scan.txt).\n")

    async def quit_bot():
        print("Quitting -- restoring camera and unhooking...")
        stop_event.set()

    listener = HotkeyListener()
    await listener.add_hotkey(Keycode.G, plant, modifiers=MODS)
    await listener.add_hotkey(Keycode.H, harvest, modifiers=MODS)
    await listener.add_hotkey(Keycode.S, scan, modifiers=MODS)
    await listener.add_hotkey(Keycode.K, quit_bot, modifiers=MODS)
    listener.start()
    try:
        await stop_event.wait()
    finally:
        with_suppress = (Exception,)
        try:
            await listener.stop()
        except with_suppress:
            pass
        try:
            await client.close()
        except with_suppress:
            pass
        try:
            await handler.close()
        except with_suppress:
            pass
        print("Done. Camera and hooks restored.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

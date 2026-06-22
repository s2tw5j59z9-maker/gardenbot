"""
Installer for the GardenBot Deimos add-on.

Copies gardener.py + world_to_screen.py into your Deimos `src/` folder, then tells you the
small Deimos.py edit that binds the Ctrl+Alt+G (plant) and Ctrl+Alt+H (harvest) hotkeys.

Usage:
    python install.py "C:\\path\\to\\Deimos-Wizard101"

If you omit the path it looks for a Deimos folder next to this installer and one level up.
This only COPIES files (backing up any it overwrites as .bak); it does NOT edit Deimos.py for
you -- that snippet is printed so you can paste it where it fits your Deimos version.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ["gardener.py", "world_to_screen.py"]

WIRING = r'''
# ---- 1) hotkey handlers (put them next to the other `async def *_hotkey()` handlers) ----
	async def garden_hotkey():
		# Ctrl+Alt+G -> plant. Reload each press so edits to gardener.py apply without a restart.
		import importlib
		from src import gardener
		try:
			importlib.reload(gardener)
		except Exception as e:
			logger.error(f'[garden] reload failed: {e}')
		c = get_foreground_client()          # any hooked wizwalker Client works here
		if c is None:
			logger.warning('[garden] no hooked client selected.')
			return
		await gardener.run_diagnostic(c)

	async def harvest_hotkey():
		# Ctrl+Alt+H -> harvest every ready plant. Reload each press so edits apply.
		import importlib
		from src import gardener
		try:
			importlib.reload(gardener)
		except Exception as e:
			logger.error(f'[garden] reload failed: {e}')
		c = get_foreground_client()
		if c is None:
			logger.warning('[garden] no hooked client selected.')
			return
		await gardener.run_harvest(c)

# ---- 2) register them where the listener is set up (near the other add_hotkey calls) ----
	_gmods = ModifierKeys.CTRL | ModifierKeys.ALT | ModifierKeys.NOREPEAT
	try:
		await listener.add_hotkey(Keycode.G, garden_hotkey, modifiers=_gmods)
		await listener.add_hotkey(Keycode.H, harvest_hotkey, modifiers=_gmods)
		logger.debug("Garden hotkeys bound: G (plant) / H (harvest) ['CTRL', 'ALT']")
	except Exception as e:
		logger.debug(f'Failed to register garden hotkeys: {e}')

# ---- NOTE: if your Deimos disables hotkeys when the client loses focus (an enable/disable
#      cycle with an "always-bound" exclude list), add "garden"/"harvest" to that exclude
#      list too -- otherwise these stop firing after the first tab-out. ----
'''


def find_deimos(arg):
    candidates = []
    if arg:
        candidates.append(arg)
    candidates += [
        os.path.join(HERE, "Deimos-Wizard101"),
        os.path.join(os.path.dirname(HERE), "Deimos-Wizard101"),
        os.getcwd(),
    ]
    for c in candidates:
        if c and os.path.isfile(os.path.join(c, "Deimos.py")) and os.path.isdir(os.path.join(c, "src")):
            return os.path.abspath(c)
    return None


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    deimos = find_deimos(arg)
    if not deimos:
        print("Could not find your Deimos folder (it needs both Deimos.py and a src/ folder).")
        print('Run:  python install.py "C:\\path\\to\\Deimos-Wizard101"')
        return

    print(f"Deimos found: {deimos}")
    src = os.path.join(deimos, "src")
    for f in FILES:
        s = os.path.join(HERE, f)
        d = os.path.join(src, f)
        if not os.path.isfile(s):
            print(f"  ! missing {f} next to this installer; skipping")
            continue
        backed_up = False
        if os.path.isfile(d):
            shutil.copy2(d, d + ".bak")
            backed_up = True
        shutil.copy2(s, d)
        print(f"  copied {f} -> src/{f}" + ("  (existing backed up as .bak)" if backed_up else ""))

    dp = os.path.join(deimos, "Deimos.py")
    try:
        txt = open(dp, encoding="utf-8").read()
    except Exception:
        txt = ""
    if "run_harvest" in txt and "run_diagnostic" in txt:
        print("\nDeimos.py already wires both gardener hotkeys -- you're set. Restart Deimos;")
        print("Ctrl+Alt+G plants, Ctrl+Alt+H harvests.")
    else:
        print("\nLast step: add the hotkeys to Deimos.py (handlers + registrations), then restart")
        print("Deimos. Paste this where it fits your version (see README.md). If garden_hotkey is")
        print("already present, just add the harvest_hotkey handler + its add_hotkey line:")
        print(WIRING)
    print("Then: stand in your garden -- CTRL+ALT+G plants, CTRL+ALT+H harvests. SEED_SLOT in")
    print("src/gardener.py is an OPTIONAL hint; the planter auto-detects the seed slot per soil size.")


if __name__ == "__main__":
    main()

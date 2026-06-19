"""
Installer for the GardenBot Deimos add-on.

Copies gardener.py + world_to_screen.py into your Deimos `src/` folder, then tells you the one
small Deimos.py edit that binds the Ctrl+Alt+G hotkey.

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
# ---- 1) a hotkey handler (put it next to the other `async def *_hotkey()` handlers) ----
	async def garden_hotkey():
		# Ctrl+Alt+G -> run the gardener on the hooked client. Reload each press so edits apply.
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

# ---- 2) register it where the listener is set up (near the other add_hotkey calls) ----
	try:
		await listener.add_hotkey(Keycode.G, garden_hotkey,
		                          modifiers=ModifierKeys.CTRL | ModifierKeys.ALT | ModifierKeys.NOREPEAT)
		logger.debug("Garden hotkey bound: G ['CTRL', 'ALT']")
	except Exception as e:
		logger.debug(f'Failed to register garden hotkey: {e}')
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
    if "gardener" in txt and "run_diagnostic" in txt:
        print("\nDeimos.py already calls the gardener -- you're set. Restart Deimos and press Ctrl+Alt+G.")
    else:
        print("\nLast step: add the hotkey to Deimos.py (one handler + one registration), then")
        print("restart Deimos. Paste this where it fits your version (see README.md):")
        print(WIRING)
    print("Then: stand in your garden and press CTRL+ALT+G. Edit src/gardener.py SEED_SLOT for your seeds.")


if __name__ == "__main__":
    main()

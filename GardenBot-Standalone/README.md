# GardenBot (standalone) | Wizard101 garden auto-planter

Press one hotkey and it opens the gardening menu, swings the camera straight down over the
bed you're standing at, and plants every empty plot with the matching seed | fastest-first,
stopping on its own when it runs out of seeds or energy.
USE AT YOUR OWN RISK -- automation violates the Wizard101 Terms of Service.

---

## What you need

- **Windows** (the memory hooks are Windows-only)
- **Python 3.10-3.12** | get it from <https://www.python.org/downloads/> and tick
  *"Add Python to PATH"* during install
- **Wizard101**, installed and logged in

## Quick start

1. Unzip this folder anywhere.
2. Launch **Wizard101**, log in, and walk your character **into your garden, standing in the
   bed** you want to plant.
3. Double-click **`run.bat`**. The first run installs a few Python packages, then the bot hooks
   the game and waits.
4. With the game in focus, press the hotkeys:

   | Hotkey | Action |
   |---|---|
   | **Ctrl + Alt + G** | Plant the bed you're standing in |
   | **Ctrl + Alt + S** | Scan your soil -> writes `_garden_scan.txt` (use it to set up seeds) |
   | **Ctrl + Alt + K** | Quit (restores your camera) |

You can reposition to another bed and press **Ctrl + Alt + G** again. It plants one bed per
press (whatever is on screen after it frames the bed you're standing in).

## One-time setup: tell it which seed goes in which plot

Open **`gardener.py`** and edit the `SEED_SLOT` map near the top:

```python
SEED_SLOT = {
    "Large": 1,    # the seed in slot 1 of your Seeds tab goes in Large plots
    "Medium": 2,   # slot 2 goes in Medium plots
    # "Small": 3,
}
```

- The **size** keys (`Large`, `Medium`, `Small`, ...) are the soil sizes the **Ctrl+Alt+S** scan
  reports for your garden (see `_garden_scan.txt`).
- The **number** is the seed's position on the gardening **Seeds tab** (1 = first slot, 2 =
  second, ...). Put the seed you want for that plot size in that slot, in-game.
- Only sizes listed in `SEED_SLOT` are planted; others are skipped.

That's the only thing most people need to change.

## How it works (so you can trust it)

- **Opens the menu** by clicking the in-world gardening (plant) button | the `G` keybind does
  not register through injected input, so it clicks the button instead.
- **Top-down camera**: it briefly enters free-camera and points straight down over the bed, so
  tall seedlings don't hide empty soil and the on-screen aim is accurate. Your camera is
  restored when it finishes.
- **Plants farthest-first** so a freshly planted seedling never covers a plot it hasn't reached.
- **Knows when to stop**: planting costs energy; if 5
  clicks in a row spend no energy (out of seeds, out of energy, or bad camera) it aborts.
- **Cheat-Engine friendly**: every decision reads the live game state, so speeding up growth
  won't desync it.

## Troubleshooting

- **"No Wizard101 window found"** | launch and log into the game *before* running the bot.
- **"Failed to hook"** | make sure the game is fully loaded (past the loading screens), that
  you ran the bot as the **same Windows user** as the game, and that **no other bot (Deimos,
  another wizwalker tool) is already hooked** into that client. Try running `run.bat` as
  administrator.
- **Menu won't open / nothing plants** | you must be standing **in your garden**. Watch the
  console: it prints `menu state ->` and `after click ->` lines showing exactly what it found.
- **Camera ends up wrong** | press **Ctrl+Alt+K** to quit; it restores the normal camera. If it
  ever sticks, toggling Wizard101's own free-cam off, or zoning, resets it.
- **It worked before, now it doesn't after a game update** | Wizard101 patches move the memory
  signatures the hook relies on. That's a **wizwalker** update, not this bot; check the
  [wizwalker] project for a refreshed version of the bundled library.

## What's in this folder

```
plant_bot.py        the launcher (run this; or use run.bat)
gardener.py         the planter logic + SEED_SLOT config
world_to_screen.py  world->screen projection (camera math)
wizwalker/          the bundled memory-hook library (do not edit)
requirements.txt    Python dependencies
run.bat             one-click installer + launcher
```

## Credits

Built on [wizwalker] (memory framework) and the [Deimos] Wizard101 bot. This is an independent
gardening add-on; all risk and responsibility for using it is yours.

[wizwalker]: https://github.com/LaurenzLikeThat/wizwalker
[Deimos]: https://github.com/Deimos-Wizard101/Deimos-Wizard101

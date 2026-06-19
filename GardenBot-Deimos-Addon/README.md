# GardenBot // Deimos add-on

Adds a Ctrl+Alt+G garden auto-planter to an existing [Deimos] install. It reuses Deimos's
already-hooked client (no second hook, no restart of the game), opens the gardening menu, points
the camera straight down over the bed you're standing near, and plants every empty plot with the
matching seed.
USE AT YOUR OWN RISK -- automation violates the Wizard101 Terms of Service.

For people not running Deimos, use the standalone version instead (separate folder).

---

## Install

1. Copy `gardener.py` and `world_to_screen.py` into your Deimos `src/` folder. Easiest way:
   ```
   python install.py "C:\path\to\Deimos-Wizard101"
   ```
   (It backs up any files it overwrites as `.bak`. If your `world_to_screen.py` already exists
   and you've customized it, keep yours, the gardener only needs `get_camera_state` /
   `project_point` / `world_to_screen` from it.)

2. Wire the hotkey in `Deimos.py` (the installer prints this too). The only requirement is
   that something calls `gardener.run_diagnostic(client)` on a hooked client. In this Deimos
   fork that's two small additions:

   a) A handler | put it beside the other `async def *_hotkey()` functions:
   ```python
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
   ```

   b) A registration | where the `HotkeyListener` is set up, near the other `add_hotkey`
   calls:
   ```python
   try:
       await listener.add_hotkey(Keycode.G, garden_hotkey,
                                 modifiers=ModifierKeys.CTRL | ModifierKeys.ALT | ModifierKeys.NOREPEAT)
       logger.debug("Garden hotkey bound: G ['CTRL', 'ALT']")
   except Exception as e:
       logger.debug(f'Failed to register garden hotkey: {e}')
   ```

   > Adapt names to your Deimos version if needed: `get_foreground_client()` is just "the hooked
   > client you want to plant on," and `listener` is your `HotkeyListener`. `Keycode` /
   > `ModifierKeys` are already imported at the top of Deimos.py (`from wizwalker import ...`).
   > The `importlib.reload` means you can edit `src/gardener.py` and re-press the hotkey without
   > restarting Deimos.

3. Restart Deimos. On boot you should see `Garden hotkey bound: G ['CTRL', 'ALT']`.

## Use

1. Walk your character into your garden, standing next to the bed.
2. Press Ctrl + Alt + G. It opens the menu, frames the bed top-down, and plants. It plants
   one bed per press; reposition and press again for another bed.

Watch the Deimos console for `[garden]` lines, it logs the menu state, the camera framing
(`freecam H=... framed`), each plant, and a final `done/ABORTED ... energy ... spent`.

## One-time setup: map seeds to plot sizes

Edit `src/gardener.py` -> `SEED_SLOT`:
```python
SEED_SLOT = {
    "Large": 1,    # seed in slot 1 of your Seeds tab -> Large plots
    "Medium": 2,   # slot 2 -> Medium plots
}
```
The number is the seed's position on the gardening Seeds tab (1 = first slot). Only listed
sizes get planted. Not sure of your soil sizes? `gardener.garden_scan(client)` writes
`src/_garden_scan.txt` listing every plot and its size.

## Notes & troubleshooting

- It stops after ~5 clicks with "ABORT ... spent no energy" | intended: you're
  out of seeds/energy, or the camera wasn't over the bed. Restock / reposition and retry.
- Menu won't open | you must be standing in your garden. The console's `menu state ->`
  line shows whether the `OpenGardening` button was found.
- Plants land off-target without the top-down camera | expected; the bot uses a
  top-down free-camera on purpose and restores your camera afterward.
- *Breaks after a Wizard101 update | the memory signatures live in wizwalker (bundled
  with Deimos), not here. Update Deimos/wizwalker; the gardener is unaffected.

## Files

```
gardener.py         the planter (+ SEED_SLOT config) -> goes in Deimos/src/
world_to_screen.py  camera/projection math           -> goes in Deimos/src/
install.py          copies the two files into your Deimos and prints the hotkey snippet
```

[Deimos]: https://github.com/Deimos-Wizard101

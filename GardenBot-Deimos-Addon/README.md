# GardenBot // Deimos add-on

Adds a Ctrl+Alt+G garden auto-planter (and a Ctrl+Alt+H auto-harvester) to an existing [Deimos]
install. It reuses Deimos's already-hooked client (no second hook, no restart of the game), opens
the gardening menu, points the camera straight down over the bed you're standing near, and plants
every empty plot with the matching seed. Harvesting teleports to each ready plant and collects it,
looping until the bed is clear.
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

2. Wire the hotkeys in `Deimos.py` (the installer prints this too). The requirement is that
   something calls `gardener.run_diagnostic(client)` (plant) and `gardener.run_harvest(client)`
   (harvest) on a hooked client. In this Deimos fork that's two small additions:

   a) Handlers | put them beside the other `async def *_hotkey()` functions:
   ```python
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
       # Ctrl+Alt+H -> harvest every ready plant on the hooked client.
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
   ```

   b) Registrations | where the `HotkeyListener` is set up, near the other `add_hotkey` calls:
   ```python
   _gmods = ModifierKeys.CTRL | ModifierKeys.ALT | ModifierKeys.NOREPEAT
   try:
       await listener.add_hotkey(Keycode.G, garden_hotkey, modifiers=_gmods)
       await listener.add_hotkey(Keycode.H, harvest_hotkey, modifiers=_gmods)
       logger.debug("Garden hotkeys bound: G (plant) / H (harvest) ['CTRL', 'ALT']")
   except Exception as e:
       logger.debug(f'Failed to register garden hotkeys: {e}')
   ```

   > Adapt names to your Deimos version if needed: `get_foreground_client()` is just "the hooked
   > client you want," and `listener` is your `HotkeyListener`. `Keycode` / `ModifierKeys` are
   > already imported at the top of Deimos.py. `importlib.reload` lets you edit `src/gardener.py`
   > and re-press a hotkey without restarting Deimos.
   > **If your Deimos disables hotkeys when the client loses focus** (an enable/disable cycle with
   > an "always-bound" exclude list), add `garden`/`harvest` to that list too, or they'll stop
   > firing after the first tab-out.

3. Restart Deimos. On boot you should see `Garden hotkeys bound: G (plant) / H (harvest) ['CTRL', 'ALT']`.

## Use

1. Walk your character into your garden, standing next to the bed.
2. Press Ctrl + Alt + G. It opens the menu, frames the bed top-down, and plants. It plants
   one bed per press; reposition and press again for another bed.
3. Press Ctrl + Alt + H to harvest -- it teleports to every ready plant and collects, looping
   until the bed is clear (no menu or camera needed). Re-press to re-sweep.

Watch the Deimos console for `[garden]` lines, it logs the menu state, the camera framing
(`freecam H=... framed`), each plant, and a final `done/ABORTED ... energy ... spent`.

## One-time setup: which seeds to plant

Put your seeds in the gardening Seeds tab, then edit `src/gardener.py` -> `SEED_SLOT` to list the
soil sizes you want planted:
```python
SEED_SLOT = {
    "Large": 1,    # plant Large plots (number = OPTIONAL slot hint; auto-detected if wrong)
    "Medium": 1,
}
```
The number is just an optional hint -- the planter **auto-detects** the real Seeds-tab slot per
size (probing slots + watching energy), so you mainly need the seeds present. Only listed sizes
get planted. Not sure of your soil sizes? `gardener.garden_scan(client)` writes
`src/_garden_scan.txt` listing every plot and its size. (Harvest needs no setup.)

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

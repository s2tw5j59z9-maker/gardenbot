# GardenBot - Wizard101 garden auto-planter

One hotkey plants a whole garden bed: it opens the gardening menu, swings the camera straight
down over the bed you're standing in, and plants every empty plot with the matching seed -
farthest-first, and it stops on its own when it runs out of seeds or energy.

> **Use at your own risk.** Automating Wizard101 violates its Terms of Service and **can get
> your account banned.** It reads and writes the game's memory (the same technique as the
> open-source wizwalker / Deimos projects it's built on). Only run it on an account you accept
> that risk for.

## Two ways to use it

| Folder | For |
|---|---|
| [`GardenBot-Standalone/`](GardenBot-Standalone/) | Anyone - a self-contained bot (bundles wizwalker). Unzip, run `run.bat`. |
| [`GardenBot-Deimos-Addon/`](GardenBot-Deimos-Addon/) | People already running Deimos - drop-in `src/` files + one hotkey. |

Each folder has its own `README.md` with setup steps. The one thing you'll customize is
`SEED_SLOT` in `gardener.py` (which seed goes in which plot size) - the in-app **Ctrl+Alt+S**
scan lists your soil sizes to help.

## How it works

- Opens the menu by **clicking the in-world gardening button** (the `G` key doesn't register
  through injected input).
- Uses a **top-down free-camera** over the bed so standing seedlings don't hide empty soil and
  the on-screen aim stays accurate - then restores your camera.
- Plants **farthest-first** so a new seedling never covers a plot it hasn't reached yet.
- Treats an **energy drop as proof a plant took**; 5 no-cost clicks in a row -> it aborts.
- Reads only **live game state**, so speeding up growth (e.g. Cheat Engine) won't desync it.

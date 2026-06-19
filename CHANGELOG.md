# Changelog

All notable changes to GardenBot. (Wizard101 gardening automation built on wizwalker - see the
READMEs. Use at your own risk; it violates the game's Terms of Service.)

## v1.1 - 2026-06-19
### Changed
- **Dynamic seed-slot detection.** The planter now auto-detects which seed slot plants each soil
  size by probing the seed slots and watching energy (a real plant lowers it), instead of a
  hardcoded `SEED_SLOT` position map. The old map broke whenever your inventory shifted a seed to
  a different slot.
- `SEED_SLOT` is now an **optional hint** (tried first, self-corrects), not a hard requirement.
- Energy detection is now **polled** for ~2-3 seconds. A single immediate read was too soon and
  missed the drop, which made earlier versions think nothing had planted.

### Known issues
- **Untested beyond initial verification** - confirmed one successful run (auto-found Medium ->
  slot 1, planted 10/10 on-screen plots). Not yet exercised across multiple beds or seed types.
- The per-folder READMEs still describe `SEED_SLOT` as required setup; it is now optional.

## v1.0 - 2026-06-19
### Added
- Initial release: one-hotkey Wizard101 garden auto-planter, in two flavors - a self-contained
  standalone (bundles wizwalker) and a drop-in Deimos add-on.
- Opens the gardening menu by clicking the in-world OpenGardening button (the `G` key doesn't
  register via injected input).
- Drops a top-down freecam over the bed so standing seedlings don't occlude plots and clicks land
  accurately, then restores the camera.
- Plants every vacant plot farthest-first with the size-matched seed (hardcoded slot map).
- Energy-based success detection with an auto-abort when nothing is planting.

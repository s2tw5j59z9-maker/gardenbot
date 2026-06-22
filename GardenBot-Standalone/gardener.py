"""Wizard101 garden auto-planter (gardener.py).

The SAME file works two ways:
  * Standalone    -- imported by plant_bot.py, with a sibling `world_to_screen.py` bundled.
  * Deimos add-on -- dropped into Deimos/src/ and run from a Ctrl+Alt+G hotkey on Deimos's
                     already-hooked client (it then imports src.world_to_screen).

Plant model (from live entity dumps): a plot is the 'Prepared Soil - <Size>' entity; a growing
plant is a SEPARATE 'GDN_<size>_<plant>_<stage>' entity at the SAME location -- so a plot is
VACANT iff its soil has no GDN_ plant co-located with it.

How it plants (the hard-won bits):
  * Opens the menu by CLICKING the in-world 'OpenGardening' button -- the 'G' key does NOT
    register through synthetic input, and the window visible-flags are unreliable.
  * Drops a top-down freecam over the bed (update_orientation, pitch = pi/2) so plots aren't
    occluded by standing seedlings and the screen projection is accurate.
  * AUTO-DETECTS the seed slot per soil size: probes slots and watches energy (a real plant
    lowers it -- POLLED, since a single read is too soon), then plants the rest of that size.
  * Plants farthest-first; energy drop is the only success signal (the vacant count is noise).

Cheat-Engine safe: every decision reads LIVE entities / UI, never a wall-clock timer.

USE AT YOUR OWN RISK -- automation violates the Wizard101 Terms of Service.
"""
import asyncio
import os
import re
from collections import Counter

from loguru import logger
from wizwalker import Keycode

try:
    from src import world_to_screen as w2s   # type: ignore  # inside Deimos (src/ package)
except Exception:                            # noqa: BLE001
    import world_to_screen as w2s            # type: ignore  # standalone bundle (sibling module)

# soil size -> seed name. Values must match the in-game gardening-UI seed names (confirm
# against the UI dump). Extend with more sizes/seeds as needed.
SEED_FOR_SIZE = {
    "Large": "Couch Potatoes",
    "Medium": "Evil Magma Peas",
    # "Small": "Pink Dandelions",
}
# Which soil sizes to plant. The number is an OPTIONAL slot HINT (tried first); the planter now
# auto-detects the real slot per size by trying slots and watching energy, so the hint can be
# wrong/stale and it self-corrects. Add a size to have the bot plant it; remove one to ignore it.
SEED_SLOT = {
    "Large": 1,    # Couch Potatoes (hint)
    "Medium": 1,   # Evil Magma Peas (hint)
}
COLOCATE_DIST = 10.0
FAIL_ABORT = 5   # consecutive clicks that spend no energy -> abort (out of seeds/energy, or camera off-target)
_HERE = os.path.dirname(os.path.abspath(__file__))
SCAN_PATH = os.path.join(_HERE, "_garden_scan.txt")
UI_PATH = os.path.join(_HERE, "_garden_ui_tree.txt")
EXPLORE_PATH = os.path.join(_HERE, "_garden_explore.txt")

# --- harvesting ---
HARVEST_PREFIX = "HarvestEffect"  # a ready-to-harvest plant spawns a 'HarvestEffect<Size>' entity at its coords
HARVEST_ARRIVE = 0.25   # wait after teleport for the plant's harvest prompt to appear BEFORE pressing X
HARVEST_SETTLE = 0.06   # wait after each X tap for the harvest to register
HARVEST_X_TAPS = 2      # X presses per plant (the prompt can show a beat after you arrive)
HARVEST_MAX_PASSES = 6  # re-scan/retry passes; stops early when nothing remains or a pass makes no progress


def _dist(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2) ** 0.5


async def read_garden(client):
    player = await client.body.position()
    soils, plants, others = [], [], []
    for e in await client.get_base_entity_list():
        tmpl = await e.object_template()
        if tmpl is None:
            continue
        name = await tmpl.object_name()
        if not name:
            continue
        loc = await e.location()
        if name.startswith("Prepared Soil"):
            soils.append((name, name.split("-")[-1].strip(), loc, _dist(player, loc)))
        elif name.startswith("GDN_"):
            plants.append((name, loc, _dist(player, loc)))
        else:
            others.append(name)
    return soils, plants, others


def _occupied(loc, plants):
    return any(_dist(loc, pl) < COLOCATE_DIST for _, pl, _ in plants)


async def garden_scan(client):
    soils, plants, others = await read_garden(client)
    vacant = [(n, s, l, d) for n, s, l, d in soils if not _occupied(l, plants)]
    lines = [f"soil plots: {len(soils)} | growing plants: {len(plants)} | VACANT: {len(vacant)}", "",
             "vacant by size:"]
    for size, n in sorted(Counter(s for _, s, _, _ in vacant).items()):
        lines.append(f"  {size} x{n} -> would plant: {SEED_FOR_SIZE.get(size, '(unmapped!)')}")
    lines += ["", "all soil plots (V=vacant  P=planted), nearest first:"]
    for n, s, l, d in sorted(soils, key=lambda v: v[3]):
        flag = "P" if _occupied(l, plants) else "V"
        lines.append(f"  [{flag}] [{d:8.1f}] {n}  XYZ({l.x:.1f}, {l.y:.1f}, {l.z:.1f})")
    lines += ["", f"growing plants ({len(plants)}), nearest first:"]
    for n, l, d in sorted(plants, key=lambda v: v[2]):
        lines.append(f"  [{d:8.1f}] {n}  XYZ({l.x:.1f}, {l.y:.1f}, {l.z:.1f})")
    if not soils and not plants:
        lines += ["", "NO soil/GDN entities found nearby. all entity names seen:"]
        lines += [f"  {nm}" for nm in sorted(set(others))]
    with open(SCAN_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"[garden] scan -> {SCAN_PATH}  ({len(vacant)} vacant of {len(soils)} plots)")


async def garden_dump_ui(client):
    tree = await client.root_window.get_ui_tree_stringified()
    with open(UI_PATH, "w", encoding="utf-8") as f:
        f.write(tree)
    logger.info(f"[garden] UI tree -> {UI_PATH} ({tree.count(chr(10))} lines). "
                f"(Have the gardening menu OPEN when you press the hotkey.)")


async def garden_explore(client):
    """SAFE planting dry-run -- switch to the Seeds tab, hover each item slot to read its name
    (GardeningInfoText), and project the nearest vacant plots to screen. Clicks NO plots and
    plants nothing; just gathers what the real planter needs (seed->slot map + projection)."""
    root = client.root_window
    lines = []
    async with client.mouse_handler:   # managed mouseless (coexists with Deimos's own mouse use)
        if not await root.get_windows_with_name("GardeningWindow"):
            lines.append("gardening menu NOT open -- open it (Seeds tab) before pressing, for seed IDs.")
        else:
            tab = await root.get_windows_with_name("Tab_Seeds")
            if tab:
                await client.mouse_handler.click_window(tab[0])
                await asyncio.sleep(0.6)
            info = await root.get_windows_with_name("GardeningInfoText")
            info = info[0] if info else None
            lines.append("seed slots on Tab_Seeds (cursor hovered over each):")
            for i in range(1, 11):
                icons = await root.get_windows_with_name(f"Icon{i}")
                if not icons:
                    continue
                try:
                    await client.mouse_handler.set_mouse_position_to_window(icons[0])
                    await asyncio.sleep(0.35)
                    txt = (await info.maybe_text()) if info else ""
                    cw = await root.get_windows_with_name(f"ItemCount{i}")
                    cnt = (await cw[0].maybe_text()) if cw else ""
                    lines.append(f"  Icon{i}: info={txt!r} count={cnt!r}")
                except Exception as e:
                    lines.append(f"  Icon{i}: read failed ({e})")
    soils, plants, _ = await read_garden(client)
    vac = sorted([(s, l, d) for n, s, l, d in soils if not _occupied(l, plants)], key=lambda v: v[2])
    lines += ["", "nearest vacant plots projected to screen (client-relative pixels):"]
    for size, loc, d in vac[:8]:
        try:
            sc = await w2s.world_to_screen(client, loc.x, loc.y, loc.z)
        except Exception as e:
            sc = f"proj failed ({e})"
        lines.append(f"  {size} dist {d:.0f} XYZ({loc.x:.0f},{loc.y:.0f},{loc.z:.0f}) -> {sc}")
    with open(EXPLORE_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"[garden] explore -> {EXPLORE_PATH} (seed-slot names + plot projections)")


async def _read_energy(client):
    """Current energy from the gardening energy globe (textEnergy), or None if unreadable."""
    try:
        w = await client.root_window.get_windows_with_name("textEnergy")
        if not w:
            return None
        m = re.search(r"\d+", (await w[0].maybe_text()) or "")
        return int(m.group()) if m else None
    except Exception:
        return None


async def _win_state(root, name):
    """(window, visible) for a named window; window is None if not found, visible None on error."""
    w = await root.get_windows_with_name(name)
    if not w:
        return None, None
    try:
        return w[0], await w[0].is_visible()
    except Exception:
        return w[0], None


async def _menu_open(root):
    """Menu is open iff the Seeds tab (nested inside GardeningWindow) is visible -- a far more
    reliable signal than GardeningWindow itself, which lingers in the tree while hidden."""
    _, vis = await _win_state(root, "Tab_Seeds")
    return bool(vis)


async def _open_gardening(client, root):
    """Open the menu by CLICKING the in-world 'OpenGardening' HUD button (the plant icon). 'G' won't
    register via synthetic input, AND the window visible-flags are unreliable -- they stay set while
    the menu is hidden, and that false 'already open' is exactly why the click kept getting skipped
    and nothing ever planted. So we do NOT trust an is-open check: we always click. OpenGardening
    only opens (CloseGardening is a separate button), so a redundant click is harmless. Logs the
    live flag states (before + after) so a reliable open-signal can be picked if needed."""
    ob, ovis = await _win_state(root, "OpenGardening")
    cb, cvis = await _win_state(root, "CloseGardening")
    gw, gvis = await _win_state(root, "GardeningWindow")
    ts, tvis = await _win_state(root, "Tab_Seeds")
    logger.info(f"[garden] menu state -> OpenGardening(found={ob is not None},vis={ovis}) "
                f"CloseGardening(found={cb is not None},vis={cvis}) "
                f"GardeningWindow(found={gw is not None},vis={gvis}) Tab_Seeds(found={ts is not None},vis={tvis})")
    if ob is None:
        logger.warning("[garden] OpenGardening button not found -- are you standing in your garden?")
        return False
    logger.info("[garden] clicking OpenGardening button...")
    async with client.mouse_handler:   # managed mouseless (coexists with Deimos's own mouse use)
        await client.mouse_handler.click_window(ob)
    await asyncio.sleep(1.3)
    _, ovis2 = await _win_state(root, "OpenGardening")
    _, cvis2 = await _win_state(root, "CloseGardening")
    _, tvis2 = await _win_state(root, "Tab_Seeds")
    logger.info(f"[garden] after click -> OpenGardening.vis={ovis2} CloseGardening.vis={cvis2} Tab_Seeds.vis={tvis2}")
    return True   # we clicked it; planting + the energy abort are the real arbiter of success


async def _enter_topdown_freecam(client):
    """Enter freecam and place the camera straight DOWN over the nearby vacant bed, at the lowest
    height that frames it (lower = bigger plots = more accurate clicks). Anchors on the centroid of
    vacant plots within range of the player, so you pick which bed by where you stand. Rotates via
    update_orientation (writes the view matrix) -- the bare pitch offset doesn't turn the rendered
    freecam. Returns True if freecam was engaged (caller restores the camera afterward)."""
    import math
    from wizwalker import XYZ, Orient
    try:
        soils, plants, _ = await read_garden(client)
        near = [l for n, s, l, d in soils if not _occupied(l, plants) and d < 1500]
        if not near:
            logger.warning("[garden] no vacant plots within ~1500 units -- skipping freecam setup.")
            return False
        cx = sum(l.x for l in near) / len(near)
        cy = sum(l.y for l in near) / len(near)
        cz = max(l.z for l in near)
        if not await client.game_client.is_freecam():
            await client.camera_freecam()
            await asyncio.sleep(0.4)
        cam_ctrl = await client.game_client.free_camera_controller()
        # Straight down: calculate_pitch(above, below) == pi/2. Apply through the VIEW MATRIX
        # (update_orientation), not the bare pitch offset, which doesn't rotate the rendered freecam.
        down = Orient(math.pi / 2, 0.0, 0.0)
        await cam_ctrl.update_orientation(down)
        best_h, best_on = None, -1
        for H in (600, 900, 1300, 1800, 2500, 3400):
            await cam_ctrl.write_position(XYZ(cx, cy, cz + H))
            await cam_ctrl.update_orientation(down)
            await asyncio.sleep(0.15)
            cam = await w2s.get_camera_state(client)
            if not cam:
                continue
            mx, my = cam['client_w'] * 0.12, cam['client_h'] * 0.12   # 12% margin -> zoom out enough for breathing room
            on = 0
            for l in near:
                sc = w2s.project_point(cam, l.x, l.y, l.z)
                if sc and mx <= sc[0] <= cam['client_w'] - mx and my <= sc[1] <= cam['client_h'] - my:
                    on += 1
            logger.info(f"[garden] freecam H={H}: {on}/{len(near)} nearby plots framed (12% margin)")
            if on > best_on:
                best_on, best_h = on, H
            if on >= 0.95 * len(near):
                break   # smallest height that frames ~the whole bed -> best click precision
        await cam_ctrl.write_position(XYZ(cx, cy, cz + best_h))
        await cam_ctrl.update_orientation(down)
        await asyncio.sleep(0.2)
        logger.info(f"[garden] freecam top-down over ({cx:.0f},{cy:.0f}) H={best_h} "
                    f"({best_on}/{len(near)} framed)")
        return True
    except Exception as e:
        logger.warning(f"[garden] freecam setup failed ({e}); planting from the current camera.")
        return False


async def _exit_freecam(client):
    """Restore the normal (elastic) camera after planting."""
    try:
        if await client.game_client.is_freecam():
            await client.camera_elastic()
    except Exception as e:
        logger.warning(f"[garden] camera restore failed ({e}).")


async def _plant_at(client, root, slot, sc, prev_e):
    """Select seed Icon{slot}, click the plot at screen sc, then POLL energy for a couple seconds
    to catch the drop. Planting lowers energy; a wrong-size/empty-seed click doesn't -- so an
    energy DROP means that slot's seed fits this plot. (A single immediate read misses the drop;
    that was the earlier bug -- hence the poll.) Returns (planted_bool, latest_energy). Mouseless
    must be active."""
    icon = await root.get_windows_with_name(f"Icon{slot}")
    if not icon:
        return False, prev_e
    await client.mouse_handler.click_window(icon[0])
    await asyncio.sleep(0.25)
    await client.mouse_handler.click(sc[0], sc[1])
    last = prev_e
    for _ in range(6):                       # poll up to ~2.4s for the energy drop to register
        await asyncio.sleep(0.4)
        cur_e = await _read_energy(client)
        if cur_e is not None:
            last = cur_e
            if prev_e is not None and cur_e < prev_e:
                return True, cur_e
    return False, last


async def garden_plant(client, limit=None):
    """One press: foreground the client, open the gardening menu (G), drop into a top-down freecam
    over the nearby bed, then plant every framed vacant plot FARTHEST-FIRST (so new seedlings never
    occlude unplanted soil), auto-learning which seed slot plants each soil size. Stops after FAIL_ABORT
    no-energy clicks in a row, then restores the camera. CE-safe: live state + window-msg clicks."""
    import ctypes
    import ctypes.wintypes
    root = client.root_window

    if not await _open_gardening(client, root):
        logger.warning("[garden] could not open gardening menu -- aborting (are you in your garden?).")
        return

    # Top-down freecam over the bed: no occlusion + accurate projection (the method you verified).
    freecam_set = await _enter_topdown_freecam(client)
    if not await _menu_open(root):
        logger.info("[garden] menu not open after freecam -- reopening.")
        await _open_gardening(client, root)

    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetClientRect(client.window_handle, ctypes.byref(rect))
    cw, ch = rect.right, rect.bottom

    soils, plants, _ = await read_garden(client)
    vac1 = sum(1 for n, s, l, d in soils if not _occupied(l, plants))
    # Project all vacant mapped plots once (camera is static -- player isn't moving), keep the
    # on-screen ones, and sort by screen-Y ascending = farthest first (a seedling only occludes
    # plots behind/above it, so planting top-down means new seedlings never block unplanted soil).
    cam = await w2s.get_camera_state(client)
    targets, offscreen = [], 0
    for n, s, l, d in soils:
        if _occupied(l, plants) or SEED_SLOT.get(s) is None:
            continue
        sc = w2s.project_point(cam, l.x, l.y, l.z) if cam else None
        if sc is None or not (0 <= sc[0] <= cw and 0 <= sc[1] <= ch):
            offscreen += 1
            continue
        targets.append((s, l, sc))
    targets.sort(key=lambda t: t[2][1])   # top of screen (farthest) first
    e0 = await _read_energy(client)
    logger.info(f"[garden] {len(targets)} plantable on-screen ({offscreen} off-screen); "
                f"energy {e0}; limit {limit or 'ALL'}")
    planted, fails, aborted = 0, 0, False
    learned = {}   # soil size -> the Icon slot that actually plants it (auto-detected via energy)
    cur_e = e0
    async with client.mouse_handler:   # managed mouseless (coexists with Deimos's own mouse use)
        tab = await root.get_windows_with_name("Tab_Seeds")   # Seeds = 2nd tab, bottom-left of the gardening UI
        if tab:
            await client.mouse_handler.click_window(tab[0])
            await asyncio.sleep(0.5)
        slots = [i for i in range(1, 11) if await root.get_windows_with_name(f"Icon{i}")]
        for size, loc, sc in targets:
            if limit is not None and planted >= limit:
                break
            xyz = f"XYZ({loc.x:.0f},{loc.y:.0f},{loc.z:.0f})"
            if size in learned:
                slot = learned[size]
                if slot is None:
                    continue   # already probed -- nothing in the menu plants this size
                took, cur_e = await _plant_at(client, root, slot, sc, cur_e)
                if took:
                    planted += 1
                    fails = 0
                    logger.info(f"[garden] planted {size} #{planted} (slot {slot}) {xyz} | energy {cur_e}")
                else:
                    fails += 1   # the learned slot stopped planting -> out of that seed (or off-target)
                    logger.info(f"[garden] {size} slot {slot} no plant {xyz} | energy {cur_e} | fail-streak {fails}")
                    if fails >= FAIL_ABORT:
                        aborted = True
                        logger.warning(f"[garden] ABORT: {FAIL_ABORT} no-plant clicks in a row "
                                       f"(out of seeds/energy, or camera off-target). Stopping.")
                        break
            else:
                # First plot of this size: probe slots (hint first) until energy drops = it planted.
                order = list(slots)
                hint = SEED_SLOT.get(size)
                if hint in order:
                    order.remove(hint)
                    order.insert(0, hint)
                hit = None
                for slot in order:
                    took, cur_e = await _plant_at(client, root, slot, sc, cur_e)
                    if took:
                        hit = slot
                        break
                learned[size] = hit
                if hit is not None:
                    planted += 1
                    fails = 0
                    logger.info(f"[garden] learned {size} -> slot {hit}; planted #{planted} {xyz} | energy {cur_e}")
                else:
                    logger.warning(f"[garden] no slot plants {size} (tried {order}); skipping {size} plots.")
    e1 = await _read_energy(client)
    spent = (e0 - e1) if (e0 is not None and e1 is not None) else None
    logger.info(f"[garden] {'ABORTED' if aborted else 'done'}: planted {planted} ({offscreen} off-screen); "
                f"energy {e0} -> {e1}"
                + (f" ({spent} spent)" if spent is not None else "")
                + f"; detected slots {learned}")
    if freecam_set:
        await _exit_freecam(client)


async def run_diagnostic(client):
    # Hotkey entry point (Deimos.py calls this name). Runs the full auto-planter.
    logger.info("[garden] hotkey fired -- starting auto-planter.")
    try:
        await garden_plant(client)
    except Exception as e:
        import traceback
        logger.error(f"[garden] plant run failed: {e}\n{traceback.format_exc()}")


async def read_harvestables(client):
    """Ready-to-harvest plants: each spawns a 'HarvestEffect<Size>' entity at the plant's coords
    (e.g. HarvestEffectLg). Returns [(name, loc, dist)] nearest-first."""
    player = await client.body.position()
    out = []
    for e in await client.get_base_entity_list():
        tmpl = await e.object_template()
        if tmpl is None:
            continue
        name = await tmpl.object_name()
        if name and name.startswith(HARVEST_PREFIX):
            loc = await e.location()
            out.append((name, loc, _dist(player, loc)))
    out.sort(key=lambda v: v[2])
    return out


def _tap_key(client, vk):
    """Tap a virtual-key via PostMessageW to the game window -- the method proven to register world
    input (a plain key send does NOT register through synthetic input). WM_KEYDOWN/UP = 0x100/0x101."""
    import ctypes
    u = ctypes.windll.user32
    u.PostMessageW(client.window_handle, 0x0100, vk, 0)
    u.PostMessageW(client.window_handle, 0x0101, vk, 0)


async def garden_harvest(client, arrive=HARVEST_ARRIVE, settle=HARVEST_SETTLE,
                         x_taps=HARVEST_X_TAPS, max_passes=HARVEST_MAX_PASSES):
    """Harvest every ready plant: teleport onto each HarvestEffect marker, wait briefly for the
    plant's harvest prompt to appear, then tap X (proximity harvest). No freecam / clicks / energy.
    LOOPS, re-scanning each pass and retrying what's left, until no markers remain OR a pass makes
    no progress (so it self-confirms instead of pressing X into the void). CE-safe: live entities
    each pass; returns to the start position when done. Speed vs reliability lives in
    arrive/settle/x_taps -- the X-interact needs the prompt rendered, so it trades raw speed for
    completeness (a true few-seconds sweep would need the game's memory/protocol harvest message)."""
    from wizwalker import XYZ
    VK_X = 0x58
    start = await client.body.position()
    swept = 0
    prev_remaining = None
    for p in range(max_passes):
        ready = await read_harvestables(client)
        if not ready:
            logger.info("[garden] nothing ready to harvest (no HarvestEffect markers)." if p == 0
                        else f"[garden] all harvested after {p} pass(es).")
            break
        logger.info(f"[garden] harvest pass {p + 1}: {len(ready)} ready plant(s).")
        for name, loc, d in ready:
            try:
                await client.teleport(XYZ(loc.x, loc.y, loc.z), wait_on_inuse=True,
                                      wait_on_inuse_timeout=0.5, purge_on_after_unuser_fixer=False)
                await asyncio.sleep(arrive)          # let the harvest prompt render before pressing X
                for _ in range(x_taps):
                    _tap_key(client, VK_X)
                    await asyncio.sleep(settle)
                swept += 1
            except Exception as e:
                logger.warning(f"[garden] harvest at XYZ({loc.x:.0f},{loc.y:.0f},{loc.z:.0f}) failed: {e}")
        remaining = len(await read_harvestables(client))
        logger.info(f"[garden] pass {p + 1} done: {remaining} marker(s) remain.")
        if remaining == 0:
            break
        if prev_remaining is not None and remaining >= prev_remaining:
            logger.warning(f"[garden] no progress this pass ({remaining} remain) -- stopping.")
            break
        prev_remaining = remaining
    try:
        await client.teleport(start, wait_on_inuse=False, purge_on_after_unuser_fixer=False)
    except Exception:
        pass
    logger.info(f"[garden] harvest done: {swept} TP+X attempt(s) over up to {max_passes} passes.")


async def run_harvest(client):
    # Hotkey entry point (plant_bot.py / a Deimos harvest hotkey calls this). Harvest all ready plants.
    logger.info("[garden] harvest hotkey fired -- harvesting ready plants.")
    try:
        await garden_harvest(client)
    except Exception as e:
        import traceback
        logger.error(f"[garden] harvest run failed: {e}\n{traceback.format_exc()}")

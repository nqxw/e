# cogs/spoofer.py | Platform spoofer — class-level send_json patch (discord.py-self)
#
# HOW IT WORKS (mirrors the original modifyself approach):
#   discord.py-self uses DiscordWebSocket.send_json() for every gateway message.
#   OP 2 = IDENTIFY.  We patch send_json AT THE CLASS LEVEL so even new WebSocket
#   instances (created on reconnect) use our version.  When an OP2 payload passes
#   through, we rewrite the 'properties' block before it hits the wire.
#   Code 4000 on close forces a full reconnect + new IDENTIFY (not RESUME), so
#   the patched IDENTIFY fires with our properties.
#
import asyncio
import base64
import json
import random
import time
import traceback
import discord
from discord.ext import commands
from . import state as S

# ── Platform presets ──────────────────────────────────────────────────────────
PLATFORM_PRESETS = {
    "desktop":     {"os": "Windows",  "browser": "Chrome",          "device": "",            "label": "Windows Desktop"},
    "windows":     {"os": "Windows",  "browser": "Chrome",          "device": "",            "label": "Windows Desktop"},
    "macos":       {"os": "Mac OS X", "browser": "Chrome",          "device": "",            "label": "macOS Desktop"},
    "linux":       {"os": "Linux",    "browser": "Chrome",          "device": "",            "label": "Linux Desktop"},
    "web":         {"os": "Windows",  "browser": "Chrome",          "device": "",            "label": "Web Browser"},
    "phone":       {"os": "Android",  "browser": "Discord Android", "device": "Android",     "label": "Android Phone"},
    "mobile":      {"os": "Android",  "browser": "Discord Android", "device": "Android",     "label": "Android Phone"},
    "android":     {"os": "Android",  "browser": "Discord Android", "device": "Android",     "label": "Android"},
    "ios":         {"os": "iOS",      "browser": "Discord iOS",     "device": "iPhone",      "label": "iPhone"},
    "iphone":      {"os": "iOS",      "browser": "Discord iOS",     "device": "iPhone",      "label": "iPhone"},
    "ipad":        {"os": "iOS",      "browser": "Discord iOS",     "device": "iPad",        "label": "iPad"},
    "console":     {"os": "Windows",  "browser": "Chrome",          "device": "console",     "label": "Console"},
    "xbox":        {"os": "Windows",  "browser": "Chrome",          "device": "xbox",        "label": "Xbox"},
    "playstation": {"os": "Windows",  "browser": "Chrome",          "device": "playstation", "label": "PlayStation"},
    "ps":          {"os": "Windows",  "browser": "Chrome",          "device": "playstation", "label": "PlayStation"},
    "vr":          {"os": "Android",  "browser": "Discord VR",      "device": "Quest",       "label": "VR Headset"},
    "quest":       {"os": "Android",  "browser": "Discord VR",      "device": "Quest 3",     "label": "Meta Quest 3"},
    "quest2":      {"os": "Android",  "browser": "Discord VR",      "device": "Quest 2",     "label": "Meta Quest 2"},
    "embedded":    {"os": "Windows",  "browser": "Chrome",          "device": "",            "label": "Embedded"},
}

# Correct user-agents per (os, browser) pair
UA_MAP = {
    ("Android",  "Discord Android"): "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    ("Android",  "Discord VR"):      "Mozilla/5.0 (Linux; Android 12; Quest 3) AppleWebKit/537.36 (KHTML, like Gecko) OculusBrowser/37.0.0.0.43 SamsungBrowser/4.0 Chrome/122.0.6261.140 VR Safari/537.36",
    ("iOS",      "Discord iOS"):     "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    ("Windows",  "Chrome"):          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    ("Mac OS X", "Chrome"):          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    ("Linux",    "Chrome"):          "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
}

# ── Module-level patch state (survives cog reloads) ───────────────────────────
_POOL = {
    "mode":   "sticky",   # sticky | rotate | random
    "keys":   ["desktop"],
    "pool":   [PLATFORM_PRESETS["desktop"]],
    "cursor": 0,
    "last":   None,
}
_PATCH_INFO  = {"installed": False, "path": None, "orig": None}
_STATS       = {"identifies": 0, "reconnects": 0}
_COG_REF     = [None]   # live SpooferCog instance for callbacks


def _pick() -> dict | None:
    pool = _POOL["pool"]
    if not pool: return None
    if _POOL["mode"] == "sticky": return pool[0]
    if _POOL["mode"] == "random": return random.choice(pool)
    idx = _POOL["cursor"] % len(pool)
    _POOL["cursor"] = idx + 1
    return pool[idx]


def _set_pool(keys: list):
    _POOL["keys"] = [k for k in keys if k in PLATFORM_PRESETS]
    _POOL["pool"] = [PLATFORM_PRESETS[k] for k in _POOL["keys"]]
    _POOL["cursor"] = 0


# ── Class-level patch (the real mechanism) ────────────────────────────────────
def _find_ws_class(bot=None):
    """Return discord.py-self's DiscordWebSocket class, or None."""
    # Primary: standard discord.py-self location
    try:
        import discord.gateway as gw
        cls = getattr(gw, "DiscordWebSocket", None)
        if cls and hasattr(cls, "send_json"):
            return cls, "discord.gateway.DiscordWebSocket"
    except Exception:
        pass
    # Fallback: crawl bot's ws object
    for bot_ref in ([bot] if bot else []):
        ws = getattr(bot_ref, "ws", None)
        if ws and hasattr(ws, "send_json"):
            return type(ws), f"{type(ws).__module__}.{type(ws).__name__}"
    return None, None


def _install_patch(bot=None):
    """
    Patch send_json on the gateway WebSocket CLASS.
    Every send_json call — on any instance, including new ones after reconnect —
    passes through our interceptor, which rewrites OP2 properties.
    """
    if _PATCH_INFO["installed"]:
        return True

    cls, path = _find_ws_class(bot)
    if cls is None:
        print("[spoofer] cannot find gateway class — patch NOT installed")
        return False

    orig = cls.send_json
    _PATCH_INFO["orig"] = orig
    _PATCH_INFO["path"] = path

    async def _patched_send_json(self_ws, data):
        try:
            if isinstance(data, dict) and data.get("op") == 2:
                preset = _pick()
                if preset:
                    d = data.setdefault("d", {})
                    props = d.setdefault("properties", {})
                    props["os"]      = preset["os"]
                    props["browser"] = preset["browser"]
                    props["device"]  = preset.get("device", "")
                    ua = UA_MAP.get((preset["os"], preset["browser"]))
                    if ua:
                        props["browser_user_agent"] = ua
                    _POOL["last"] = preset
                    _STATS["identifies"] += 1
                    cog = _COG_REF[0]
                    if cog:
                        cog._last_props = dict(props)
                    print(f"[spoofer] IDENTIFY rewritten → {preset['label']} "
                          f"(os={preset['os']} browser={preset['browser']} "
                          f"device={preset.get('device','') or 'none'})")
        except Exception as e:
            print(f"[spoofer] patch rewrite error: {e}")
        return await orig(self_ws, data)

    cls.send_json = _patched_send_json
    cls._spoofer_patched = True
    _PATCH_INFO["installed"] = True
    print(f"[spoofer] class patch installed → {path}.send_json")
    return True


def _remove_patch():
    """Restore original send_json (called on cog unload if desired)."""
    if not _PATCH_INFO["installed"] or not _PATCH_INFO["orig"]:
        return
    try:
        cls, _ = _find_ws_class()
        if cls:
            cls.send_json = _PATCH_INFO["orig"]
            cls._spoofer_patched = False
    except Exception:
        pass
    _PATCH_INFO["installed"] = False
    _PATCH_INFO["orig"] = None


# ── Cog ───────────────────────────────────────────────────────────────────────
class SpooferCog(commands.Cog, name="spoofer"):
    """Platform spoofer — patches gateway send_json at class level."""

    def __init__(self, bot):
        self.bot         = bot
        self._last_props = None
        _COG_REF[0]      = self
        # Install the patch immediately (bot is already connected)
        ok = _install_patch(bot)
        if not ok:
            # Gateway class not importable yet; will retry on_ready/on_connect
            print("[spoofer] will retry patch install on connect")

    async def cog_load(self):
        # If not patched yet (import failed at __init__), try again
        if not _PATCH_INFO["installed"]:
            _install_patch(self.bot)

    # Re-apply on every (re)connect — guarantees the patch is on the new ws class
    @commands.Cog.listener()
    async def on_connect(self):
        if not _PATCH_INFO["installed"]:
            _install_patch(self.bot)

    @commands.Cog.listener()
    async def on_ready(self):
        if not _PATCH_INFO["installed"]:
            _install_patch(self.bot)

    async def _reconnect(self):
        """Close with code 4000 → full reconnect, new IDENTIFY (not RESUME)."""
        _STATS["reconnects"] += 1
        ws = getattr(self.bot, "ws", None)
        if ws and hasattr(ws, "close"):
            try:
                await ws.close(code=4000)
                return
            except Exception as e:
                print(f"[spoofer] ws.close(4000): {e}")
        # Fallback: close with 1000
        if ws and hasattr(ws, "close"):
            try: await ws.close(code=1000)
            except Exception: pass

    # ── Commands ──────────────────────────────────────────────────────────────

    @commands.command(name="spoof", aliases=["spoofer"], brief="Spoof platform — spoof <preset>")
    async def spoof(self, ctx, platform: str = "", sub: str = "", *, rest: str = ""):
        if not platform or platform in ("status", "info"):
            return await self._show_status(ctx)

        p = platform.lower()

        if p == "add" and sub:
            sub = sub.lower()
            if sub not in PLATFORM_PRESETS:
                return await ctx.message.edit(content=S.ui_err(f"unknown: {sub}"))
            if sub not in _POOL["keys"]:
                _POOL["keys"].append(sub)
                _POOL["pool"].append(PLATFORM_PRESETS[sub])
            return await ctx.message.edit(
                content=S.ui_ok(f"added {sub} to pool ({len(_POOL['keys'])} total)"))

        if p == "remove" and sub:
            sub = sub.lower()
            if sub in _POOL["keys"]:
                i = _POOL["keys"].index(sub)
                _POOL["keys"].pop(i)
                _POOL["pool"].pop(i)
            return await ctx.message.edit(content=S.ui_ok(f"removed {sub}"))

        if p == "mode" and sub in ("rotate", "random", "sticky"):
            _POOL["mode"] = sub; _POOL["cursor"] = 0
            return await ctx.message.edit(content=S.ui_ok(f"mode → {sub}"))

        if p == "clear":
            _set_pool([])
            return await ctx.message.edit(content=S.ui_ok("pool cleared — no spoofing"))

        if p == "reset":
            _set_pool(["desktop"]); _POOL["mode"] = "sticky"
            await ctx.message.edit(content=S.ui_ok("reset → Desktop"))
            await self._reconnect()
            return

        if p == "pool":
            rows = []
            for i, k in enumerate(_POOL["keys"]):
                marker = "→ " if (_POOL["mode"] == "rotate"
                                  and i == _POOL["cursor"] % max(len(_POOL["keys"]),1)) else "  "
                rows.append(f"  {S.DIM}{marker}{S.RESET}{k:<12} {PLATFORM_PRESETS[k]['label']}")
            rows += [
                "",
                f"  {S.DIM}mode  {S.RESET}{_POOL['mode']}  "
                f"cursor {_POOL['cursor']}  size {len(_POOL['keys'])}",
            ]
            return await ctx.message.edit(content=S.ui_box("spoof pool", rows))

        if p not in PLATFORM_PRESETS:
            return await ctx.message.edit(
                content=S.ui_err(f"unknown preset: {p}  |  valid: {', '.join(PLATFORM_PRESETS)}"))

        _set_pool([p]); _POOL["mode"] = "sticky"
        preset = PLATFORM_PRESETS[p]
        await ctx.message.edit(content=S.ui_ok(
            f"spoofing → {preset['label']}  (reconnecting…)"))
        await self._reconnect()
        # Brief wait then confirm
        await asyncio.sleep(4)
        last = _POOL["last"]
        if last:
            await ctx.channel.send(S.ui_ok(
                f"✓  IDENTIFY sent as {last['label']}  "
                f"(os={last['os']} / browser={last['browser']} / "
                f"device={last.get('device','') or 'none'})"))
        else:
            await ctx.channel.send(S.ui_warn("reconnected but IDENTIFY not fired yet"))

    @commands.command(name="vr", brief="Spoof VR headset (Meta Quest)")
    async def vr(self, ctx):
        _set_pool(["vr"]); _POOL["mode"] = "sticky"
        await ctx.message.edit(content=S.ui_ok("spoofing → VR Headset  (reconnecting…)"))
        await self._reconnect()

    @commands.command(name="console", brief="Spoof console platform")
    async def console(self, ctx):
        _set_pool(["console"]); _POOL["mode"] = "sticky"
        await ctx.message.edit(content=S.ui_ok("spoofing → Console  (reconnecting…)"))
        await self._reconnect()

    @commands.command(name="spoofreset", brief="Reset spoofer to desktop")
    async def spoofreset(self, ctx):
        _set_pool(["desktop"]); _POOL["mode"] = "sticky"
        await ctx.message.edit(content=S.ui_ok("reset → Desktop  (reconnecting…)"))
        await self._reconnect()

    @commands.command(name="platform", brief="Alias: platform <preset>")
    async def platform_cmd(self, ctx, *, preset: str = ""):
        key = preset.strip().lower().split()[0] if preset.strip() else ""
        if not key:
            rows = [f"  {S.CYAN}{k:<12}{S.RESET} {v['label']}"
                    for k, v in PLATFORM_PRESETS.items()]
            return await ctx.message.edit(content=S.ui_box("platforms", rows))
        await self.spoof(ctx, key)

    @commands.command(name="spoofstatus", brief="Show current spoof status")
    async def spoofstatus(self, ctx):
        await self._show_status(ctx)

    @commands.command(name="spooferdiag", brief="Full spoofer diagnostics")
    async def spooferdiag(self, ctx):
        cls, path = _find_ws_class(self.bot)
        patched   = bool(getattr(cls, "_spoofer_patched", False)) if cls else False
        p         = self._last_props or {}
        ws        = getattr(self.bot, "ws", None)
        rows = [
            f"  {S.DIM}patch installed{S.RESET}  {'YES ✓' if _PATCH_INFO['installed'] else 'NO ✗'}",
            f"  {S.DIM}class found{S.RESET}     {path or 'NOT FOUND'}",
            f"  {S.DIM}class patched{S.RESET}   {'YES ✓' if patched else 'NO ✗'}",
            f"  {S.DIM}ws type{S.RESET}         {type(ws).__name__ if ws else 'None'}",
            "",
            f"  {S.DIM}pool mode{S.RESET}  {_POOL['mode']}",
            f"  {S.DIM}pool keys{S.RESET}  {', '.join(_POOL['keys']) or '—'}",
            f"  {S.DIM}last pick{S.RESET}  {_POOL['last']['label'] if _POOL['last'] else '—'}",
            "",
            f"  {S.DIM}last os{S.RESET}      {p.get('os','—')}",
            f"  {S.DIM}last browser{S.RESET} {p.get('browser','—')}",
            f"  {S.DIM}last device{S.RESET}  {p.get('device','—') or 'none'}",
            "",
            f"  {S.DIM}identifies{S.RESET}   {_STATS['identifies']}",
            f"  {S.DIM}reconnects{S.RESET}   {_STATS['reconnects']}",
        ]
        await ctx.message.edit(content=S.ui_box("spoofer diag", rows))

    async def _show_status(self, ctx):
        preset = _POOL["last"] or {}
        p      = self._last_props or {}
        rows = [
            f"  {S.DIM}preset{S.RESET}    {preset.get('label','—')}",
            f"  {S.DIM}pool{S.RESET}      {', '.join(_POOL['keys']) or '—'}",
            f"  {S.DIM}mode{S.RESET}      {_POOL['mode']}",
            "",
            f"  {S.DIM}os{S.RESET}        {p.get('os', preset.get('os','?'))}",
            f"  {S.DIM}browser{S.RESET}   {p.get('browser', preset.get('browser','?'))}",
            f"  {S.DIM}device{S.RESET}    {p.get('device', preset.get('device','?')) or 'none'}",
            "",
            f"  {S.DIM}identifies{S.RESET} {_STATS['identifies']}",
            f"  {S.DIM}reconnects{S.RESET} {_STATS['reconnects']}",
            f"  {S.DIM}patched{S.RESET}    {'yes ✓' if _PATCH_INFO['installed'] else 'NO ✗  — run spoof <preset> to activate'}",
            "",
            f"  {S.DIM}valid: {', '.join(PLATFORM_PRESETS)}{S.RESET}",
        ]
        await ctx.message.edit(content=S.ui_box("spoofer", rows))


async def setup(bot):
    await bot.add_cog(SpooferCog(bot))

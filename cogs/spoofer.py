# cogs/spoofer.py — Platform spoofer for discord.py-self
#
# Strategy (three layers):
#   1. http attribute patch  — sets .browser / .device / .os on the HTTPClient so
#      the library's own identify() picks them up on every reconnect.
#   2. class-level send patch — intercepts OP2 on send_json AND send_as_json so
#      any identify payload is rewritten before it leaves the process.
#   3. instance identify patch — hooks the new ws.identify() directly in
#      on_connect, which fires *before* the identify is sent.
#
import asyncio, base64, json, random, time
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

UA_MAP = {
    ("Android",  "Discord Android"): "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    ("Android",  "Discord VR"):      "Mozilla/5.0 (Linux; Android 12; Quest 3) AppleWebKit/537.36 (KHTML, like Gecko) OculusBrowser/37.0.0.0.43 Chrome/122.0.6261.140 VR Safari/537.36",
    ("iOS",      "Discord iOS"):     "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    ("Windows",  "Chrome"):          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    ("Mac OS X", "Chrome"):          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    ("Linux",    "Chrome"):          "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
}

# ── Module-level state ────────────────────────────────────────────────────────
_POOL   = {"mode": "sticky", "keys": ["desktop"],
           "pool": [PLATFORM_PRESETS["desktop"]], "cursor": 0, "last": None}
_PATCH  = {"json": False, "as_json": False, "orig_json": None, "orig_as_json": None, "path": None}
_STATS  = {"identifies": 0, "reconnects": 0}
_COG    = [None]   # live cog reference


def _pick() -> dict | None:
    pool = _POOL["pool"]
    if not pool: return None
    if _POOL["mode"] == "sticky": return pool[0]
    if _POOL["mode"] == "random": return random.choice(pool)
    idx = _POOL["cursor"] % len(pool); _POOL["cursor"] = idx + 1
    return pool[idx]


def _set_pool(keys: list):
    _POOL["keys"] = [k for k in keys if k in PLATFORM_PRESETS]
    _POOL["pool"] = [PLATFORM_PRESETS[k] for k in _POOL["keys"]]
    _POOL["cursor"] = 0


def _make_identify_payload(preset: dict, token: str) -> dict:
    return {
        "op": 2,
        "d": {
            "token":        token,
            "capabilities": 16381,
            "properties": {
                "os":                        preset["os"],
                "browser":                   preset["browser"],
                "device":                    preset.get("device", ""),
                "system_locale":             "en-US",
                "browser_user_agent":        UA_MAP.get((preset["os"], preset["browser"]),
                                              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/132.0.0.0 Safari/537.36"),
                "browser_version":           "132.0.0.0",
                "os_version":                "",
                "referrer":                  "",
                "referring_domain":          "",
                "referrer_current":          "",
                "referring_domain_current":  "",
                "release_channel":           "stable",
                "client_build_number":       999999,
                "client_event_source":       None,
            },
            "compress": False,
            "client_state": {
                "guild_versions":              {},
                "highest_last_message_id":     "0",
                "read_state_version":          0,
                "user_guild_settings_version": -1,
                "user_settings_version":       -1,
                "private_channels_version":    "0",
                "api_code_version":            0,
            },
            "presence": {"status": "online", "since": 0, "activities": [], "afk": False},
        }
    }


# ── Layer 2: class-level send_json / send_as_json patch ───────────────────────
def _find_ws_class(bot=None):
    try:
        import discord.gateway as gw
        cls = getattr(gw, "DiscordWebSocket", None)
        if cls: return cls, "discord.gateway.DiscordWebSocket"
    except Exception:
        pass
    ws = getattr(bot, "ws", None) if bot else None
    if ws: return type(ws), f"{type(ws).__module__}.{type(ws).__name__}"
    return None, None


def _install_class_patch(bot=None):
    cls, path = _find_ws_class(bot)
    if not cls:
        print("[spoofer] class not found — class patch skipped")
        return

    _PATCH["path"] = path

    def _make_interceptor(orig, method_name):
        async def interceptor(self_ws, data):
            try:
                if isinstance(data, dict) and data.get("op") == 2:
                    preset = _pick()
                    if preset:
                        d     = data.setdefault("d", {})
                        props = d.setdefault("properties", {})
                        props["os"]                 = preset["os"]
                        props["browser"]            = preset["browser"]
                        props["device"]             = preset.get("device", "")
                        ua = UA_MAP.get((preset["os"], preset["browser"]))
                        if ua: props["browser_user_agent"] = ua
                        _POOL["last"] = preset
                        _STATS["identifies"] += 1
                        cog = _COG[0]
                        if cog: cog._last_props = dict(props)
                        print(f"[spoofer] {method_name} OP2 → {preset['label']}")
            except Exception as e:
                print(f"[spoofer] {method_name} intercept error: {e}")
            return await orig(self_ws, data)
        return interceptor

    for method in ("send_json", "send_as_json"):
        orig = getattr(cls, method, None)
        if orig and not getattr(cls, f"_spoofer_patched_{method}", False):
            setattr(cls, method, _make_interceptor(orig, method))
            setattr(cls, f"_spoofer_patched_{method}", True)
            _PATCH[method.replace("send_", "")] = True
            print(f"[spoofer] patched {path}.{method}")


# ── Layer 1: http attribute patch (persists across reconnects) ────────────────
def _patch_http(bot, preset: dict):
    for attr_path in ("http", "_connection.http"):
        try:
            obj = bot
            for part in attr_path.split("."):
                obj = getattr(obj, part, None)
                if obj is None: break
            if obj is None: continue
            for attr, key in [("browser", "browser"), ("device", "device"),
                               ("os", "os"), ("user_agent", None)]:
                if hasattr(obj, attr):
                    if key:
                        setattr(obj, attr, preset.get(key, ""))
                    elif attr == "user_agent":
                        ua = UA_MAP.get((preset["os"], preset["browser"]))
                        if ua: setattr(obj, attr, ua)
            print(f"[spoofer] http patch applied via {attr_path}")
            return True
        except Exception as e:
            print(f"[spoofer] http patch ({attr_path}): {e}")
    return False


# ── Cog ───────────────────────────────────────────────────────────────────────
class SpooferCog(commands.Cog, name="spoofer"):
    def __init__(self, bot):
        self.bot         = bot
        self._last_props = None
        _COG[0] = self
        _install_class_patch(bot)

    async def cog_load(self):
        if not (_PATCH.get("json") or _PATCH.get("as_json")):
            _install_class_patch(self.bot)

    # ── Layer 3: instance identify patch ──────────────────────────────────────
    @commands.Cog.listener()
    async def on_connect(self):
        """
        Fires AFTER the new WebSocket connects but BEFORE identify is sent.
        Patch ws.identify on the new instance directly so even if the class
        patch missed, this instance will send our custom properties.
        """
        if not _POOL["pool"]: return
        # Also retry class patch in case class wasn't importable at __init__
        _install_class_patch(self.bot)

        ws = getattr(self.bot, "ws", None)
        if not ws: return
        preset = _pick()
        if not preset: return

        # Patch http attributes (layer 1)
        _patch_http(self.bot, preset)

        # Patch this instance's identify method (layer 3)
        for method_name in ("identify", "_identify"):
            orig = getattr(ws, method_name, None)
            if orig and not getattr(ws, f"_spoof_patched_{method_name}", False):
                token   = S.TOKEN
                _preset = dict(preset)

                async def _patched(p=_preset, t=token, ws_ref=ws):
                    try:
                        payload = _make_identify_payload(p, t)
                        for send_m in ("send_json", "send_as_json"):
                            fn = getattr(ws_ref, send_m, None)
                            if fn:
                                await fn(payload)
                                _POOL["last"] = p
                                _STATS["identifies"] += 1
                                if _COG[0]: _COG[0]._last_props = dict(p)
                                print(f"[spoofer] instance identify sent → {p['label']}")
                                return
                    except Exception as e:
                        print(f"[spoofer] patched identify error: {e}")

                setattr(ws, method_name, _patched)
                setattr(ws, f"_spoof_patched_{method_name}", True)
                print(f"[spoofer] instance {method_name} patched")

    @commands.Cog.listener()
    async def on_ready(self):
        _install_class_patch(self.bot)

    async def _reconnect(self):
        """
        Invalidate the gateway session then close the WebSocket.
        Clearing session_id / sequence forces the library to send a fresh
        IDENTIFY (OP 2) on reconnect instead of a RESUME (OP 6).
        Without this, code-4000 close still resumes — our OP2 interceptor
        never fires and the platform properties are never rewritten.
        """
        _STATS["reconnects"] += 1

        # ── Wipe session so the reconnect MUST do a full IDENTIFY ─────────────
        for obj in (
            getattr(self.bot, "_connection", None),
            getattr(self.bot, "ws", None),
        ):
            if obj is None:
                continue
            for attr in ("session_id", "_session_id",
                         "sequence",   "_sequence"):
                try:
                    if hasattr(obj, attr):
                        setattr(obj, attr, None)
                except Exception:
                    pass

        ws = getattr(self.bot, "ws", None)
        if ws:
            for code in (1000, 4000):
                try:
                    await ws.close(code=code)
                    return
                except Exception as e:
                    print(f"[spoofer] close({code}): {e}")

    async def _apply_and_reconnect(self, preset: dict, label: str, ctx):
        _set_pool([label]); _POOL["mode"] = "sticky"
        _patch_http(self.bot, preset)
        await ctx.message.edit(content=S.ui_ok(f"spoofing → {preset['label']}  (reconnecting…)"))

        # ── Reset stale last-identify record so the wait below is not fooled
        # by a previous connection's identify (e.g. the initial Desktop boot).
        _POOL["last"] = None

        await self._reconnect()

        # Wait up to 12 s for the new IDENTIFY to fire and be intercepted
        for _ in range(12):
            await asyncio.sleep(1)
            if _POOL["last"] is not None:
                break

        last = _POOL["last"]
        if last:
            await ctx.channel.send(S.ui_ok(
                f"✓  identified as {last['label']}\n"
                f"   os={last['os']}  browser={last['browser']}"
                f"  device={last.get('device','') or 'none'}"))
        else:
            await ctx.channel.send(S.ui_warn(
                "reconnected but IDENTIFY not intercepted — run .spooferdiag"))

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
                _POOL["keys"].append(sub); _POOL["pool"].append(PLATFORM_PRESETS[sub])
            return await ctx.message.edit(content=S.ui_ok(f"added {sub} — pool: {', '.join(_POOL['keys'])}"))

        if p == "remove" and sub:
            sub = sub.lower()
            if sub in _POOL["keys"]:
                i = _POOL["keys"].index(sub); _POOL["keys"].pop(i); _POOL["pool"].pop(i)
            return await ctx.message.edit(content=S.ui_ok(f"removed {sub}"))

        if p == "mode" and sub in ("rotate", "random", "sticky"):
            _POOL["mode"] = sub; _POOL["cursor"] = 0
            return await ctx.message.edit(content=S.ui_ok(f"mode → {sub}"))

        if p == "clear":
            _set_pool([])
            return await ctx.message.edit(content=S.ui_ok("pool cleared"))

        if p == "reset":
            preset = PLATFORM_PRESETS["desktop"]
            await self._apply_and_reconnect(preset, "desktop", ctx)
            return

        if p == "pool":
            rows = [f"  {k:<12} {PLATFORM_PRESETS[k]['label']}" for k in _POOL["keys"]]
            rows.append(f"\n  mode {_POOL['mode']}  cursor {_POOL['cursor']}")
            return await ctx.message.edit(content=S.ui_box("spoof pool", rows))

        if p not in PLATFORM_PRESETS:
            return await ctx.message.edit(
                content=S.ui_err(f"unknown: {p}  ·  valid: {', '.join(PLATFORM_PRESETS)}"))

        await self._apply_and_reconnect(PLATFORM_PRESETS[p], p, ctx)

    @commands.command(name="vr", brief="Spoof Meta Quest VR headset")
    async def vr(self, ctx):
        await self._apply_and_reconnect(PLATFORM_PRESETS["vr"], "vr", ctx)

    @commands.command(name="console", brief="Spoof console platform")
    async def console(self, ctx):
        await self._apply_and_reconnect(PLATFORM_PRESETS["console"], "console", ctx)

    @commands.command(name="spoofreset", brief="Reset spoofer to desktop")
    async def spoofreset(self, ctx):
        await self._apply_and_reconnect(PLATFORM_PRESETS["desktop"], "desktop", ctx)

    @commands.command(name="platform", brief="platform <preset>")
    async def platform_cmd(self, ctx, *, preset: str = ""):
        key = preset.strip().lower().split()[0] if preset.strip() else ""
        if not key:
            rows = [f"  {k:<14} {v['label']}" for k, v in PLATFORM_PRESETS.items()]
            return await ctx.message.edit(content=S.ui_box("platforms", rows))
        await self.spoof(ctx, key)

    @commands.command(name="spoofstatus", brief="Show current spoof status")
    async def spoofstatus(self, ctx):
        await self._show_status(ctx)

    @commands.command(name="spooferdiag", brief="Full spoofer diagnostics")
    async def spooferdiag(self, ctx):
        cls, path = _find_ws_class(self.bot)
        ws = getattr(self.bot, "ws", None)
        p  = self._last_props or {}
        patched_json    = getattr(cls, "_spoofer_patched_send_json",    False) if cls else False
        patched_as_json = getattr(cls, "_spoofer_patched_send_as_json", False) if cls else False
        ws_has_identify = hasattr(ws, "_spoof_patched_identify") if ws else False
        rows = [
            f"  {S.DIM}class found{S.RESET}         {path or 'NOT FOUND'}",
            f"  {S.DIM}send_json patched{S.RESET}   {'✓' if patched_json    else '✗'}",
            f"  {S.DIM}send_as_json patched{S.RESET}{'✓' if patched_as_json else '✗'}",
            f"  {S.DIM}instance identify{S.RESET}   {'✓' if ws_has_identify  else '✗'}",
            f"  {S.DIM}ws type{S.RESET}             {type(ws).__name__ if ws else 'None'}",
            f"  {S.DIM}has send_json{S.RESET}       {hasattr(ws, 'send_json') if ws else False}",
            f"  {S.DIM}has send_as_json{S.RESET}    {hasattr(ws, 'send_as_json') if ws else False}",
            f"  {S.DIM}has identify{S.RESET}        {hasattr(ws, 'identify') if ws else False}",
            f"  {S.DIM}has _identify{S.RESET}       {hasattr(ws, '_identify') if ws else False}",
            "",
            f"  {S.DIM}pool{S.RESET}  {', '.join(_POOL['keys']) or '—'}",
            f"  {S.DIM}mode{S.RESET}  {_POOL['mode']}",
            f"  {S.DIM}last{S.RESET}  {_POOL['last']['label'] if _POOL['last'] else '—'}",
            f"  {S.DIM}os{S.RESET}    {p.get('os','—')}",
            f"  {S.DIM}browser{S.RESET}  {p.get('browser','—')}",
            f"  {S.DIM}device{S.RESET}   {p.get('device','—') or 'none'}",
            "",
            f"  {S.DIM}identifies{S.RESET}  {_STATS['identifies']}",
            f"  {S.DIM}reconnects{S.RESET}  {_STATS['reconnects']}",
        ]
        await ctx.message.edit(content=S.ui_box("spoofer diag", rows))

    async def _show_status(self, ctx):
        preset = _POOL["last"] or {}
        p      = self._last_props or {}
        rows = [
            f"  {S.DIM}preset{S.RESET}   {preset.get('label','—')}",
            f"  {S.DIM}pool{S.RESET}     {', '.join(_POOL['keys']) or '—'}",
            f"  {S.DIM}mode{S.RESET}     {_POOL['mode']}",
            "",
            f"  {S.DIM}os{S.RESET}       {p.get('os', preset.get('os','?'))}",
            f"  {S.DIM}browser{S.RESET}  {p.get('browser', preset.get('browser','?'))}",
            f"  {S.DIM}device{S.RESET}   {p.get('device', preset.get('device','?')) or 'none'}",
            "",
            f"  {S.DIM}identifies{S.RESET} {_STATS['identifies']}",
            f"  {S.DIM}reconnects{S.RESET} {_STATS['reconnects']}",
            "",
            f"  {S.DIM}valid: {', '.join(PLATFORM_PRESETS)}{S.RESET}",
        ]
        await ctx.message.edit(content=S.ui_box("spoofer", rows))


async def setup(bot):
    await bot.add_cog(SpooferCog(bot))

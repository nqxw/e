# cogs/rpc.py | Rich Presence — 6 slots, presets, rotation, CDN refresh, persistence
import asyncio, aiohttp, io, json, re, time
from pathlib import Path
import discord
from discord.ext import commands
from . import state as S
from .antid import jitter

# ── Constants ─────────────────────────────────────────────────────────────────
PURPLESTREAM_URL = "https://www.twitch.tv/hadeontop"
DEFAULT_APP_ID   = 1112560163734691870

TYPE_MAP = {
    "playing": 0, "streaming": 1, "listening": 2,
    "watching": 3, "competing": 5, "purplestream": 1,
}
TYPE_NAMES = {0: "Playing", 1: "Streaming", 2: "Listening",
              3: "Watching", 5: "Competing"}

PLATFORM_PRESET_MAP = {
    "xbox":        {"application_id": 622174530214821906,   "platform": "xbox",       "asset": "xbox"},
    "ps":          {"application_id": 1470539864909943067,  "platform": "ps5",        "asset": "playstation"},
    "ps4":         {"application_id": 1470539864909943067,  "platform": "ps4",        "asset": "playstation"},
    "ps5":         {"application_id": 1470539864909943067,  "platform": "ps5",        "asset": "playstation"},
    "playstation": {"application_id": 1470539864909943067,  "platform": "ps5",        "asset": "playstation"},
    "crunchyroll": {"application_id": 981509069309354054,   "platform": None,         "asset": "crunchyroll"},
    "crunchy":     {"application_id": 981509069309354054,   "platform": None,         "asset": "crunchyroll"},
    "youtube":     {"application_id": 111299001912,          "platform": None,         "asset": "youtube"},
    "twitch":      {"application_id": 111299001912,          "platform": None,         "asset": "twitch"},
    "vrchat":      {"application_id": 1498387526501535835,  "platform": "meta_quest", "asset": "vrchat"},
    "meta_quest":  {"application_id": 1498387526501535835,  "platform": "meta_quest", "asset": "vrchat"},
    "meta":        {"application_id": 1498387526501535835,  "platform": "meta_quest", "asset": "vrchat"},
    "quest":       {"application_id": 1498387526501535835,  "platform": "meta_quest", "asset": "vrchat"},
    "oculus":      {"application_id": 1498387526501535835,  "platform": "meta_quest", "asset": "vrchat"},
    "roblox":      {"application_id": 1552026905023356938,  "platform": None,         "asset": "roblox"},
    "spotify":     {"application_id": 3201606009684,         "platform": None,         "asset": "spotify"},
}

# Icon-only presets: apply the app_id + large_image without touching name/details/state.
# This lets you show e.g. the Roblox icon on a fully custom activity.
ICON_PRESETS = {
    "roblox":      {"application_id": "1552026905023356938", "large_image": "roblox",       "small_text": "Roblox"},
    "xbox":        {"application_id": "622174530214821906",  "large_image": "xbox",         "small_text": "Xbox"},
    "ps":          {"application_id": "1470539864909943067", "large_image": "playstation",  "small_text": "PlayStation"},
    "ps4":         {"application_id": "1470539864909943067", "large_image": "playstation",  "small_text": "PS4"},
    "ps5":         {"application_id": "1470539864909943067", "large_image": "playstation",  "small_text": "PS5"},
    "spotify":     {"application_id": "3201606009684",        "large_image": "spotify",      "small_text": "Spotify"},
    "youtube":     {"application_id": "111299001912",         "large_image": "youtube",      "small_text": "YouTube"},
    "crunchyroll": {"application_id": "981509069309354054",  "large_image": "crunchyroll",  "small_text": "Crunchyroll"},
    "vrchat":      {"application_id": "1498387526501535835", "large_image": "vrchat",       "small_text": "VRChat"},
    "twitch":      {"application_id": "111299001912",         "large_image": "twitch",       "small_text": "Twitch"},
    "meta":        {"application_id": "1498387526501535835", "large_image": "vrchat",       "small_text": "Meta Quest"},
    "quest":       {"application_id": "1498387526501535835", "large_image": "vrchat",       "small_text": "Meta Quest"},
    "quest2":      {"application_id": "1498387526501535835", "large_image": "vrchat",       "small_text": "Meta Quest 2"},
    "quest3":      {"application_id": "1498387526501535835", "large_image": "vrchat",       "small_text": "Meta Quest 3"},
    "metaquest":   {"application_id": "1498387526501535835", "large_image": "vrchat",       "small_text": "Meta Quest"},
    # ── Streaming — Discord Watch Together app IDs ────────────────────────────
    "netflix":     {"application_id": "1045108407458267217", "large_image": "netflix",      "small_text": "Netflix"},
    "prime":       {"application_id": "474659241278947329",  "large_image": "prime_video",  "small_text": "Prime Video"},
    "primevideo":  {"application_id": "474659241278947329",  "large_image": "prime_video",  "small_text": "Prime Video"},
    "disney":      {"application_id": "1034427773249798284", "large_image": "disneyplus",   "small_text": "Disney+"},
    "disneyplus":  {"application_id": "1034427773249798284", "large_image": "disneyplus",   "small_text": "Disney+"},
    "hulu":        {"application_id": "1045543797585559652", "large_image": "hulu",         "small_text": "Hulu"},
    "funimation":  {"application_id": "992020185348001822",  "large_image": "funimation",   "small_text": "Funimation"},
    "appletv":     {"application_id": "1067250063950274571", "large_image": "appletv",      "small_text": "Apple TV"},
    "apple_tv":    {"application_id": "1067250063950274571", "large_image": "appletv",      "small_text": "Apple TV"},
    # ── Other media ───────────────────────────────────────────────────────────
    "plex":        {"application_id": "521825494798237696",  "large_image": "plex",              "small_text": "Plex"},
    # ── Riot Games (official Discord RPC) ─────────────────────────────────────
    "lol":             {"application_id": "401518684763586560", "large_image": "league_of_legends", "small_text": "League of Legends"},
    "league":          {"application_id": "401518684763586560", "large_image": "league_of_legends", "small_text": "League of Legends"},
    "leagueoflegends": {"application_id": "401518684763586560", "large_image": "league_of_legends", "small_text": "League of Legends"},
    "valorant":        {"application_id": "700136079562375258", "large_image": "valorant",          "small_text": "Valorant"},
    "tft":             {"application_id": "401518684763586560", "large_image": "teamfight_tactics",  "small_text": "Teamfight Tactics"},
}

# Fallback image URLs per platform — used when Discord's /applications/{id}/rpc
# returns null for the icon field (e.g. Roblox, VRChat use per-session thumbnails).
# All fetched, re-uploaded to Discord CDN via DM, so the mp:attachments key works.
PLATFORM_ICON_FALLBACK_URLS: dict = {
    "roblox":      "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Roblox_logo.svg/512px-Roblox_logo.svg.png",
    "xbox":        "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/Xbox_one_logo.svg/512px-Xbox_one_logo.svg.png",
    "playstation": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Playstation_logo_colour.svg/512px-Playstation_logo_colour.svg.png",
    "ps":          "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Playstation_logo_colour.svg/512px-Playstation_logo_colour.svg.png",
    "ps4":         "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Playstation_logo_colour.svg/512px-Playstation_logo_colour.svg.png",
    "spotify":     "https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/Spotify_icon.svg/512px-Spotify_icon.svg.png",
    "youtube":     "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/YouTube_full-color_icon_%282017%29.svg/512px-YouTube_full-color_icon_%282017%29.svg.png",
    "crunchyroll": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Crunchyroll_Logo.svg/512px-Crunchyroll_Logo.svg.png",
    "twitch":      "https://upload.wikimedia.org/wikipedia/commons/thumb/2/26/Twitch_logo.svg/512px-Twitch_logo.svg.png",
    "netflix":     "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Netflix_2015_logo.svg/512px-Netflix_2015_logo.svg.png",
    "discord":     "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Logo_of_Twitter.svg/512px-Logo_of_Twitter.svg.png",
    "vrchat":      "https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/Spotify_icon.svg/512px-Spotify_icon.svg.png",
    "plex":        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Plex_logo_2022.svg/512px-Plex_logo_2022.svg.png",
    "lol":         "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/League_of_Legends_2019_vector.svg/512px-League_of_Legends_2019_vector.svg.png",
    "league":      "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/League_of_Legends_2019_vector.svg/512px-League_of_Legends_2019_vector.svg.png",
    "valorant":    "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Valorant_logo_-_pink_color_version.svg/512px-Valorant_logo_-_pink_color_version.svg.png",
}

INLINE_KEYS = ["name", "details", "state", "type", "timestamp",
               "large_image_text", "large_image", "small_image", "btn1", "btn2"]

GATEWAY_KEYS = {
    "type","name","url","details","state","application_id",
    "assets","timestamps","buttons","platform","sync_id",
    "session_id","party","secrets","flags","instance",
}

_MIN_REPUSH_GAP   = 30
_WATCH_INTERVAL   = 45
_BOOT_SETTLE      = 5.0


class RPCCog(commands.Cog, name="rpc"):
    """Rich Presence — 6 slots, platform presets, rotation, CDN refresh, persistence."""

    def __init__(self, bot):
        self.bot                   = bot
        self.rpc_slots             = [None] * 6
        self._slot_platform_preset = [None] * 6
        self._asset_cache:  dict   = {}    # image_url -> mp:... key
        self._asset_urls:   dict   = {}    # mp:... key -> original URL (for refresh)
        self.status_rotation_active= False
        self.emoji_rotation_active = False
        self._status_rotation_task = None
        self._emoji_rotation_task  = None
        self.current_status        = ""
        self.current_emoji         = ""
        self._clearing             = False
        self._watchdog_task        = None
        self._last_push_ts         = 0.0
        self._watchdog_cycles      = 0
        self._icon_cache: dict     = {}   # icon key -> mp:attachments key

    async def cog_load(self):
        # Load saved slots + asset URLs, then start watchdog
        try:
            self._load_rpc_slots()
            self._load_asset_urls()
        except Exception as e:
            print(f"[rpc] load error: {e}")
        await asyncio.sleep(_BOOT_SETTLE)
        self._watchdog_task = asyncio.create_task(self._watchdog_boot())

    def cog_unload(self):
        for t in [self._watchdog_task,
                  self._status_rotation_task,
                  self._emoji_rotation_task]:
            if t and not t.done():
                t.cancel()

    # ── File helpers ──────────────────────────────────────────────────────────
    def _data_path(self, filename: str) -> Path:
        """Per-user data path: data/<user_id>_<filename>"""
        if self.bot and getattr(self.bot, "user", None):
            uid = str(self.bot.user.id)
            p = Path(f"data/{uid}_{filename}")
        else:
            p = Path(f"data/_unready_{filename}")
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _save_rpc_slots(self):
        try:
            path = self._data_path("slots.json")
            strip = {"instance","flags","session_id","sync_id","secrets","party","metadata"}
            data  = [
                {k: v for k, v in slot.items() if k not in strip} if slot else None
                for slot in self.rpc_slots
            ]
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[rpc] save slots: {e}")

    def _load_rpc_slots(self):
        path = self._data_path("slots.json")
        if not path.exists(): return
        try:
            with open(path) as f:
                data = json.load(f)
            for i, slot in enumerate(data[:6]):
                if slot:
                    slot.setdefault("type", 0)
                    slot.setdefault("name", "Default")
                    slot.setdefault("application_id", DEFAULT_APP_ID)
                    slot.setdefault("assets", {})
                    self.rpc_slots[i] = slot
            n = sum(1 for s in self.rpc_slots if s)
            if n: print(f"[rpc] loaded {n} saved slots")
        except Exception as e:
            print(f"[rpc] load slots: {e}")

    def _save_asset_urls(self):
        try:
            path = self._data_path("asset_urls.json")
            with open(path, "w") as f:
                json.dump(self._asset_urls, f, indent=2)
        except Exception: pass

    def _load_asset_urls(self):
        path = self._data_path("asset_urls.json")
        if not path.exists(): return
        try:
            with open(path) as f:
                self._asset_urls = json.load(f)
        except Exception:
            self._asset_urls = {}

    # ── Gateway send ──────────────────────────────────────────────────────────
    async def _send_presence_payload(self, activities: list, status: str = "online") -> bool:
        payload = {
            "op": 3,
            "d": {"since": 0, "activities": activities, "status": status, "afk": False},
        }
        # Try gateway WS first (supports all fields: platform, buttons, app_id)
        ws = getattr(self.bot, "ws", None)
        if ws:
            for method in ("send_json", "send_as_json"):
                fn = getattr(ws, method, None)
                if fn:
                    try:
                        await fn(payload)
                        self._last_push_ts = time.time()
                        return True
                    except Exception as e:
                        print(f"[rpc] ws.{method}: {e}")

        # Fallback: change_presence with Activity objects (loses platform/buttons/app_id)
        try:
            act_objs = []
            for a in activities:
                t, n = a.get("type", 0), a.get("name", "")
                if   t == 0: act_objs.append(discord.Game(name=n))
                elif t == 1: act_objs.append(discord.Streaming(name=n, url=a.get("url","")))
                elif t == 2: act_objs.append(discord.Activity(type=discord.ActivityType.listening, name=n))
                elif t == 3: act_objs.append(discord.Activity(type=discord.ActivityType.watching,  name=n))
                elif t == 5: act_objs.append(discord.Activity(type=discord.ActivityType.competing, name=n))
            await self.bot.change_presence(
                activity=act_objs[0] if act_objs else None,
                status=discord.Status(status))
            self._last_push_ts = time.time()
            return True
        except Exception as e:
            print(f"[rpc] change_presence fallback: {e}")
            return False

    def _clean_activity(self, slot: dict) -> dict:
        clean = {k: v for k, v in slot.items() if k in GATEWAY_KEYS}
        if "application_id" in clean:
            clean["application_id"] = str(clean["application_id"])
        if "assets" in clean:
            clean["assets"] = {k: v for k, v in clean["assets"].items() if v}
            if not clean["assets"]: del clean["assets"]
        if "type" in clean and isinstance(clean["type"], str):
            clean["type"] = TYPE_MAP.get(clean["type"].lower(), 0)
        return clean

    async def apply_activities(self):
        active  = [self._clean_activity(a) for a in self.rpc_slots if a is not None]
        ok      = await self._send_presence_payload(active, "online")
        if ok:  self._save_rpc_slots()
        else:   print("[rpc] push failed — will retry on next watchdog tick")


    # ── Watchdog ──────────────────────────────────────────────────────────────
    async def _watchdog_boot(self):
        await self.bot.wait_until_ready()
        # Restore saved presence if any slots loaded
        if any(s is not None for s in self.rpc_slots):
            try:
                await self.apply_activities()
                print("[rpc] restored saved presence")
            except Exception as e:
                print(f"[rpc] restore push failed: {e}")
        await self._watchdog_loop()

    async def _watchdog_loop(self):
        while not self.bot.is_closed():
            try:
                await asyncio.sleep(jitter(_WATCH_INTERVAL))
                self._watchdog_cycles += 1
                has_slots = any(s is not None for s in self.rpc_slots)
                stale     = time.time() - self._last_push_ts > _MIN_REPUSH_GAP
                if has_slots and stale:
                    await self.apply_activities()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[rpc] watchdog: {e}")

    # ── Slot helpers ──────────────────────────────────────────────────────────
    def _ensure_slot(self, i: int):
        if self.rpc_slots[i] is None:
            self.rpc_slots[i] = {
                "type": 0, "name": "Default",
                "application_id": DEFAULT_APP_ID,
                "assets": {}, "instance": True,
            }

    def _set_timestamp(self, slot: int, value: str):
        v = value.strip()
        if ":" in v:
            p = v.split(":")
            secs = (int(p[0])*3600+int(p[1])*60+int(p[2]) if len(p)==3
                    else int(p[0])*60+int(p[1]))
        else:
            secs = float(v) * 3600
        now = int(time.time() * 1000)
        self.rpc_slots[slot]["timestamps"] = {
            "start": now, "end": now + int(secs * 1000)}

    def _apply_platform_preset(self, slot: int, key: str) -> bool:
        if key in {"off","none","clear","normal"}:
            self._slot_platform_preset[slot] = None
            self._ensure_slot(slot)
            self.rpc_slots[slot]["application_id"] = DEFAULT_APP_ID
            self.rpc_slots[slot].pop("platform", None)
            return True
        preset = PLATFORM_PRESET_MAP.get(key)
        if not preset: return False
        self._ensure_slot(slot)
        self._slot_platform_preset[slot] = key
        self.rpc_slots[slot]["application_id"] = preset["application_id"]
        if preset["platform"]: self.rpc_slots[slot]["platform"] = preset["platform"]
        else: self.rpc_slots[slot].pop("platform", None)
        self.rpc_slots[slot].setdefault("assets",{})["large_image"] = preset["asset"]
        return True

    def _parse_inline(self, args: str) -> dict:
        result, words = {}, args.split()
        pos = [(w.lower(), i) for i, w in enumerate(words) if w.lower() in INLINE_KEYS]
        for idx, (key, p) in enumerate(pos):
            end   = pos[idx+1][1] if idx+1 < len(pos) else len(words)
            value = " ".join(words[p+1:end]).strip()
            if value: result[key] = value
        return result

    async def _apply_inline(self, slot: int, parsed: dict):
        self._ensure_slot(slot)
        act = self.rpc_slots[slot]
        for k in ("name","details","state"):
            if k in parsed: act[k] = parsed[k]
        if "type" in parsed:
            t = parsed["type"].lower()
            if t in TYPE_MAP:
                act["type"] = TYPE_MAP[t]
                if t == "purplestream": act["url"] = PURPLESTREAM_URL
                elif "url" in act and t not in ("streaming","purplestream"): del act["url"]
        if "timestamp" in parsed:
            v = parsed["timestamp"]
            if v.lower() == "clear": act.pop("timestamps", None)
            else:
                try: self._set_timestamp(slot, v)
                except Exception: pass

    # ── Asset upload ──────────────────────────────────────────────────────────
    async def upload_asset(self, image_url: str) -> str | None:
        """
        Download image_url and re-upload to Discord CDN via DM-with-self.
        Returns an mp:attachments/... key that works as large_image in activities.
        Ported from the original modifyself version (the one that actually worked).
        """
        if not image_url: return None
        if image_url in self._asset_cache: return self._asset_cache[image_url]

        # Fast-path: already a Discord CDN attachment URL → convert directly
        cdn_re = re.compile(
            r"https?://(?:cdn\.discordapp\.com|media\.discordapp\.net)"
            r"/attachments/(\d+)/(\d+)/([^?#\s]+)")
        m = cdn_re.search(image_url)
        if m:
            key = f"mp:attachments/{m.group(1)}/{m.group(2)}/{m.group(3)}"
            self._asset_cache[image_url] = key
            self._asset_urls[key] = image_url
            return key

        if not self.bot or not getattr(self.bot, "user", None):
            print("[rpc] upload_asset: bot.user not ready")
            return None

        try:
            # Use Discord-style headers — some CDNs check Referer/UA
            fetch_h = {
                "Authorization": S.TOKEN,
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "discord/1.0.9191 Chrome/132.0.0.0 Safari/537.36"
                ),
                "Accept":   "image/*,*/*;q=0.8",
                "Referer":  "https://discord.com/",
            }
            async with aiohttp.ClientSession(headers=fetch_h) as sess:
                async with sess.get(image_url) as r:
                    if r.status != 200:
                        print(f"[rpc] upload_asset fetch {r.status}: {image_url[:80]}")
                        return None
                    image_bytes = await r.read()

            if not image_bytes:
                print("[rpc] upload_asset: empty body")
                return None

            # Derive filename; Discord may reject .webp in DMs — rename to .png
            raw  = image_url.split("/")[-1].split("?")[0]
            name = raw if ("." in raw and len(raw) <= 50) else "asset.png"
            if name.lower().endswith(".webp"):
                name = name.rsplit(".", 1)[0] + ".png"

            # Get DM channel with self
            self_dm = self.bot.user.dm_channel
            if self_dm is None:
                self_dm = await self.bot.user.create_dm()

            msg = await self_dm.send(
                file=discord.File(io.BytesIO(image_bytes), filename=name))

            if msg.attachments:
                att     = msg.attachments[0]
                # Handle both object and dict form (discord.py-self varies)
                new_url = (att.get("url") if isinstance(att, dict)
                           else getattr(att, "url", None))
                if new_url:
                    m2 = cdn_re.search(new_url)
                    if m2:
                        key = f"mp:attachments/{m2.group(1)}/{m2.group(2)}/{m2.group(3)}"
                        self._asset_cache[image_url] = key
                        self._asset_urls[key] = image_url
                        self._save_asset_urls()
                        print(f"[rpc] upload_asset ok: {key[:60]}")
                        return key
                    print(f"[rpc] upload_asset: no CDN match in {new_url[:80]}")
                else:
                    print("[rpc] upload_asset: no url on attachment")
            else:
                print("[rpc] upload_asset: msg has no attachments")

        except Exception as e:
            import traceback as _tb
            print(f"[rpc] upload_asset failed: {type(e).__name__}: {e}")
            _tb.print_exc()
        return None


    # ── Icon fetch helper ─────────────────────────────────────────────────────
    async def _fetch_app_icon(self, app_id: str, cache_key: str) -> str | None:
        """
        Fetch a Discord application's icon and upload it as an mp:attachments key.
        The /applications/{id}/rpc endpoint is public — no auth required.
        Returns the mp:attachments key, or None if anything fails.
        """
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        icon_hash = None
        # Try two endpoints: public RPC info, then authenticated app info
        for endpoint, needs_auth in [
            (f"https://discord.com/api/v9/applications/{app_id}/rpc", False),
            (f"https://discord.com/api/v9/applications/{app_id}",     True),
        ]:
            try:
                h = {"User-Agent": S.USER_AGENT}
                if needs_auth: h["Authorization"] = S.TOKEN
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(endpoint, headers=h) as r:
                        if r.status == 200:
                            data = await r.json()
                            icon_hash = data.get("icon")
                            if icon_hash:
                                break
                        else:
                            print(f"[rpc] icon endpoint {endpoint}: HTTP {r.status}")
            except Exception as e:
                print(f"[rpc] icon endpoint error: {e}")
        if not icon_hash:
            # Discord API returned no icon — try the platform fallback URL instead
            fallback_url = PLATFORM_ICON_FALLBACK_URLS.get(cache_key)
            if fallback_url:
                print(f"[rpc] no Discord icon for {app_id} — using fallback URL for {cache_key}")
                mp_key = await self.upload_asset(fallback_url)
                if mp_key:
                    self._icon_cache[cache_key] = mp_key
                    print(f"[rpc] fallback icon {cache_key} cached → {mp_key[:50]}")
                return mp_key
            print(f"[rpc] no icon hash and no fallback URL for app {app_id} ({cache_key})")
            return None
        try:
            # Use .png — discord.py-self DM uploads may reject .webp
            icon_url = (f"https://cdn.discordapp.com/app-icons/"
                        f"{app_id}/{icon_hash}.png?size=256")
            print(f"[rpc] fetching icon for {cache_key}: {icon_url[:80]}")
            mp_key = await self.upload_asset(icon_url)
            if mp_key:
                self._icon_cache[cache_key] = mp_key
                print(f"[rpc] icon {cache_key} cached → {mp_key[:50]}")
            return mp_key
        except Exception as e:
            print(f"[rpc] _fetch_app_icon upload({app_id}): {e}")
            return None

    # ── Custom status ─────────────────────────────────────────────────────────
    async def _patch_custom_status(self):
        try:
            h = {"Authorization": S.TOKEN, "Content-Type": "application/json",
                 "User-Agent": S.USER_AGENT}
            async with aiohttp.ClientSession() as sess:
                await sess.patch(
                    "https://discord.com/api/v9/users/@me/settings",
                    headers=h,
                    json={"custom_status": {
                        "text":       self.current_status or None,
                        "emoji_name": self.current_emoji  or None,
                    }})
        except Exception as e:
            print(f"[rpc] patch_custom_status: {e}")

    # ── Field routing for platform presets ───────────────────────────────────
    # For app-name-fixed presets the 'content' is NOT in the name field:
    #   Roblox / YouTube / Crunchyroll / Spotify → details
    #   VRChat / Meta Quest                      → state
    #   Xbox / PS / custom                       → name  (correct as-is)
    _DETAILS_PRESETS = {
        "1552026905023356938",  # Roblox     (details = game title)
        "111299001912",         # YouTube    (details = video title)
        "981509069309354054",   # Crunchyroll(details = anime title)
        "3201606009684",        # Spotify    (details = song title)
    }
    _STATE_PRESETS = {
        "1498387526501535835",  # VRChat / Meta Quest (state = world/activity)
    }

    def _content_field(self, slot: int) -> str:
        """Return the field that holds the main 'content name' for this slot."""
        act    = self.rpc_slots[slot]
        app_id = str(act.get("application_id", "")) if act else ""
        if app_id in self._DETAILS_PRESETS: return "details"
        if app_id in self._STATE_PRESETS:   return "state"
        return "name"

    # ── Slot command handler ──────────────────────────────────────────────────
    async def _handle_slot_ctx(self, ctx, slot: int, sub: str, rest: str):
        label = f"RPC{slot+1}"
        rest  = rest.strip()
        sub   = sub.lower() if sub else ""

        SUBS = {"name","details","state","type","timestamp",
                "large_image","small_image","large_image_text","btn1","btn2",
                "appname","icon",
                "spotify","youtube","xbox","ps","ps4","crunchy","crunchyroll",
                "roblox","vrchat","clear","show"}

        # No sub → show current slot
        if not sub or sub == "show":
            act = self.rpc_slots[slot]
            if not act:
                return await ctx.message.edit(content=S.ui_info(f"{label} — empty"))
            rows = [f"  {S.GREY}{k:<20}{S.RESET}{v}"
                    for k, v in act.items() if k not in ("instance","flags","metadata")]
            return await ctx.message.edit(content=S.ui_box(label, rows))

        # Unknown sub → try inline parse
        if sub not in SUBS:
            parsed = self._parse_inline(f"{sub} {rest}".strip())
            if parsed:
                await self._apply_inline(slot, parsed)
                await self.apply_activities()
                return await ctx.message.edit(content=S.ui_ok(f"{label} updated"))
            return await ctx.message.edit(
                content=S.ui_err(f"unknown sub: {sub}  ·  "
                                 f"name · details · state · type · platform · "
                                 f"timestamp · large_image · small_image · btn1 · btn2 · clear"))

        if sub == "name":
            self._ensure_slot(slot)
            field = self._content_field(slot)
            self.rpc_slots[slot][field] = rest
            if field != "name":
                await self.apply_activities()
                return await ctx.message.edit(
                    content=S.ui_ok(f"{label} {field} → {rest}"))
        elif sub == "appname":
            # Force-override the 'name' field regardless of preset — bypasses routing
            if not rest:
                return await ctx.message.edit(
                    content=S.ui_err("usage: rpc1 appname <name>  (cannot be empty)"))
            self._ensure_slot(slot)
            self.rpc_slots[slot]["name"] = rest
            await self.apply_activities()
            return await ctx.message.edit(content=S.ui_ok(f"{label} appname → {rest}"))
        elif sub == "icon":
            # Apply a platform icon (app_id + large_image) without touching name/details/state
            key = rest.strip().lower()
            if not key:
                valid = ", ".join(ICON_PRESETS)
                return await ctx.message.edit(
                    content=S.ui_info(f"valid icons: {valid}"))
            if key not in ICON_PRESETS:
                valid = ", ".join(ICON_PRESETS)
                return await ctx.message.edit(
                    content=S.ui_err(f"unknown icon: {key}  ·  valid: {valid}"))
            preset = ICON_PRESETS[key]
            self._ensure_slot(slot)
            self.rpc_slots[slot]["application_id"] = preset["application_id"]
            # Try to get the real Discord app icon (guaranteed to render)
            mp_key = await self._fetch_app_icon(preset["application_id"], key)
            large_image = mp_key if mp_key else preset["large_image"]
            self.rpc_slots[slot].setdefault("assets", {})["large_image"] = large_image
            if preset.get("small_text"):
                self.rpc_slots[slot]["assets"]["large_text"] = preset["small_text"]
            await self.apply_activities()
            src_label = "uploaded" if mp_key else "asset key"
            return await ctx.message.edit(
                content=S.ui_ok(f"{label} icon → {key}  ({src_label})"))
        elif sub == "details":
            self._ensure_slot(slot); self.rpc_slots[slot]["details"] = rest
        elif sub == "state":
            self._ensure_slot(slot); self.rpc_slots[slot]["state"] = rest
        elif sub == "type":
            t = rest.lower()
            if t not in TYPE_MAP:
                return await ctx.message.edit(content=S.ui_err(f"valid: {', '.join(TYPE_MAP)}"))
            self._ensure_slot(slot)
            self.rpc_slots[slot]["type"] = TYPE_MAP[t]
            if t == "purplestream": self.rpc_slots[slot]["url"] = PURPLESTREAM_URL
            elif "url" in self.rpc_slots[slot] and t not in ("streaming","purplestream"):
                del self.rpc_slots[slot]["url"]

        elif sub == "timestamp":
            self._ensure_slot(slot)
            if rest.lower() == "clear":
                self.rpc_slots[slot].pop("timestamps", None)
            else:
                try: self._set_timestamp(slot, rest)
                except Exception: return await ctx.message.edit(content=S.ui_err("format: 3600  or  1:30:00"))
        elif sub == "large_image":
            if not rest: return await ctx.message.edit(content=S.ui_err(f"usage: rpc{slot+1} large_image <url>"))
            key = await self.upload_asset(rest)
            if not key: return await ctx.message.edit(content=S.ui_err("upload failed"))
            self._ensure_slot(slot); self.rpc_slots[slot].setdefault("assets",{})["large_image"] = key
        elif sub == "small_image":
            if not rest: return await ctx.message.edit(content=S.ui_err(f"usage: rpc{slot+1} small_image <url>"))
            key = await self.upload_asset(rest)
            if not key: return await ctx.message.edit(content=S.ui_err("upload failed"))
            self._ensure_slot(slot); self.rpc_slots[slot].setdefault("assets",{})["small_image"] = key
        elif sub == "large_image_text":
            self._ensure_slot(slot); self.rpc_slots[slot].setdefault("assets",{})["large_text"] = rest
        elif sub == "btn1":
            parts = rest.split()
            if len(parts) < 2: return await ctx.message.edit(content=S.ui_err("btn1 <label> <url>"))
            self._ensure_slot(slot)
            btns = self.rpc_slots[slot].setdefault("buttons", [])
            entry = {"label": " ".join(parts[:-1])[:32], "url": parts[-1]}
            if not btns: btns.append(entry)
            else: btns[0] = entry
        elif sub == "btn2":
            parts = rest.split()
            if len(parts) < 2: return await ctx.message.edit(content=S.ui_err("btn2 <label> <url>"))
            self._ensure_slot(slot)
            btns = self.rpc_slots[slot].setdefault("buttons", [])
            while len(btns) < 2: btns.append(None)
            btns[1] = {"label": " ".join(parts[:-1])[:32], "url": parts[-1]}
            self.rpc_slots[slot]["buttons"] = [b for b in btns if b]
        elif sub in ("spotify","youtube","xbox","ps","ps4",
                     "crunchy","crunchyroll","roblox","vrchat"):
            ps = [p.strip() for p in rest.split("-") if p.strip()]
            bmap = {
                "spotify": self.build_spotify,  "youtube": self.build_youtube,
                "xbox":    self.build_xbox,      "roblox":  self.build_roblox,
                "vrchat":  self.build_vrchat,
                "crunchy": self.build_crunchyroll, "crunchyroll": self.build_crunchyroll,
            }
            if sub in ("ps","ps4"):
                act = await self.build_playstation(ps or ["PlayStation"], ps4=(sub=="ps4"))
            else:
                act = await bmap[sub](ps or [sub.capitalize()])
            if act: self.rpc_slots[slot] = act
        elif sub == "clear":
            self.rpc_slots[slot] = None
            await self.apply_activities()
            return await ctx.message.edit(content=S.ui_ok(f"{label} cleared"))

        await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"{label} {sub} → {rest or 'set'}"))

    # ── Slot commands ─────────────────────────────────────────────────────────
    @commands.command(name="rpc1", brief="RPC slot 1  — rpc1 <sub> <value>")
    async def rpc1(self, ctx, sub: str = "", *, rest: str = ""):
        await self._handle_slot_ctx(ctx, 0, sub, rest)

    @commands.command(name="rpc2", brief="RPC slot 2")
    async def rpc2(self, ctx, sub: str = "", *, rest: str = ""):
        await self._handle_slot_ctx(ctx, 1, sub, rest)

    @commands.command(name="rpc3", brief="RPC slot 3")
    async def rpc3(self, ctx, sub: str = "", *, rest: str = ""):
        await self._handle_slot_ctx(ctx, 2, sub, rest)

    @commands.command(name="rpc4", brief="RPC slot 4")
    async def rpc4(self, ctx, sub: str = "", *, rest: str = ""):
        await self._handle_slot_ctx(ctx, 3, sub, rest)

    @commands.command(name="rpc5", brief="RPC slot 5")
    async def rpc5(self, ctx, sub: str = "", *, rest: str = ""):
        await self._handle_slot_ctx(ctx, 4, sub, rest)

    @commands.command(name="rpc6", brief="RPC slot 6")
    async def rpc6(self, ctx, sub: str = "", *, rest: str = ""):
        await self._handle_slot_ctx(ctx, 5, sub, rest)

    # ── Management ────────────────────────────────────────────────────────────
    @commands.command(name="rpc", brief="Show RPC slot summary")
    async def rpc(self, ctx):
        type_names = {0:"Playing",1:"Streaming",2:"Listening",3:"Watching",5:"Competing"}
        lines = []
        for i, act in enumerate(self.rpc_slots):
            if act is None:
                lines.append(f"RPC{i+1} — empty")
            else:
                t     = type_names.get(act.get("type",0),"?")
                plat  = f"  [{act['platform']}]" if "platform" in act else ""
                lines.append(
                    f"RPC{i+1} [{t}]{plat}  {act.get('name','—')} | "
                    f"{act.get('details','—')} | {act.get('state','—')}")
        await ctx.message.edit(content=S._ansi_block(lines))

    @commands.command(name="rpc_status", aliases=["rpcstatus"], brief="Detailed RPC slot status")
    async def rpc_status(self, ctx):
        type_names = {0:"Playing",1:"Streaming",2:"Listening",3:"Watching",5:"Competing"}
        lines = []
        for i, act in enumerate(self.rpc_slots):
            if act is None:
                lines.append(f"  {S.GREY}RPC{i+1}{S.RESET}  empty")
            else:
                t    = type_names.get(act.get("type",0),"?")
                plat = f"  [{act['platform']}]" if "platform" in act else ""
                lines.append(
                    f"  {S.CYAN}RPC{i+1}{S.RESET}  [{t}]{plat}  "
                    f"{act.get('name','—')} | {act.get('details','—')} | {act.get('state','—')}")
        wd    = bool(self._watchdog_task and not self._watchdog_task.done())
        since = int(time.time()-self._last_push_ts) if self._last_push_ts else -1
        lines += [
            "",
            f"  {S.DIM}watchdog{S.RESET}   {'on' if wd else 'off'}  "
            f"·  cycles {self._watchdog_cycles}  "
            f"·  last push {'never' if since<0 else f'{since}s ago'}",
        ]
        await ctx.message.edit(content=S._ansi_block(lines))

    @commands.command(name="clear_multi_rpc", aliases=["clearrpc","aoff"], brief="Clear all RPC slots")
    async def clear_multi_rpc(self, ctx):
        self.rpc_slots = [None] * 6
        await self._send_presence_payload([], "online")
        self._save_rpc_slots()
        await ctx.message.edit(content=S.ui_ok("All RPC slots cleared"))

    @commands.command(name="stopactivity", brief="Stop current activity")
    async def stopactivity(self, ctx):
        self.rpc_slots = [None] * 6
        await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok("Activity cleared"))

    @commands.command(name="setpresencestatus", brief="Set status  setpresencestatus <online|idle|dnd|invisible>")
    async def setpresencestatus(self, ctx, status: str = "online"):
        valid = {"online","idle","dnd","invisible","offline"}
        if status.lower() not in valid:
            return await ctx.message.edit(content=S.ui_err(f"valid: {', '.join(valid)}"))
        ok = await self._send_presence_payload(
            [self._clean_activity(a) for a in self.rpc_slots if a],
            status.lower())
        await ctx.message.edit(
            content=S.ui_ok(f"status → {status}") if ok else S.ui_err("failed"))

    # ── Status / emoji rotation ───────────────────────────────────────────────
    @commands.command(name="rstatus", brief="Rotating status  rstatus a, b, c")
    async def rstatus(self, ctx, *, statuses: str = ""):
        if not statuses:
            return await ctx.message.edit(content=S.ui_err("usage: rstatus s1, s2, s3"))
        sl = [s.strip() for s in statuses.split(",") if s.strip()]
        if not sl: return await ctx.message.edit(content=S.ui_err("separate with commas"))
        if self._status_rotation_task and not self._status_rotation_task.done():
            self._status_rotation_task.cancel()
        self.status_rotation_active = True

        async def _loop():
            idx = 0
            try:
                while self.status_rotation_active:
                    self.current_status = sl[idx]
                    await self._patch_custom_status()
                    await asyncio.sleep(jitter(8.0))
                    idx = (idx + 1) % len(sl)
            finally:
                self.current_status = ""
                try: await self._patch_custom_status()
                except Exception: pass

        self._status_rotation_task = asyncio.create_task(_loop())
        await ctx.message.edit(content=S.ui_ok(f"status rotation → {len(sl)} statuses"))

    @commands.command(name="remoji", brief="Rotating emoji  remoji 🔥, 💎, ⭐")
    async def remoji(self, ctx, *, emojis: str = ""):
        if not emojis: return await ctx.message.edit(content=S.ui_err("usage: remoji 🔥, 💎"))
        el = [e.strip() for e in emojis.split(",") if e.strip()]
        if not el: return await ctx.message.edit(content=S.ui_err("separate with commas"))
        if self._emoji_rotation_task and not self._emoji_rotation_task.done():
            self._emoji_rotation_task.cancel()
        self.emoji_rotation_active = True

        async def _loop():
            idx = 0
            try:
                while self.emoji_rotation_active:
                    self.current_emoji = el[idx]
                    await self._patch_custom_status()
                    await asyncio.sleep(jitter(8.0))
                    idx = (idx + 1) % len(el)
            finally:
                self.current_emoji = ""
                try: await self._patch_custom_status()
                except Exception: pass

        self._emoji_rotation_task = asyncio.create_task(_loop())
        await ctx.message.edit(content=S.ui_ok(f"emoji rotation → {len(el)} emojis"))

    @commands.command(name="stopstatus", brief="Stop status rotation")
    async def stopstatus(self, ctx):
        self.status_rotation_active = False
        if self._status_rotation_task and not self._status_rotation_task.done():
            self._status_rotation_task.cancel()
        await ctx.message.edit(content=S.ui_ok("status rotation stopped"))

    @commands.command(name="stopemoji", brief="Stop emoji rotation")
    async def stopemoji(self, ctx):
        self.emoji_rotation_active = False
        if self._emoji_rotation_task and not self._emoji_rotation_task.done():
            self._emoji_rotation_task.cancel()
        await ctx.message.edit(content=S.ui_ok("emoji rotation stopped"))

    # ── Watchdog command ──────────────────────────────────────────────────────
    @commands.command(name="rpcwatchdog", aliases=["rpcwd"], brief="Watchdog on/off/status")
    async def rpcwatchdog(self, ctx, sub: str = "status"):
        sub = sub.lower()
        if sub in ("stop","off"):
            if self._watchdog_task and not self._watchdog_task.done():
                self._watchdog_task.cancel(); self._watchdog_task = None
            await ctx.message.edit(content=S.ui_ok("rpc watchdog stopped"))
        elif sub in ("start","on"):
            if not self._watchdog_task or self._watchdog_task.done():
                self._watchdog_task = asyncio.create_task(self._watchdog_loop())
            await ctx.message.edit(content=S.ui_ok("rpc watchdog started"))
        else:
            running = bool(self._watchdog_task and not self._watchdog_task.done())
            since   = int(time.time()-self._last_push_ts) if self._last_push_ts else -1
            active  = sum(1 for s in self.rpc_slots if s is not None)
            lines   = [
                f"rpc watchdog: {'running' if running else 'stopped'}",
                f"cycles:       {self._watchdog_cycles}",
                f"last push:    {'never' if since<0 else f'{since}s ago'}",
                f"active slots: {active}/6",
            ]
            await ctx.message.edit(content=S._ansi_block(lines))

    # ── Quick preset commands ─────────────────────────────────────────────────
    @commands.command(name="playing", brief="Playing <name>")
    async def playing(self, ctx, *, name: str = ""):
        self._ensure_slot(0); self.rpc_slots[0]["name"] = name; self.rpc_slots[0]["type"] = 0
        await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"playing → {name}"))

    @commands.command(name="watching", brief="Watching <name>")
    async def watching(self, ctx, *, name: str = ""):
        self._ensure_slot(0); self.rpc_slots[0]["name"] = name; self.rpc_slots[0]["type"] = 3
        await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"watching → {name}"))

    @commands.command(name="listening", brief="Listening <name>")
    async def listening(self, ctx, *, name: str = ""):
        self._ensure_slot(0); self.rpc_slots[0]["name"] = name; self.rpc_slots[0]["type"] = 2
        await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"listening → {name}"))

    @commands.command(name="competing", brief="Competing <name>")
    async def competing(self, ctx, *, name: str = ""):
        self._ensure_slot(0); self.rpc_slots[0]["name"] = name; self.rpc_slots[0]["type"] = 5
        await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"competing → {name}"))

    @commands.command(name="streaming", brief="Streaming <url> <name>")
    async def streaming(self, ctx, url: str = "", *, name: str = "Streaming"):
        self._ensure_slot(0)
        self.rpc_slots[0].update({"name": name, "type": 1, "url": url or "https://twitch.tv/x"})
        await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"streaming → {name}"))

    @commands.command(name="youtube", brief="YouTube RPC  youtube Video - Channel")
    async def youtube(self, ctx, *, args: str = ""):
        parts = [p.strip() for p in args.split("-") if p.strip()]
        act   = await self.build_youtube(parts or ["Video","YouTube"])
        if act: self.rpc_slots[0] = act; await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"YouTube → {(parts or ['Video'])[0]}") if act
                               else S.ui_err("format: youtube Video - Channel"))

    @commands.command(name="spotify", brief="Spotify RPC  spotify Song - Artist")
    async def spotify(self, ctx, *, args: str = ""):
        parts = [p.strip() for p in args.split("-") if p.strip()]
        act   = await self.build_spotify(parts or ["Song","Artist"])
        if act: self.rpc_slots[0] = act; await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"Spotify → {(parts or ['Song'])[0]}") if act
                               else S.ui_err("format: spotify Song - Artist"))

    @commands.command(name="xbox", brief="Xbox RPC  xbox Game")
    async def xbox(self, ctx, *, args: str = "Xbox"):
        parts = [p.strip() for p in args.split("-") if p.strip()]
        self.rpc_slots[0] = await self.build_xbox(parts or ["Xbox"])
        await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"Xbox → {parts[0] if parts else 'Xbox'}"))

    @commands.command(name="ps", aliases=["ps5"], brief="PS5 RPC  ps Game")
    async def ps(self, ctx, *, args: str = "PlayStation"):
        parts = [p.strip() for p in args.split("-") if p.strip()]
        self.rpc_slots[0] = await self.build_playstation(parts or ["PlayStation"])
        await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"PS5 → {parts[0] if parts else 'PlayStation'}"))

    @commands.command(name="ps4", brief="PS4 RPC  ps4 Game")
    async def ps4(self, ctx, *, args: str = "PlayStation 4"):
        parts = [p.strip() for p in args.split("-") if p.strip()]
        self.rpc_slots[0] = await self.build_playstation(parts or ["PlayStation 4"], ps4=True)
        await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"PS4 → {parts[0] if parts else 'PS4'}"))

    @commands.command(name="crunchy", aliases=["crunchyroll"], brief="Crunchyroll RPC  crunchy Anime - Episode")
    async def crunchy(self, ctx, *, args: str = ""):
        parts = [p.strip() for p in args.split("-") if p.strip()]
        self.rpc_slots[0] = await self.build_crunchyroll(parts or ["Anime","Episode 1"])
        await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"Crunchyroll → {parts[0] if parts else 'Anime'}"))

    @commands.command(name="vrchat", brief="VRChat RPC  vrchat World - State")
    async def vrchat(self, ctx, *, args: str = ""):
        parts = [p.strip() for p in args.split("-") if p.strip()]
        self.rpc_slots[0] = await self.build_vrchat(parts or ["Exploring VRChat","VRChat"])
        await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"VRChat → {parts[0] if parts else 'VRChat'}"))

    @commands.command(name="roblox", brief="Roblox RPC  roblox Game")
    async def roblox(self, ctx, *, args: str = "Roblox"):
        parts = [p.strip() for p in args.split("-") if p.strip()]
        self.rpc_slots[0] = await self.build_roblox(parts or ["Roblox"])
        await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"Roblox → {parts[0] if parts else 'Roblox'}"))

    @commands.command(name="meta", aliases=["metaquest","oculus"], brief="Meta Quest RPC")
    async def meta(self, ctx, *, args: str = ""):
        parts = [p.strip() for p in args.split("-") if p.strip()]
        self.rpc_slots[0] = await self.build_vrchat(parts or ["Exploring","Meta Quest"])
        await self.apply_activities()
        await ctx.message.edit(content=S.ui_ok(f"Meta → {parts[0] if parts else 'Meta Quest'}"))

    # ── Builders ──────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_kwargs(parts: list) -> tuple:
        KWARG_KEYS = {"dur","pos","elapsed","total","img","small","btn","type",
                      "details","state","album","name"}
        positional, kwargs = [], {}
        for part in parts:
            p = part.strip(); c = p.find(":")
            if c > 0 and p[:c].lower() in KWARG_KEYS:
                kwargs[p[:c].lower()] = p[c+1:].strip()
            else:
                positional.append(p)
        return positional, kwargs

    @staticmethod
    def _parse_btn(s: str) -> dict:
        if "|" in s:
            label, url = s.split("|", 1)
            return {"label": label.strip()[:32], "url": url.strip()}
        return {"label": "Open", "url": s.strip()}

    async def build_spotify(self, parts: list):
        """spotify Song - Artist - Album - dur:4.2 - pos:1.0 - img:URL - btn:Listen|URL"""
        pos, kw = self._parse_kwargs(parts)
        if not pos: return None
        song   = pos[0]; artist = pos[1] if len(pos)>1 else "Unknown Artist"
        album  = kw.get("album") or (pos[2] if len(pos)>2 else song)
        dur    = float(kw.get("dur", pos[3] if len(pos)>3 else "3.5"))
        posv   = float(kw.get("pos", pos[4] if len(pos)>4 else "0.0"))
        sid    = "09xhawlPUifhftf8zuie7w"
        now    = int(time.time() * 1000)
        cur_ms = int(posv * 60 * 1000); tot_ms = int(dur * 60 * 1000)

        lg = await self._fetch_app_icon("3201606009684", "spotify") or "spotify"
        if kw.get("img"):
            k = await self.upload_asset(kw["img"])
            if k: lg = k

        assets = {"large_image": lg, "large_text": f"{album} on Spotify"}
        if kw.get("small"):
            sk = await self.upload_asset(kw["small"]) if kw["small"].startswith("http") else kw["small"]
            if sk: assets["small_image"] = sk; assets["small_text"] = "Spotify"

        act = {
            "type": 2, "name": "Spotify", "details": song[:128], "state": artist[:128],
            "timestamps": {"start": now - cur_ms, "end": (now - cur_ms) + tot_ms},
            "application_id": "3201606009684", "sync_id": sid,
            "session_id": f"spotify:{sid}",
            "party":   {"id": f"spotify:{sid}", "size": [1,1]},
            "secrets": {"join": f"spotify:{sid}", "spectate": f"spotify:{sid}",
                        "match": f"spotify:{sid}"},
            "flags": 48, "instance": True,
            "metadata": {"context_uri": f"spotify:album:{sid}", "album_id": sid,
                         "artist_ids": ["0HPG2EIdGCP6gjXW0KzrJq"], "track_id": sid},
            "assets": assets,
        }
        if kw.get("btn"): act["buttons"] = [self._parse_btn(kw["btn"])]
        return act

    async def build_youtube(self, parts: list):
        """youtube Video - Channel - dur:8.5 - pos:2.0 - img:URL - type:watching"""
        pos, kw = self._parse_kwargs(parts)
        if not pos: return None
        video   = pos[0]
        channel = kw.get("state") or (pos[1] if len(pos)>1 else "YouTube")
        dur     = float(kw.get("dur", pos[2] if len(pos)>2 else "5.0"))
        posv    = float(kw.get("pos", pos[3] if len(pos)>3 else "0.0"))
        t       = TYPE_MAP.get(kw.get("type","watching").lower(), 3)
        now     = int(time.time() * 1000)
        cur_ms  = int(posv * 60 * 1000); tot_ms = int(dur * 60 * 1000)

        lg = await self._fetch_app_icon("111299001912", "youtube") or "youtube"
        if kw.get("img"):
            k = await self.upload_asset(kw["img"])
            if k: lg = k

        assets = {"large_image": lg, "large_text": f"{video} on YouTube"}
        if kw.get("small"):
            sk = await self.upload_asset(kw["small"]) if kw["small"].startswith("http") else kw["small"]
            if sk: assets["small_image"] = sk; assets["small_text"] = channel[:128]

        act = {
            "type": t, "name": "YouTube", "details": video[:128], "state": channel[:128],
            "timestamps": {"start": now - cur_ms, "end": (now - cur_ms) + tot_ms},
            "application_id": "111299001912", "assets": assets,
        }
        if kw.get("btn"): act["buttons"] = [self._parse_btn(kw["btn"])]
        return act

    async def build_xbox(self, parts: list):
        """xbox Game - details:Achievement - state:Online - img:URL - btn:Label|URL"""
        pos, kw = self._parse_kwargs(parts)
        game    = (pos[0] if pos else "Xbox")[:128]
        lg      = await self._fetch_app_icon("622174530214821906", "xbox") or "xbox"
        if kw.get("img"):
            k = await self.upload_asset(kw["img"])
            if k: lg = k

        assets = {"large_image": lg, "large_text": game[:32]}
        if kw.get("small"):
            sk = await self.upload_asset(kw["small"]) if kw["small"].startswith("http") else kw["small"]
            if sk: assets["small_image"] = sk; assets["small_text"] = "Xbox"

        act = {
            "type": 0, "name": game, "application_id": "622174530214821906",
            "platform": "xbox",
            "timestamps": {"start": int(time.time() * 1000)}, "assets": assets,
        }
        if kw.get("details") or len(pos)>1: act["details"] = (kw.get("details") or pos[1])[:128]
        if kw.get("state")   or len(pos)>2: act["state"]   = (kw.get("state")   or pos[2])[:128]
        if kw.get("btn"): act["buttons"] = [self._parse_btn(kw["btn"])]
        return act

    async def build_playstation(self, parts: list, ps4: bool = False):
        """ps Game - details:Trophy - state:Online - img:URL - btn:Label|URL"""
        pos, kw = self._parse_kwargs(parts)
        game    = (pos[0] if pos else "PlayStation")[:128]
        plat    = "ps4" if ps4 else "ps5"
        label   = "PS4"  if ps4 else "PS5"
        lg      = await self._fetch_app_icon("1470539864909943067", "playstation") or "playstation"
        if kw.get("img"):
            k = await self.upload_asset(kw["img"])
            if k: lg = k

        assets = {"large_image": lg, "large_text": game[:32]}
        if kw.get("small"):
            sk = await self.upload_asset(kw["small"]) if kw["small"].startswith("http") else kw["small"]
            if sk: assets["small_image"] = sk; assets["small_text"] = label

        act = {
            "type": 0, "name": game, "application_id": "1470539864909943067",
            "platform": plat,
            "timestamps": {"start": int(time.time() * 1000)}, "assets": assets,
        }
        if kw.get("details") or len(pos)>1: act["details"] = (kw.get("details") or pos[1])[:128]
        if kw.get("state")   or len(pos)>2: act["state"]   = (kw.get("state")   or pos[2])[:128]
        if kw.get("btn"): act["buttons"] = [self._parse_btn(kw["btn"])]
        return act

    async def build_crunchyroll(self, parts: list):
        """crunchy Anime - Episode - elapsed:10 - total:24 - img:URL - btn:Watch|URL"""
        pos, kw  = self._parse_kwargs(parts)
        anime    = (pos[0] if pos else "Anime")[:128]
        episode  = (pos[1] if len(pos)>1 else "Episode 1")[:128]
        elapsed  = float(kw.get("elapsed", kw.get("pos", pos[2] if len(pos)>2 else "0.0")))
        total    = float(kw.get("total",   kw.get("dur", pos[3] if len(pos)>3 else "24.0")))
        now      = int(time.time() * 1000)
        cur_ms   = int(elapsed * 60 * 1000); tot_ms = int(total * 60 * 1000)
        lg       = await self._fetch_app_icon("981509069309354054", "crunchyroll") or "crunchyroll"
        if kw.get("img"):
            k = await self.upload_asset(kw["img"])
            if k: lg = k

        assets = {"large_image": lg, "large_text": anime[:32]}
        if kw.get("small"):
            sk = await self.upload_asset(kw["small"]) if kw["small"].startswith("http") else kw["small"]
            if sk: assets["small_image"] = sk; assets["small_text"] = episode[:32]

        act = {
            "type": 3, "name": "Crunchyroll", "application_id": "981509069309354054",
            "details": anime, "state": episode,
            "timestamps": {"start": now - cur_ms, "end": (now - cur_ms) + tot_ms},
            "assets": assets,
        }
        if kw.get("btn"): act["buttons"] = [self._parse_btn(kw["btn"])]
        return act

    async def build_vrchat(self, parts: list, image_url: str = None):
        """vrchat World - state:With friends - img:URL - btn:Label|URL"""
        pos, kw  = self._parse_kwargs(parts)
        state    = kw.get("state") or (pos[0] if pos else "Exploring VRChat")
        world    = pos[1] if len(pos)>1 else "VRChat"
        img_url  = image_url or kw.get("img")
        lg       = await self._fetch_app_icon("1498387526501535835", "vrchat") or "vrchat"
        if img_url:
            k = await self.upload_asset(img_url)
            if k: lg = k

        assets = {"large_image": lg, "large_text": world[:128]}
        if kw.get("small"):
            sk = await self.upload_asset(kw["small"]) if kw["small"].startswith("http") else kw["small"]
            if sk: assets["small_image"] = sk; assets["small_text"] = state[:32]

        act = {
            "type": 0, "name": "VRChat", "application_id": "1498387526501535835",
            "platform": "meta_quest", "state": state[:128],
            "timestamps": {"start": int(time.time() * 1000)},
            "assets": assets, "instance": True,
        }
        if kw.get("btn"): act["buttons"] = [self._parse_btn(kw["btn"])]
        return act

    async def build_roblox(self, parts: list):
        """roblox Game - state:With friends - img:URL - btn:Play|URL"""
        pos, kw = self._parse_kwargs(parts)
        game    = (pos[0] if pos else "Roblox")[:128]
        # Try fetching the real Roblox Discord app icon (renders reliably)
        lg = await self._fetch_app_icon("1552026905023356938", "roblox") or "roblox"
        if kw.get("img"):
            k = await self.upload_asset(kw["img"])
            if k: lg = k

        assets = {"large_image": lg, "large_text": game[:128]}
        if kw.get("small"):
            sk = await self.upload_asset(kw["small"]) if kw["small"].startswith("http") else None
            if sk: assets["small_image"] = sk; assets["small_text"] = game[:32]

        act = {
            "type": 0, "name": "Roblox", "application_id": "1552026905023356938",
            "details": game, "timestamps": {"start": int(time.time() * 1000)},
            "assets": assets, "instance": True,
        }
        if kw.get("state") or len(pos)>1: act["state"] = (kw.get("state") or pos[1])[:128]
        if kw.get("btn"): act["buttons"] = [self._parse_btn(kw["btn"])]
        return act


async def setup(bot):
    await bot.add_cog(RPCCog(bot))

# cogs/quests.py | Quest auto-completer — auto-enroll, auto-progress, auto-claim
import asyncio
import logging
import json
import json as _json   # alias: survives parameter shadowing in transport methods
import random
import math
import time
import os
import traceback
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from . import state as S
from .antid import jitter, delay, rand_interval
from typing import Optional, Any

logger = logging.getLogger(__name__)

# ── Optional fork transport ───────────────────────────────────────────────────
try:
    from modifyself.http.client import HTTPClient as _ForkHTTP
    from modifyself.http.route  import Route       as _ForkRoute
    from modifyself.headers     import HeaderSpoofer, EMULATION
    HAS_FORK_HTTP = True
except Exception as _e:
    print(f"[quest] fork HTTP unavailable ({_e}) — falling back to aiohttp")
    _ForkHTTP = _ForkRoute = HeaderSpoofer = EMULATION = None
    HAS_FORK_HTTP = False

# ── Token resolution ──────────────────────────────────────────────────────────
def _resolve_token(bot):
    for attr in ("http.token","_http.token","token"):
        try:
            obj = bot
            for part in attr.split("."):
                obj = getattr(obj, part)
            if obj:
                return str(obj).strip().strip('"\'')
        except Exception:
            pass
    return None

# ── Fork transport ────────────────────────────────────────────────────────────
class _ForkTransport:
    def __init__(self, token):
        self._token   = token
        self._spoofer = HeaderSpoofer(token, EMULATION)
        self._client  = _ForkHTTP(token, headers=self._spoofer)

    async def request(self, method, url, headers=None, payload=None, params=None):
        path = url
        for prefix in ("https://discord.com/api/v10",
                       "https://discord.com/api/v9",
                       "https://discord.com/api",
                       "https://discord.com"):
            if path.startswith(prefix):
                path = path[len(prefix):]
                break
        if not path.startswith("/"): path = "/" + path
        route = _ForkRoute(method.upper(), path)
        for attempt in range(3):
            try:
                call = self._client.request(route, json=payload,
                                             **({"params": params} if params else {}))
                if asyncio.iscoroutine(call): call = await call
                body = call if isinstance(call, dict) else {}
                if isinstance(call, list): body = {"quests": call}
                return 200, body
            except Exception as e:
                status = (getattr(e, "status", None)
                          or getattr(getattr(e, "response", None), "status", None))
                if status:
                    return int(status), {"error": str(e)}
                await asyncio.sleep(0.5 * (attempt + 1))
        return 0, {}

    async def close(self):
        try: await self._client.close()
        except Exception: pass

# ── aiohttp fallback transport ────────────────────────────────────────────────
class _AiohttpTransport:
    def __init__(self, token):
        self._token   = token
        self._session = None

    def _headers(self):
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "discord/1.0.9191 Chrome/134.0.6998.179 "
                "Electron/35.1.5 Safari/537.36"
            ),
            "Accept":          "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type":    "application/json",
            "Authorization":   self._token,
        }

    async def _ensure(self):
        if self._session is None or self._session.closed:
            import aiohttp
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30, connect=10))

    async def request(self, method, url, headers=None, payload=None, params=None):
        await self._ensure()
        import aiohttp
        merged = {**self._headers(), **(headers or {})}
        try:
            async with self._session.request(
                    method, url, headers=merged, json=payload, params=params) as r:
                text = await r.text()
                try: body = _json.loads(text)
                except Exception: body = {}
                return r.status, body
        except Exception as e:
            logger.error(f"[quest] aiohttp request failed: {e}")
            return 0, {}

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


async def _make_transport(token):
    if HAS_FORK_HTTP:
        try:
            return _ForkTransport(token)
        except Exception as e:
            print(f"[quest] fork transport init failed: {e} — using aiohttp")
    return _AiohttpTransport(token)


# ── Quest model ───────────────────────────────────────────────────────────────
class Quest:
    def __init__(self, id, title, description, task_type, status=None):
        self.id           = id
        self.title        = title
        self.description  = description
        self.task_type    = task_type
        self.status       = status
        self.enrolled_at  = None
        self.completed_at = None
        self.progress     = 0.0
        self.target       = 0.0
        self.expires_at   = None
        self.starts_at    = None
        self.is_expired   = False
        self.last_updated = time.time()

    def is_supported(self):
        t = (self.task_type or "").lower()
        if self.is_expired: return False
        if "watch" in t and "video" in t: return True
        if "play"  in t: return True
        if "stream" in t: return True
        return False

    def check_expiration(self):
        if not self.expires_at: return False
        try:
            exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            self.is_expired = datetime.now(exp.tzinfo) > exp
            return self.is_expired
        except Exception: return False

    def to_dict(self):
        return {k: getattr(self, k) for k in (
            "id","title","description","task_type","status","enrolled_at",
            "completed_at","progress","target","expires_at","starts_at",
            "is_expired","last_updated")}

    @classmethod
    def from_dict(cls, d):
        q = cls(d["id"], d["title"], d["description"], d["task_type"], d.get("status"))
        for k in ("enrolled_at","completed_at","expires_at","starts_at","is_expired","last_updated"):
            setattr(q, k, d.get(k))
        q.progress = d.get("progress", 0.0)
        q.target   = d.get("target",   0.0)
        return q


# ── Cog ───────────────────────────────────────────────────────────────────────
class QuestsCog(commands.Cog, name="quests"):
    """Quest auto-completer — fetch, auto-enroll, progress, claim."""

    def __init__(self, bot):
        self.bot               = bot
        self.quests:     dict  = {}
        self.auto_complete     = False
        self.last_fetch_time   = 0.0
        self.quest_completion_task = None
        self.cache:      dict  = {}
        self.refresh_interval  = 30 * 60
        self.excluded_quests:  set  = set()
        self.data_file         = "quest_data.json"
        self._last_save_ts     = 0.0
        self._save_min_interval= 5.0
        self._transport        = None
        self._transport_lock   = asyncio.Lock()
        self._load_quests()

    # ── Persistence ───────────────────────────────────────────────────────────
    def _load_quests(self):
        try:
            if not os.path.exists(self.data_file): return
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for qd in data.get("quests", []):
                try:
                    q = Quest.from_dict(qd)
                    self.quests[q.id] = q
                except Exception as e:
                    logger.warning(f"[quest] skipping malformed entry: {e}")
            self.excluded_quests = set(data.get("excluded_quests", []))
            self.cache = data.get("cache", {})
        except Exception as e:
            logger.error(f"[quest] load error: {e}")

    def _save_quests(self, force=False):
        now = time.time()
        if not force and now - self._last_save_ts < self._save_min_interval:
            return
        try:
            data = {
                "quests":          [q.to_dict() for q in self.quests.values()],
                "excluded_quests": list(self.excluded_quests),
                "cache":           self.cache,
            }
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            self._last_save_ts = now
        except Exception as e:
            logger.error(f"[quest] save error: {e}")

    # ── Transport ─────────────────────────────────────────────────────────────
    async def _get_transport(self):
        if self._transport is not None: return self._transport
        async with self._transport_lock:
            if self._transport is not None: return self._transport
            token = S.TOKEN or _resolve_token(self.bot)
            if not token:
                logger.error("[quest] no token — cannot build transport")
                return None
            self._transport = await _make_transport(token)
            return self._transport

    async def cog_unload(self):
        self.auto_complete = False
        if self.quest_completion_task and not self.quest_completion_task.done():
            self.quest_completion_task.cancel()
            try: await self.quest_completion_task
            except asyncio.CancelledError: pass
        if self._transport:
            try: await self._transport.close()
            except Exception: pass
            self._transport = None
        self._save_quests(force=True)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _task_type(self, config) -> str:
        def _check(tasks):
            tl = {k.upper(): v for k, v in tasks.items()}
            if "WATCH_VIDEO" in tl or "WATCH_VIDEO_ON_MOBILE" in tl:
                return "WatchVideo"
            if ("PLAY_ON_DESKTOP" in tl or "PLAY_ON_DESKTOP_V2" in tl
                    or "PLAY_ACTIVITY" in tl or "STREAM_ON_DESKTOP" in tl):
                return "PlayOnDesktop"
            # Check task TYPE field inside each task
            for v in tasks.values():
                if isinstance(v, dict):
                    t = str(v.get("type", "") or v.get("task_type", "")).upper()
                    if "WATCH" in t and "VIDEO" in t: return "WatchVideo"
                    if "PLAY" in t or "STREAM" in t:  return "PlayOnDesktop"
            return ""

        # Try both v2 and v1 configs
        for key in ("task_config_v2", "task_config"):
            cfg_block = config.get(key) or {}
            tasks = cfg_block.get("tasks") or {}
            if not isinstance(tasks, dict):
                # Sometimes tasks is a list
                if isinstance(tasks, list):
                    tasks = {str(i): t for i, t in enumerate(tasks)}
            t = _check(tasks)
            if t: return t

        # Feature flag fallback
        fmap = {3: "WatchVideo", 4: "PlayOnDesktop"}
        for feat_id, name in fmap.items():
            if feat_id in config.get("features", []): return name

        # Last resort: check quest title/description for hints
        for key in ("messages",):
            msgs = config.get(key) or {}
            title = (msgs.get("quest_name") or msgs.get("game_title") or "").lower()
            if "watch" in title and ("video" in title or "youtube" in title):
                return "WatchVideo"
            if "play" in title or "game" in title or "stream" in title:
                return "PlayOnDesktop"

        logger.debug(f"[quest] Unknown task type for config keys: {list(config.keys())}")
        return "Unknown"

    def _extract_target(self, config, task_type) -> float:
        cands = {
            "WatchVideo":    ("WATCH_VIDEO", "WATCH_VIDEO_ON_MOBILE"),
            "PlayOnDesktop": ("PLAY_ON_DESKTOP", "PLAY_ON_DESKTOP_V2",
                              "PLAY_ACTIVITY", "STREAM_ON_DESKTOP"),
        }.get(task_type, ())
        for key in ("task_config_v2", "task_config"):
            tasks = (config.get(key) or {}).get("tasks", {})
            for c in cands:
                if c in tasks:
                    try: return float(tasks[c].get("target", 0) or 0)
                    except Exception: pass
        return 0.0

    def _extract_progress(self, progress_data, task_type) -> Optional[float]:
        if not isinstance(progress_data, dict) or not progress_data: return None
        cands = {
            "WatchVideo":    ("WATCH_VIDEO","WATCH_VIDEO_ON_MOBILE",
                              "watch_video","watch_video_on_mobile"),
            "PlayOnDesktop": ("PLAY_ON_DESKTOP","PLAY_ON_DESKTOP_V2",
                              "PLAY_ACTIVITY","STREAM_ON_DESKTOP",
                              "play_on_desktop","play_on_desktop_v2"),
        }.get(task_type, ())
        for key in cands:
            entry = progress_data.get(key)
            if isinstance(entry, dict) and "value" in entry:
                try: return float(entry["value"])
                except Exception: pass
        return None

    # ── API calls ─────────────────────────────────────────────────────────────
    async def get_quests(self) -> bool:
        """Fetch all available quests from Discord, update local cache."""
        tr = await self._get_transport()
        if tr is None: return False
        status, data = await tr.request("GET", "https://discord.com/api/v9/quests/@me")
        if status != 200:
            logger.error(f"[quest] fetch failed: HTTP {status}")
            return False

        quest_list = (data.get("quests", []) if isinstance(data, dict) else
                      data if isinstance(data, list) else [])
        if isinstance(data, dict):
            for ex in data.get("excluded_quests", []):
                if isinstance(ex, dict) and "id" in ex:
                    self.excluded_quests.add(ex["id"])

        for qd in quest_list:
            if not isinstance(qd, dict): continue
            qid = qd.get("id")
            if not qid: continue
            cfg   = qd.get("config") or {}
            title = (((cfg.get("application") or {}).get("name"))
                     or ((cfg.get("messages") or {}).get("game_title"))
                     or "Unknown Quest")
            desc  = (cfg.get("messages") or {}).get("quest_name", "")
            ttype = self._task_type(cfg)
            target= self._extract_target(cfg, ttype)

            if qid in self.quests:
                q = self.quests[qid]
                q.title = title; q.description = desc
                q.task_type = ttype; q.target = target
                q.starts_at = cfg.get("starts_at"); q.expires_at = cfg.get("expires_at")
                q.last_updated = time.time()
            else:
                q = Quest(qid, title, desc, ttype)
                q.starts_at = cfg.get("starts_at"); q.expires_at = cfg.get("expires_at")
                q.target = target
                self.quests[qid] = q

            if q.expires_at: q.check_expiration()

            us = qd.get("user_status") or {}
            if us.get("completed_at"):
                q.status = "completed"; q.completed_at = us["completed_at"]
                self.cache.pop(qid, None)
            elif us.get("enrolled_at"):
                q.status = "enrolled"; q.enrolled_at = us["enrolled_at"]

            v = self._extract_progress(us.get("progress") or {}, ttype)
            if v is not None:
                q.progress = v; self.cache[qid] = v

        self._save_quests(force=True)
        self.last_fetch_time = time.time()
        logger.info(f"[quest] fetched {len(quest_list)} quests ({len(self.quests)} cached)")
        return True

    async def enroll_quest(self, quest_id) -> bool:
        """POST /quests/{quest_id}/enroll — enroll in a single quest."""
        q = self.quests.get(quest_id)
        if not q: return False
        if q.is_expired or q.status == "completed": return False
        if q.status == "enrolled": return True

        tr = await self._get_transport()
        if tr is None: return False

        url = f"https://discord.com/api/v9/quests/{quest_id}/enroll"
        status, body = await tr.request("POST", url, payload={})

        if status in (200, 201):
            q.status = "enrolled"
            q.enrolled_at = body.get("enrolled_at", "") if isinstance(body, dict) else ""
            self._save_quests()
            logger.info(f"[quest] enrolled: {q.title}")
            return True
        if status == 204:
            q.status = "enrolled"
            self._save_quests()
            return True
        if status == 400:
            msg = (body.get("message", "") if isinstance(body, dict) else "").lower()
            if "already" in msg or "enrolled" in msg:
                q.status = "enrolled"; return True
        logger.warning(f"[quest] enroll {quest_id} returned {status}: {body}")
        return False

    async def enroll_all_available(self) -> int:
        """
        Enroll in every non-expired, non-completed quest.
        Does NOT filter by is_supported() — let the API decide eligibility.
        Returns count of newly enrolled quests.
        """
        enrolled = 0
        for qid, q in list(self.quests.items()):
            if q.is_expired: continue
            if q.status in ("completed", "enrolled"): continue
            if qid in self.excluded_quests: continue
            logger.info(f"[quest] trying to enroll: {q.title} (type={q.task_type})")
            ok = await self.enroll_quest(qid)
            if ok:
                enrolled += 1
                logger.info(f"[quest] enrolled: {q.title}")
            await asyncio.sleep(jitter(0.8))   # gentle pacing
        return enrolled

    async def update_quest_progress(self, quest_id) -> bool:
        """Send one progress heartbeat for a single enrolled quest."""
        q = self.quests.get(quest_id)
        if not q or not q.is_supported() or q.status != "enrolled": return False

        tr = await self._get_transport()
        if tr is None: return False

        t  = q.task_type.lower()
        url, data = "", {}

        if "watch" in t and "video" in t:
            target   = q.target or 30.0
            last     = self.cache.get(quest_id, q.progress if q.progress > 0 else 0.0)
            new_prog = min(last + 30.0 + round(random.random() * 1e6) / 1e6, target)
            self.cache[quest_id] = new_prog
            data = {"timestamp": new_prog}
            url  = f"https://discord.com/api/v9/quests/{quest_id}/video-progress"

        elif "play" in t or "stream" in t or "activity" in t:
            data = {
                "stream_key":   f"call:{quest_id}:{random.randint(1,9)}",
                "terminal":     False,
                "broadcast_id": None,
            }
            url = f"https://discord.com/api/v9/quests/{quest_id}/heartbeat"

        if not url: return False

        status, resp = await tr.request("POST", url, payload=data)
        if status != 200:
            if status in (401, 404): self.excluded_quests.add(quest_id)
            return False

        resp = resp if isinstance(resp, dict) else {}
        if resp.get("completed_at"):
            q.status = "completed"; q.completed_at = resp["completed_at"]
            self.cache.pop(quest_id, None)
            logger.info(f"[quest] completed: {q.title}")

        v = self._extract_progress(resp.get("progress") or {}, q.task_type)
        if v is not None:
            q.progress = v
            if v > self.cache.get(quest_id, 0): self.cache[quest_id] = v

        self._save_quests()
        return True

    # ── Auto-completer loop ───────────────────────────────────────────────────
    async def _quest_completer(self):
        try:
            while self.auto_complete:
                try:
                    # Refresh if stale
                    if time.time() - self.last_fetch_time > self.refresh_interval:
                        await self.get_quests()

                    # Build candidate list — include ALL non-expired, non-completed
                    # (is_supported gates only progress updates, not enrollment)
                    candidates = [
                        qid for qid, q in self.quests.items()
                        if not q.is_expired and q.status != "completed"
                        and qid not in self.excluded_quests
                    ]

                    if not candidates:
                        # All done or nothing available
                        all_done = all(
                            q.is_expired or not q.is_supported() or q.status == "completed"
                            for q in self.quests.values()
                        )
                        if all_done and self.quests:
                            logger.info("[quest] all quests complete — stopping auto-completer")
                            self.auto_complete = False
                            break
                        await asyncio.sleep(jitter(50.0))
                        continue

                    # Auto-enroll any unenrolled candidates (regardless of type)
                    for qid in candidates:
                        q = self.quests[qid]
                        if q.status != "enrolled":
                            ok = await self.enroll_quest(qid)
                            if ok:
                                logger.info(f"[quest] loop enrolled: {q.title}")
                            await asyncio.sleep(jitter(0.8))

                    # Progress all enrolled quests
                    enrolled = [
                        qid for qid in candidates
                        if self.quests[qid].status == "enrolled"
                    ]
                    if not enrolled:
                        await asyncio.sleep(jitter(50.0))
                        continue

                    for qid in enrolled:
                        if not self.auto_complete: break
                        await self.update_quest_progress(qid)
                        await asyncio.sleep(2)

                    await asyncio.sleep(random.randint(45, 60))

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"[quest] completer iteration error: {e}")
                    await asyncio.sleep(30)

        except asyncio.CancelledError:
            logger.info("[quest] completer cancelled")
        finally:
            self.quest_completion_task = None

    def _start_completer(self) -> bool:
        if not self.auto_complete: return False
        if self.quest_completion_task and not self.quest_completion_task.done():
            return False
        self.quest_completion_task = asyncio.create_task(self._quest_completer())
        return True

    def _stop_completer(self) -> bool:
        self.auto_complete = False
        if self.quest_completion_task and not self.quest_completion_task.done():
            self.quest_completion_task.cancel()
            return True
        self.quest_completion_task = None
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Commands
    # ─────────────────────────────────────────────────────────────────────────

    @commands.command(name="quest", aliases=["questlist","ql"], brief="Show quest status")
    async def quest(self, ctx):
        try: await ctx.message.delete()
        except Exception: pass

        await self.get_quests()
        if not self.quests:
            return await ctx.channel.send(S.ui_warn("No quests found"))

        enrolled  = [q for q in self.quests.values() if q.status == "enrolled"  and not q.is_expired]
        available = [q for q in self.quests.values() if q.status not in ("enrolled","completed") and not q.is_expired and q.is_supported()]
        completed = [q for q in self.quests.values() if q.status == "completed"]

        NL = "\n"
        lines = [
            "Quest Status", "━━━━━━━━━━━━",
            f"  auto:      {'running' if self.auto_complete else 'stopped'}",
            f"  total:     {len(self.quests)}  enrolled: {len(enrolled)}  "
            f"available: {len(available)}  done: {len(completed)}", "",
        ]
        if enrolled:
            lines.append("In progress:")
            for q in enrolled:
                tgt = q.target or 30.0
                pct = min(100, int((q.progress / tgt) * 100)) if tgt else 0
                lines.append(f"  [{q.task_type}] {q.title}  {q.progress:.0f}/{tgt:.0f}s ({pct}%)")
            lines.append("")
        if available:
            lines.append("Available (not yet enrolled):")
            for q in available:
                lines.append(f"  [{q.task_type}] {q.title}")
            lines.append("")

        pfx = S.PREFIX
        lines.append(f"  {pfx}queststart  ·  {pfx}queststop  ·  {pfx}questrefresh")
        await ctx.channel.send("```\n" + NL.join(lines) + "\n```")

    @commands.command(name="queststart", aliases=["qs"], brief="Start quest auto-completer (auto-enrolls)")
    async def queststart(self, ctx):
        try: await ctx.message.delete()
        except Exception: pass

        if self.auto_complete and self.quest_completion_task and not self.quest_completion_task.done():
            return await ctx.channel.send(S.ui_warn("Auto-completer already running"))

        msg = await ctx.channel.send(S.ui_info("Fetching quests…"))

        # 1. Fetch latest quest data
        await self.get_quests()
        if not self.quests:
            return await msg.edit(content=S.ui_err("No quests found from API"))

        await msg.edit(content=S.ui_info(f"Found {len(self.quests)} quests — enrolling…"))

        # 2. Auto-enroll ALL (not filtered by task type)
        new_enrolled = await self.enroll_all_available()

        # 3. Count ALL enrolled quests (ignore is_supported for the count)
        enrolled = [q for q in self.quests.values()
                    if q.status == "enrolled" and not q.is_expired
                    and q.id not in self.excluded_quests]

        if not enrolled:
            types = set(q.task_type for q in self.quests.values())
            return await msg.edit(content=S.ui_warn(
                f"No enrolled quests — {len(self.quests)} fetched, "
                f"types: {', '.join(types) or 'none'}.  "
                f"Tried to enroll {new_enrolled}.  "
                f"Run .questdiag for token/transport info."))

        # 4. Start the auto-completer
        self.auto_complete = True
        self._start_completer()
        supported = [q for q in enrolled if q.is_supported()]
        await msg.edit(content=S.ui_ok(
            f"Auto-completer started — {len(enrolled)} enrolled "
            f"({len(supported)} supported types, {new_enrolled} newly enrolled)"))

    @commands.command(name="queststop", aliases=["qstop","qx"], brief="Stop quest auto-completer")
    async def queststop(self, ctx):
        try: await ctx.message.delete()
        except Exception: pass
        if not self.auto_complete:
            return await ctx.channel.send(S.ui_warn("Auto-completer not running"))
        self._stop_completer()
        await ctx.channel.send(S.ui_ok("Auto-completer stopped"))

    @commands.command(name="questrefresh", aliases=["qrefresh","qr"], brief="Refresh quest data")
    async def questrefresh(self, ctx):
        try: await ctx.message.delete()
        except Exception: pass
        m = await ctx.channel.send(S.ui_info("Refreshing…"))
        ok = await self.get_quests()
        try:
            await m.edit(content=S.ui_ok(f"Refreshed — {len(self.quests)} quests")
                         if ok else S.ui_err("Refresh failed"))
        except Exception:
            pass

    @commands.command(name="questall", brief="Enroll + progress all available quests once")
    async def questall(self, ctx):
        try: await ctx.message.delete()
        except Exception: pass
        m = await ctx.channel.send(S.ui_info("Fetching and enrolling all quests…"))

        # 1. Fetch
        await self.get_quests()

        # 2. Auto-enroll any unenrolled
        new_enrolled = await self.enroll_all_available()

        # 3. Progress all enrolled
        done = 0
        for qid, q in list(self.quests.items()):
            if q.status != "enrolled" or q.is_expired or not q.is_supported(): continue
            if qid in self.excluded_quests: continue
            ok = await self.update_quest_progress(qid)
            if ok: done += 1
            await asyncio.sleep(1)

        try:
            await m.edit(content=S.ui_ok(
                f"Done — {done} progressed · {new_enrolled} newly enrolled"))
        except Exception:
            pass

    @commands.command(name="questenroll", aliases=["qenroll"], brief="Enroll in all available quests")
    async def questenroll(self, ctx):
        try: await ctx.message.delete()
        except Exception: pass
        m = await ctx.channel.send(S.ui_info("Fetching and enrolling…"))
        await self.get_quests()
        n = await self.enroll_all_available()
        try:
            await m.edit(content=S.ui_ok(f"Enrolled in {n} quest(s)"))
        except Exception:
            pass

    @commands.command(name="autoquest", brief="Toggle autoquest  autoquest [on|off]")
    async def autoquest(self, ctx, toggle: str = ""):
        cfg     = S.load_config()
        current = cfg.get("autoquest_enabled", False)
        new_val = (toggle.lower() in ("on","enable","true")) if toggle else not current
        cfg["autoquest_enabled"] = new_val
        S.save_config(cfg)
        await ctx.message.edit(content=S.ui_ok(f"autoquest → {'enabled' if new_val else 'disabled'}"))
        if new_val and (not self.quest_completion_task or self.quest_completion_task.done()):
            self.auto_complete = True
            self._start_completer()

    @commands.command(name="autoclaim", brief="Toggle auto-claim  autoclaim [on|off]")
    async def autoclaim(self, ctx, toggle: str = ""):
        cfg     = S.load_config()
        current = cfg.get("autoclaim_enabled", False)
        new_val = (toggle.lower() in ("on","enable","true")) if toggle else not current
        cfg["autoclaim_enabled"] = new_val
        S.save_config(cfg)
        await ctx.message.edit(content=S.ui_ok(f"autoclaim → {'enabled' if new_val else 'disabled'}"))

    @commands.command(name="questdiag", aliases=["qdiag"], brief="Quest diagnostics")
    async def questdiag(self, ctx):
        try: await ctx.message.delete()
        except Exception: pass
        NL = "\n"
        enrolled  = sum(1 for q in self.quests.values() if q.status == "enrolled")
        completed = sum(1 for q in self.quests.values() if q.status == "completed")
        available = sum(1 for q in self.quests.values()
                        if q.status not in ("enrolled","completed") and not q.is_expired and q.is_supported())
        since = int(time.time() - self.last_fetch_time) if self.last_fetch_time else -1
        lines = [
            "Quest Diagnostics", "━━━━━━━━━━━━━━━━━",
            f"  token:     {'set' if S.TOKEN else 'MISSING'}",
            f"  transport: {'active' if self._transport else 'not initialised'}",
            f"  auto:      {'running' if self.auto_complete else 'idle'}",
            f"  task:      {'alive' if self.quest_completion_task and not self.quest_completion_task.done() else 'done/none'}",
            f"  total:     {len(self.quests)} cached",
            f"  enrolled:  {enrolled}  available: {available}  done: {completed}",
            f"  excluded:  {len(self.excluded_quests)}",
            f"  last fetch: {since}s ago" if since >= 0 else "  last fetch: never",
        ]
        await ctx.channel.send("```\n" + NL.join(lines) + "\n```")

    @commands.command(name="questdump", aliases=["qdump"], brief="Dump quest by index  questdump [n]")
    async def questdump(self, ctx, idx: int = 1):
        try: await ctx.message.delete()
        except Exception: pass
        if not self.quests:
            return await ctx.channel.send(S.ui_warn("No quests cached"))
        ql  = list(self.quests.values())
        i   = max(0, min(idx - 1, len(ql) - 1))
        q   = ql[i]; tgt = q.target or 0
        pct = min(100, int((q.progress / tgt) * 100)) if tgt else 0
        NL  = "\n"
        lines = [
            f"Quest {i+1}/{len(ql)}: {q.title}",
            f"  id:        {q.id}",
            f"  type:      {q.task_type}",
            f"  status:    {q.status}",
            f"  progress:  {q.progress:.0f}/{tgt:.0f}s ({pct}%)",
            f"  expired:   {q.is_expired}",
            f"  supported: {q.is_supported()}",
        ]
        await ctx.channel.send("```\n" + NL.join(lines) + "\n```")

    @commands.command(name="spdecode", brief="Decode super-properties base64")
    async def spdecode(self, ctx, b64: str = ""):
        if not b64:
            return await ctx.message.edit(content=S.ui_err("usage: spdecode <base64>"))
        import base64 as _b64
        try:
            raw = _b64.b64decode(b64 + "=" * (-len(b64) % 4)).decode("utf-8")
            obj = _json.loads(raw)
            NL  = "\n"
            lines = ["Super Properties", "━━━━━━━━━━━━━━━━"]
            for k, v in obj.items():
                lines.append(f"  {k}: {v}")
            await ctx.message.edit(content="```\n" + NL.join(lines) + "\n```")
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(f"decode failed: {e}"))

    @commands.command(name="orbbadge", brief="Claim orb badge from quests")
    async def orbbadge(self, ctx):
        try: await ctx.message.delete()
        except Exception: pass
        tr = await self._get_transport()
        if not tr:
            return await ctx.channel.send(S.ui_err("transport unavailable"))
        # POST the orb badge claim endpoint
        try:
            status, body = await tr.request(
                "POST",
                "https://discord.com/api/v9/users/@me/quests/claim-orb-badge",
                payload={}
            )
            if status in (200, 201, 204):
                await ctx.channel.send(S.ui_ok("orb badge claimed ✓"))
            elif status == 400:
                msg = (body.get("message","") if isinstance(body,dict) else "").lower()
                await ctx.channel.send(S.ui_warn(f"not eligible: {msg or 'already claimed or unavailable'}"))
            else:
                await ctx.channel.send(S.ui_err(f"failed ({status}): {body}"))
        except Exception as e:
            await ctx.channel.send(S.ui_err(str(e)))

    @commands.command(name="qtransport", aliases=["qt"], brief="Quest transport diagnostics")
    async def qtransport(self, ctx):
        tr = self._transport
        await ctx.channel.send(S.ui_box("quest transport", [
            f"  {S.DIM}type{S.RESET}      {type(tr).__name__ if tr else 'None'}",
            f"  {S.DIM}quests{S.RESET}    {len(self.quests)}",
            f"  {S.DIM}auto{S.RESET}      {self.auto_complete}",
            f"  {S.DIM}excluded{S.RESET}  {len(self.excluded_quests)}",
        ]))


async def setup(bot):
    await bot.add_cog(QuestsCog(bot))

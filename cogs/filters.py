# cogs/filters.py | full filter suite — all original commands restored
import time, re, asyncio, aiohttp, discord
from discord.ext import commands
from . import state as S
import aiohttp
import asyncio
import re

URL_RE    = re.compile(r"https?://\S+")
INVITE_RE = re.compile(r"(discord\.gg|discord\.com/invite|discordapp\.com/invite)/\S+")
SCAM_RE   = re.compile(r"(free\s*nitro|steamcommunity\.(com|ru)|gift\s*claim|free\s*gift)", re.I)

class FiltersCog(commands.Cog, name="filters"):
    """Spam/link/invite/scam/nsfw/attachment/mention/bot/webhook/dupe filters."""
    def __init__(self, bot):
        self.bot = bot
        self._msg_history: dict = {}

    # ── Toggle helpers ────────────────────────────────────────────────────────
    def _toggle(self, key: str, on: bool):
        if key in S.filters and isinstance(S.filters[key], dict):
            S.filters[key]["enabled"] = on

    @commands.group(name="filter", aliases=["filters"], invoke_without_command=True, brief="Filter status")
    async def filter_cmd(self, ctx):
        rows = [f"  {S.GREY}•{S.RESET} {k:<14} {'ON' if v.get('enabled') else 'off'}"
                for k, v in S.filters.items() if isinstance(v, dict) and "enabled" in v]
        await ctx.message.edit(content=S.ui_box("filters", rows))

    @filter_cmd.command(name="on")
    async def filter_on(self, ctx, kind: str = ""):
        if kind and kind in S.filters:
            self._toggle(kind, True)
            await ctx.message.edit(content=S.ui_ok(f"{kind} on"))
        else:
            for k in S.filters:
                if isinstance(S.filters[k], dict): self._toggle(k, True)
            await ctx.message.edit(content=S.ui_ok("all filters on"))

    @filter_cmd.command(name="off")
    async def filter_off(self, ctx, kind: str = ""):
        if kind and kind in S.filters:
            self._toggle(kind, False)
            await ctx.message.edit(content=S.ui_ok(f"{kind} off"))
        else:
            for k in S.filters:
                if isinstance(S.filters[k], dict): self._toggle(k, False)
            await ctx.message.edit(content=S.ui_ok("all filters off"))

    @filter_cmd.command(name="log")
    async def filter_log(self, ctx, channel: discord.TextChannel = None):
        S.filters["log_channel"] = channel.id if channel else None
        await ctx.message.edit(content=S.ui_ok(f"filter log → {channel or 'none'}"))

    @filter_cmd.command(name="clear")
    async def filter_clear(self, ctx):
        S.filters.get("actions_log", []).clear() if isinstance(S.filters.get("actions_log"), list) else None
        S.filters["actions_log"] = []
        await ctx.message.edit(content=S.ui_ok("filter log cleared"))

    # ── Individual toggle commands ────────────────────────────────────────────
    def _make_toggle(name, key, field=None):
        async def cmd(self, ctx, toggle: str = ""):
            target = S.filters.get(key, {}) if field is None else S.filters.get(key, {})
            on = toggle.lower() not in ("off","disable","false") if toggle else not target.get("enabled", False)
            target["enabled"] = on
            await ctx.message.edit(content=S.ui_ok(f"{name} → {'on' if on else 'off'}"))
        cmd.__name__ = f"_{name}"
        return cmd

    @commands.command(name="antispam", brief="Toggle spam filter  [on/off] [threshold]")
    async def antispam(self, ctx, arg: str = ""):
        if arg.isdigit():
            S.filters["spam"]["threshold"] = int(arg)
            return await ctx.message.edit(content=S.ui_ok(f"spam threshold → {arg}"))
        on = arg.lower() not in ("off","disable") if arg else not S.filters["spam"]["enabled"]
        S.filters["spam"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"antispam → {'on' if on else 'off'}"))

    @commands.command(name="antidupe", brief="Toggle duplicate filter")
    async def antidupe(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.filters["duplicate"]["enabled"]
        S.filters["duplicate"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"antidupe → {'on' if on else 'off'}"))

    @commands.command(name="antilink", brief="Toggle link filter  antilink add <domain> to whitelist")
    async def antilink(self, ctx, arg: str = "", domain: str = ""):
        if arg.lower() == "add" and domain:
            S.filters["link"].setdefault("whitelist", set()).add(domain)
            return await ctx.message.edit(content=S.ui_ok(f"whitelisted {domain}"))
        on = arg.lower() not in ("off","disable") if arg else not S.filters["link"]["enabled"]
        S.filters["link"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"antilink → {'on' if on else 'off'}"))

    @commands.command(name="antiinvite", brief="Toggle invite filter")
    async def antiinvite(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.filters["invite"]["enabled"]
        S.filters["invite"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"antiinvite → {'on' if on else 'off'}"))

    @commands.command(name="antiattachment", brief="Toggle attachment filter")
    async def antiattachment(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.filters["attachment"]["enabled"]
        S.filters["attachment"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"antiattachment → {'on' if on else 'off'}"))

    @commands.command(name="antinsfw", brief="Toggle NSFW keyword filter  antinsfw add <word>")
    async def antinsfw(self, ctx, arg: str = "", *, word: str = ""):
        if arg.lower() == "add" and word:
            S.filters["nsfw"].setdefault("keywords", set()).add(word.lower())
            return await ctx.message.edit(content=S.ui_ok(f"nsfw keyword added: {word}"))
        on = arg.lower() not in ("off","disable") if arg else not S.filters["nsfw"]["enabled"]
        S.filters["nsfw"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"antinsfw → {'on' if on else 'off'}"))

    @commands.command(name="antimention", brief="Toggle mention spam filter  [threshold]")
    async def antimention(self, ctx, arg: str = ""):
        if arg.isdigit():
            S.filters["mention_spam"]["threshold"] = int(arg)
            return await ctx.message.edit(content=S.ui_ok(f"mention threshold → {arg}"))
        on = arg.lower() not in ("off","disable") if arg else not S.filters["mention_spam"]["enabled"]
        S.filters["mention_spam"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"antimention → {'on' if on else 'off'}"))

    @commands.command(name="antimassping", brief="Toggle @everyone/@here filter")
    async def antimassping(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.filters["mass_ping"]["enabled"]
        S.filters["mass_ping"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"antimassping → {'on' if on else 'off'}"))

    @commands.command(name="antiscam", brief="Toggle scam pattern filter")
    async def antiscam(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.filters["scam"]["enabled"]
        S.filters["scam"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"antiscam → {'on' if on else 'off'}"))

    @commands.command(name="antibot", brief="Toggle bot message filter")
    async def antibot(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.filters["bot"]["enabled"]
        S.filters["bot"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"antibot → {'on' if on else 'off'}"))

    @commands.command(name="antiwebhook", brief="Toggle webhook message filter")
    async def antiwebhook(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.filters["webhook"]["enabled"]
        S.filters["webhook"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"antiwebhook → {'on' if on else 'off'}"))

    @commands.command(name="autopurge", brief="Auto-purge own messages  autopurge <n> | on | off")
    async def autopurge(self, ctx, arg: str = ""):
        if arg.isdigit():
            S.filters["auto_purge"]["keep"] = int(arg)
            S.filters["auto_purge"]["enabled"] = True
            return await ctx.message.edit(content=S.ui_ok(f"autopurge keep last {arg}"))
        on = arg.lower() not in ("off","disable") if arg else not S.filters["auto_purge"]["enabled"]
        S.filters["auto_purge"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"autopurge → {'on' if on else 'off'}"))

    @commands.command(name="filterclear", brief="Clear filter action log")
    async def filterclear(self, ctx):
        S.filters["actions_log"] = []
        await ctx.message.edit(content=S.ui_ok("filter log cleared"))

    @commands.command(name="filterlog", brief="Show recent filter actions")
    async def filterlog(self, ctx):
        entries = S.filters.get("actions_log", [])[-30:]
        rows = [f"  {S.GREY}•{S.RESET} {e['author'][:24]:<24}  {S.DIM}{e['reason']}{S.RESET}"
                for e in entries]
        await ctx.message.edit(content=S._paginate("filter log", f"{len(S.filters.get('actions_log',[]))} total", rows)
                               if rows else S.ui_info("no hits"))

    # ── Listener ──────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.user.id: return
        if not message.guild: return
        f = S.filters; content = message.content or ""

        if f.get("bot", {}).get("enabled") and getattr(message.author, "bot", False):
            try: await message.delete()
            except Exception: pass
            return

        if f.get("webhook", {}).get("enabled") and message.webhook_id:
            try: await message.delete()
            except Exception: pass
            return

        if f.get("spam", {}).get("enabled"):
            uid = str(message.author.id); now = time.time()
            hist = self._msg_history.setdefault(uid, [])
            hist[:] = [t for t in hist if now - t < f["spam"].get("window", 5)]
            hist.append(now)
            if len(hist) >= f["spam"].get("threshold", 5):
                try: await message.delete()
                except Exception: pass
                return

        if f.get("duplicate", {}).get("enabled"):
            uid = str(message.author.id); key = f"{uid}:{content.strip().lower()}"
            now = time.time(); last = self._msg_history.get(f"dup:{key}", 0)
            if content.strip() and now - last < f["duplicate"].get("window", 10):
                try: await message.delete()
                except Exception: pass
                return
            self._msg_history[f"dup:{key}"] = now

        if f.get("invite", {}).get("enabled") and INVITE_RE.search(content):
            try: await message.delete()
            except Exception: pass
            return

        if f.get("link", {}).get("enabled") and URL_RE.search(content):
            wl = f["link"].get("whitelist", set())
            urls = URL_RE.findall(content)
            if not wl or not all(any(w in u for w in wl) for u in urls):
                try: await message.delete()
                except Exception: pass
                return

        if f.get("attachment", {}).get("enabled") and message.attachments:
            try: await message.delete()
            except Exception: pass
            return

        if f.get("nsfw", {}).get("enabled"):
            low = content.lower()
            for kw in f["nsfw"].get("keywords", set()):
                if kw in low:
                    try: await message.delete()
                    except Exception: pass
                    return

        if f.get("mention_spam", {}).get("enabled"):
            if len(message.mentions or []) >= f["mention_spam"].get("threshold", 5):
                try: await message.delete()
                except Exception: pass
                return

        if f.get("mass_ping", {}).get("enabled"):
            if "@everyone" in content or "@here" in content:
                try: await message.delete()
                except Exception: pass
                return

        if f.get("scam", {}).get("enabled") and SCAM_RE.search(content):
            try: await message.delete()
            except Exception: pass
            return

async def setup(bot):
    await bot.add_cog(FiltersCog(bot))

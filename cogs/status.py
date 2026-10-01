# cogs/status.py
import asyncio, discord
from discord.ext import commands
from . import state as S
from .antid import jitter

class StatusCog(commands.Cog, name="status"):
    """Custom status management."""
    def __init__(self, bot):
        self.bot = bot
        self._rotate_task = None
        self._rotate_statuses: list = []

    @commands.command(name="status", brief="Set custom status")
    async def status(self, ctx, *, text: str = ""):
        activity = discord.CustomActivity(name=text) if text else None
        await self.bot.change_presence(activity=activity)
        await ctx.message.edit(content=S.ui_ok(f"status → {text or 'cleared'}"))




    @commands.command(name="clearstatus", brief="Clear status")
    async def clearstatus(self, ctx):
        await self.bot.change_presence(activity=None)
        await ctx.message.edit(content=S.ui_ok("status cleared"))

    @commands.command(name="online", brief="Set online")
    async def online(self, ctx):
        await self.bot.change_presence(status=discord.Status.online)
        await ctx.message.edit(content=S.ui_ok("status → online"))

    @commands.command(name="idle", brief="Set idle")
    async def idle(self, ctx):
        await self.bot.change_presence(status=discord.Status.idle)
        await ctx.message.edit(content=S.ui_ok("status → idle"))

    @commands.command(name="dnd", brief="Set do not disturb")
    async def dnd(self, ctx):
        await self.bot.change_presence(status=discord.Status.dnd)
        await ctx.message.edit(content=S.ui_ok("status → dnd"))

    @commands.command(name="invisible", brief="Set invisible")
    async def invisible(self, ctx):
        await self.bot.change_presence(status=discord.Status.invisible)
        await ctx.message.edit(content=S.ui_ok("status → invisible"))

    @commands.group(name="rotatestatus", aliases=["rss"], invoke_without_command=True)
    async def rotatestatus(self, ctx):
        await ctx.message.edit(content=S.ui_info("rss add <status> | start [interval] | stop | clear"))

    @rotatestatus.command(name="add")
    async def rss_add(self, ctx, *, text: str = ""):
        if text: self._rotate_statuses.append(text)
        await ctx.message.edit(content=S.ui_ok(f"{len(self._rotate_statuses)} statuses queued"))

    @rotatestatus.command(name="start")
    async def rss_start(self, ctx, interval: float = 30.0):
        if self._rotate_task and not self._rotate_task.done():
            self._rotate_task.cancel()
        async def _loop():
            i = 0
            while True:
                if self._rotate_statuses:
                    txt = self._rotate_statuses[i % len(self._rotate_statuses)]
                    await self.bot.change_presence(activity=discord.CustomActivity(name=txt))
                    i += 1
                await asyncio.sleep(jitter(interval))
        self._rotate_task = asyncio.create_task(_loop())
        await ctx.message.edit(content=S.ui_ok(f"rotating {len(self._rotate_statuses)} statuses every ~{interval}s"))

    @rotatestatus.command(name="stop")
    async def rss_stop(self, ctx):
        if self._rotate_task and not self._rotate_task.done():
            self._rotate_task.cancel()
        await ctx.message.edit(content=S.ui_ok("rotate stopped"))

    @rotatestatus.command(name="clear")
    async def rss_clear(self, ctx):
        self._rotate_statuses.clear()
        await ctx.message.edit(content=S.ui_ok("statuses cleared"))


    @commands.command(name="setstatus", aliases=["customstatus"], brief="Set custom status  [emoji,] text")
    async def setstatus(self, ctx, *, text: str = ""):
        if not text: return await ctx.message.edit(content=S.ui_err("usage: setstatus [emoji, ] text"))
        import re; emoji_name = None; emoji_id = None; status_text = text.strip()
        if "," in text:
            ep, rest = text.split(",",1); ep = ep.strip(); rest = rest.strip()
            if rest:
                m = re.match(r"<:([\w]+):(\d+)>", ep)
                if m: emoji_name = m.group(1); emoji_id = m.group(2)
                elif len(ep) >= 1 and (len(ep) == 1 or any(ord(c)>127 for c in ep)): emoji_name = ep
                if emoji_name or emoji_id: status_text = rest
        payload = {"custom_status": {"text": status_text, "emoji_name": emoji_name, "emoji_id": emoji_id}}
        try:
            import aiohttp
            async with aiohttp.ClientSession() as s:
                async with s.patch("https://discord.com/api/v9/users/@me/settings",
                                   headers={"Authorization": S.TOKEN, "Content-Type": "application/json",
                                            "User-Agent": S.USER_AGENT}, json=payload) as r:
                    if r.status == 200:
                        cfg = S.load_config() or {}
                        hist = cfg.get("status_history", [])
                        from datetime import datetime
                        hist.insert(0, {"text": status_text, "emoji": emoji_name,
                                        "time": datetime.now().strftime("%H:%M %d/%m")})
                        cfg["status_history"] = hist[:20]; S.save_config(cfg)
                        await ctx.message.edit(content=S.ui_ok(f"status → {emoji_name or ''} {status_text}".strip()))
                    else:
                        await ctx.message.edit(content=S.ui_err(f"failed {r.status}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="stealstatus", aliases=["copystatus"], brief="Copy another user's status")
    async def stealstatus(self, ctx, user_id: str = ""):
        if not user_id: return await ctx.message.edit(content=S.ui_err("usage: stealstatus <user_id>"))
        uid = user_id.strip("<@!>")
        try:
            import aiohttp
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://discord.com/api/v9/users/{uid}/profile",
                                 headers={"Authorization": S.TOKEN, "User-Agent": S.USER_AGENT}) as r:
                    if r.status != 200: return await ctx.message.edit(content=S.ui_err("cannot fetch"))
                    profile = await r.json()
                username = profile.get("user",{}).get("username","?")
                bio = profile.get("user_profile",{}).get("bio","") or ""
                if not bio: return await ctx.message.edit(content=S.ui_err(f"{username} has no bio"))
                payload = {"custom_status": {"text": bio[:128], "emoji_name": None, "emoji_id": None}}
                async with s.patch("https://discord.com/api/v9/users/@me/settings",
                                   headers={"Authorization": S.TOKEN, "Content-Type": "application/json",
                                            "User-Agent": S.USER_AGENT}, json=payload) as r2:
                    await ctx.message.edit(content=S.ui_ok(f"stole from {username}")
                                           if r2.status == 200 else S.ui_err(f"failed {r2.status}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="statushistory", brief="Show recent status history")
    async def statushistory(self, ctx):
        cfg = S.load_config() or {}
        hist = cfg.get("status_history", [])
        if not hist: return await ctx.message.edit(content=S.ui_info("no history yet"))
        rows = []
        for i, e in enumerate(hist[:20], 1):
            emoji = f"{e['emoji']} " if e.get("emoji") else ""
            stolen = f"  {S.DIM}(from {e['stolen_from']}){S.RESET}" if e.get("stolen_from") else ""
            rows.append(f"  {S.GREY}{i:2}.{S.RESET} {emoji}{e['text'][:60]}  {S.DIM}{e['time']}{S.RESET}{stolen}")
        await ctx.message.edit(content=S._paginate("status history", "recent", rows))

    @commands.command(name="speaklanguage", brief="Auto-translate outgoing messages")
    async def speaklanguage(self, ctx, lang: str = ""):
        if not lang: return await ctx.message.edit(content=S.ui_err("usage: speaklanguage <lang>"))
        S._speak_lang = lang
        await ctx.message.edit(content=S.ui_ok(f"auto-translate → {lang}"))

    @commands.command(name="speaklanguagestop", brief="Stop auto-translate")
    async def speaklanguagestop(self, ctx):
        S._speak_lang = None
        await ctx.message.edit(content=S.ui_ok("auto-translate stopped"))

async def setup(bot): await bot.add_cog(StatusCog(bot))

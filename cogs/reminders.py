# cogs/reminders.py
import time
import asyncio, time, discord
import discord
from discord.ext import commands
from . import state as S
from .antid import jitter

_reminders: list = []

class RemindersCog(commands.Cog, name="reminders"):
    def __init__(self, bot):
        self.bot = bot
        self._task = None

    async def cog_load(self):
        self._task = asyncio.create_task(self._check_loop())

    def cog_unload(self):
        self._task.cancel()

    async def _check_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now = time.time()
            fired = []
            for r in _reminders:
                if now >= r["at"]:
                    fired.append(r)
                    ch = self.bot.get_channel(r["channel"])
                    if ch:
                        try: await ch.send(S.ui_info(f"⏰ reminder: {r['text']}"))
                        except Exception: pass
            for r in fired: _reminders.remove(r)
            await asyncio.sleep(jitter(10.0))

    @commands.command(name="remind", aliases=["reminder"], brief="Set a reminder")
    async def remind(self, ctx, when: str = "", *, text: str = "reminder"):
        if not when: return await ctx.message.edit(content=S.ui_err("usage: remind <time> <text>  e.g. remind 30m do thing"))
        secs = 0
        if when.endswith("s"): secs = int(when[:-1])
        elif when.endswith("m"): secs = int(when[:-1]) * 60
        elif when.endswith("h"): secs = int(when[:-1]) * 3600
        elif when.endswith("d"): secs = int(when[:-1]) * 86400
        else:
            try: secs = int(when)
            except: return await ctx.message.edit(content=S.ui_err("invalid time format"))
        _reminders.append({"at": time.time() + secs, "text": text, "channel": ctx.channel.id})
        await ctx.message.edit(content=S.ui_ok(f"reminder set for {when}: {text}"))

    @commands.command(name="reminders", brief="List reminders")
    async def list_reminders(self, ctx):
        if not _reminders: return await ctx.message.edit(content=S.ui_info("no reminders"))
        now = time.time()
        rows = [f"  {S.GREY}•{S.RESET} {r['text']} (in {int(r['at']-now)}s)" for r in _reminders]
        await ctx.message.edit(content=S._paginate("reminders","",rows))

    @commands.command(name="clearreminders", brief="Clear all reminders")
    async def clearreminders(self, ctx):
        _reminders.clear()
        await ctx.message.edit(content=S.ui_ok("reminders cleared"))


    @commands.command(name="timer", brief="Set a timer  timer <seconds> [label]")
    async def timer(self, ctx, seconds: int = 0, *, label: str = "Timer"):
        if not seconds: return await ctx.message.edit(content=S.ui_err("usage: timer <seconds> [label]"))
        import asyncio as _a
        await ctx.message.edit(content=S.ui_ok(f"timer set: {label} in {seconds}s"))
        await _a.sleep(seconds)
        await ctx.channel.send(S.ui_ok(f"⏰ {label} — {seconds}s elapsed"))

    @commands.command(name="timers", brief="List active reminders/timers")
    async def timers(self, ctx):
        reminders = getattr(S,"_reminders",[])
        if not reminders: return await ctx.message.edit(content=S.ui_info("no active reminders"))
        rows = [f"  {S.GREY}{i}{S.RESET} {r.get('text','?')} in {max(0,int(r.get('due',0)-__import__('time').time()))}s"
                for i,r in enumerate(reminders)]
        await ctx.message.edit(content=S._paginate("timers","",rows))

    @commands.command(name="delremind", brief="Delete a reminder by index")
    async def delremind(self, ctx, index: int = -1):
        reminders = getattr(S,"_reminders",[])
        if 0 <= index < len(reminders):
            removed = reminders.pop(index)
            await ctx.message.edit(content=S.ui_ok(f"removed: {removed.get('text','?')}"))
        else:
            await ctx.message.edit(content=S.ui_err("invalid index"))

    @commands.command(name="notify", brief="Notify when a user sends a message  notify <@user>")
    async def notify(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: notify <@user>"))
        if not hasattr(S,"_notify_watch"): S._notify_watch = {}
        S._notify_watch[user.id] = ctx.channel.id
        await ctx.message.edit(content=S.ui_ok(f"watching {user} — will notify when they send a message"))

    @commands.command(name="notifications", brief="List notification watches")
    async def notifications(self, ctx):
        watches = getattr(S,"_notify_watch",{})
        rows = [f"  {S.GREY}•{S.RESET} <@{uid}> → <#{cid}>" for uid,cid in watches.items()]
        await ctx.message.edit(content=S._paginate("notifications","",rows) if rows else S.ui_info("none"))

async def setup(bot): await bot.add_cog(RemindersCog(bot))
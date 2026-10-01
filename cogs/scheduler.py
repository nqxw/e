# cogs/scheduler.py
import asyncio, time, discord
from discord.ext import commands
from . import state as S
from .antid import jitter

class SchedulerCog(commands.Cog, name="scheduler"):
    def __init__(self, bot):
        self.bot = bot
        self._task = None

    async def cog_load(self):
        self._task = asyncio.create_task(self._run())

    def cog_unload(self): self._task.cancel()

    async def _run(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now = time.time()
            fired = []
            for entry in S._scheduler:
                if now >= entry.get("at", 0):
                    fired.append(entry)
                    ch = self.bot.get_channel(entry.get("channel", 0))
                    if ch:
                        try: await ch.send(entry.get("message","scheduled message"))
                        except Exception: pass
            for e in fired: S._scheduler.remove(e)
            await asyncio.sleep(jitter(10.0))

    @commands.command(name="schedule", brief="Schedule a message")
    async def schedule(self, ctx, when: str = "", *, text: str = ""):
        if not when or not text:
            return await ctx.message.edit(content=S.ui_err("usage: schedule <time> <message>"))
        secs = 0
        if when.endswith("m"): secs = int(when[:-1]) * 60
        elif when.endswith("h"): secs = int(when[:-1]) * 3600
        elif when.endswith("s"): secs = int(when[:-1])
        else:
            try: secs = int(when)
            except: return await ctx.message.edit(content=S.ui_err("invalid time"))
        S._scheduler.append({"at": time.time()+secs, "channel": ctx.channel.id, "message": text})
        await ctx.message.edit(content=S.ui_ok(f"scheduled in {when}: {text[:40]}"))

    @commands.command(name="schedulelist", brief="List scheduled messages")
    async def schedulelist(self, ctx):
        now = time.time()
        rows = [f"  {S.GREY}•{S.RESET} in {int(e['at']-now)}s: {e['message'][:50]}"
                for e in S._scheduler]
        await ctx.message.edit(content=S._paginate("scheduled","",rows) if rows else S.ui_info("none"))

    @commands.command(name="scheduleclear", brief="Clear scheduled messages")
    async def scheduleclear(self, ctx):
        S._scheduler.clear()
        await ctx.message.edit(content=S.ui_ok("schedule cleared"))

async def setup(bot): await bot.add_cog(SchedulerCog(bot))

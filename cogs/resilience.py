# cogs/resilience.py
import asyncio, discord
from discord.ext import commands
from . import state as S
from .antid import jitter

class ResilienceCog(commands.Cog, name="resilience"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="resilience", brief="Resilience status")
    async def resilience(self, ctx):
        await ctx.message.edit(content=S.ui_box("resilience", [
            f"  {S.DIM}auto_reconnect{S.RESET} {S._auto_reconnect}",
            f"  {S.DIM}reconnects{S.RESET}     {S._reconnect_count}",
            f"  {S.DIM}rate limits{S.RESET}    {len(S._rate_limit_events)}",
        ]))

    @commands.Cog.listener()
    async def on_disconnect(self):
        S._reconnect_count += 1
        print(f"[resilience] disconnected (#{S._reconnect_count})")

    @commands.Cog.listener()
    async def on_resumed(self):
        print(f"[resilience] resumed")


    @commands.command(name="autoreconnect", brief="Toggle auto-reconnect")
    async def autoreconnect(self, ctx, toggle: str = ""):
        if not hasattr(S,"_autoreconnect"): S._autoreconnect = True
        S._autoreconnect = toggle.lower() not in ("off","disable") if toggle else not S._autoreconnect
        await ctx.message.edit(content=S.ui_ok(f"autoreconnect → {'on' if S._autoreconnect else 'off'}"))

    @commands.command(name="autorestart", brief="Toggle auto-restart on crash")
    async def autorestart(self, ctx, toggle: str = ""):
        if not hasattr(S,"_autorestart"): S._autorestart = False
        S._autorestart = toggle.lower() not in ("off","disable") if toggle else not S._autorestart
        await ctx.message.edit(content=S.ui_ok(f"autorestart → {'on' if S._autorestart else 'off'}"))

    @commands.command(name="sessionmon", brief="Session monitor status")
    async def sessionmon(self, ctx):
        ws = getattr(self.bot,"ws",None)
        await ctx.message.edit(content=S.ui_box("session", [
            f"  {S.DIM}latency{S.RESET}    {round(self.bot.latency*1000)}ms",
            f"  {S.DIM}ws{S.RESET}         {type(ws).__name__ if ws else 'None'}",
            f"  {S.DIM}guilds{S.RESET}     {len(self.bot.guilds)}",
            f"  {S.DIM}closed{S.RESET}     {self.bot.is_closed()}",
        ]))

    @commands.command(name="cache", brief="Show cache stats")
    async def cache(self, ctx):
        await ctx.message.edit(content=S.ui_box("cache", [
            f"  {S.DIM}guilds{S.RESET}     {len(self.bot.guilds)}",
            f"  {S.DIM}users{S.RESET}      {len(self.bot.users)}",
            f"  {S.DIM}channels{S.RESET}   {sum(len(g.channels) for g in self.bot.guilds)}",
            f"  {S.DIM}snipe cache{S.RESET} {len(getattr(S,'_snipe_cache',{}))}",
        ]))

    @commands.command(name="ratelimit", aliases=["ratelimits"], brief="Show rate limit state")
    async def ratelimit(self, ctx):
        import time as _t
        rl = getattr(S,"_rate_limit",{})
        if not rl: return await ctx.message.edit(content=S.ui_info("no rate limit data"))
        rows = [f"  {S.GREY}•{S.RESET} {k}: retry in {max(0,v-_t.time()):.1f}s" for k,v in rl.items()]
        await ctx.message.edit(content=S._paginate("rate limits","",rows))

    @commands.command(name="queue", brief="Show command queue length")
    async def queue(self, ctx):
        q = getattr(S,"_cmd_queue",[])
        await ctx.message.edit(content=S.ui_box("queue",[
            f"  {S.DIM}length{S.RESET}  {len(q)}",
            f"  {S.DIM}items{S.RESET}   {str(q[:5])[:80]}{'...' if len(q)>5 else ''}",
        ]))

async def setup(bot): await bot.add_cog(ResilienceCog(bot))

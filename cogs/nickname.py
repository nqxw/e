# cogs/nickname.py
import asyncio, discord
from discord.ext import commands
from . import state as S
from .antid import jitter

class NicknameCog(commands.Cog, name="nickname"):
    def __init__(self, bot):
        self.bot = bot
        self._task = None

    @commands.command(name="autonick", brief="Auto-nickname config")
    async def autonick(self, ctx, sub: str = "status", *, args: str = ""):
        if sub == "on":
            S.nickname["enabled"] = True
            await ctx.message.edit(content=S.ui_ok("auto-nick → on"))
        elif sub == "off":
            S.nickname["enabled"] = False
            if self._task and not self._task.done(): self._task.cancel()
            await ctx.message.edit(content=S.ui_ok("auto-nick → off"))
        elif sub == "pattern" and args:
            S.nickname["pattern"] = args
            await ctx.message.edit(content=S.ui_ok(f"pattern → {args}"))
        elif sub == "interval" and args:
            try: S.nickname["interval"] = int(args)
            except ValueError: pass
            await ctx.message.edit(content=S.ui_ok(f"interval → {S.nickname['interval']}s"))
        else:
            await ctx.message.edit(content=S.ui_box("auto-nick", [
                f"  {S.DIM}enabled{S.RESET}   {S.nickname['enabled']}",
                f"  {S.DIM}pattern{S.RESET}   {S.nickname['pattern']}",
                f"  {S.DIM}interval{S.RESET}  {S.nickname['interval']}s",
            ]))

    @commands.command(name="setnick", brief="Set your nickname in a server")
    @commands.guild_only()
    async def setnick(self, ctx, *, nick: str = ""):
        await ctx.guild.me.edit(nick=nick or None)
        await ctx.message.edit(content=S.ui_ok(f"nick → {nick or 'cleared'}"))


    @commands.command(name="nickset", brief="Set your own nick")
    @commands.guild_only()
    async def nickset(self, ctx, *, nick: str = ""):
        await ctx.guild.me.edit(nick=nick or None)
        await ctx.message.edit(content=S.ui_ok(f"nick → {nick or 'cleared'}"))

    @commands.command(name="nickclear", brief="Clear your nick")
    @commands.guild_only()
    async def nickclear(self, ctx):
        await ctx.guild.me.edit(nick=None)
        await ctx.message.edit(content=S.ui_ok("nick cleared"))

    @commands.command(name="nickhistory", brief="Show nick change history")
    async def nickhistory(self, ctx):
        hist = getattr(S,"_nick_history",[])
        rows = [f"  {S.GREY}•{S.RESET} {e}" for e in hist[-20:]]
        await ctx.message.edit(content=S._paginate("nick history","",rows) if rows else S.ui_info("no history"))

async def setup(bot): await bot.add_cog(NicknameCog(bot))

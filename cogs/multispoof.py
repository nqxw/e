# cogs/multispoof.py
import asyncio, discord
from discord.ext import commands
from . import state as S

_satellite_bots: list = []

class MultiSpoofCog(commands.Cog, name="multispoof"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="multispoof", brief="Spawn satellite sessions")
    async def multispoof(self, ctx, sub: str = "status"):
        if sub == "status":
            await ctx.message.edit(content=S.ui_box("multispoof", [
                f"  {S.DIM}sessions{S.RESET}  {len(_satellite_bots)}",
                f"  {S.DIM}tokens{S.RESET}    {len(S.HOSTED_TOKENS)}",
            ]))
        elif sub == "start":
            await ctx.message.edit(content=S.ui_info(f"add tokens with hostadd first ({len(S.HOSTED_TOKENS)} loaded)"))
        elif sub == "stop":
            for b in _satellite_bots:
                try: await b.close()
                except Exception: pass
            _satellite_bots.clear()
            await ctx.message.edit(content=S.ui_ok("satellite sessions stopped"))


    @commands.command(name="mspoof", brief="Multi-platform spoof pool  mspoof <p1> <p2> ...")
    async def mspoof(self, ctx, *platforms):
        if not platforms: return await ctx.message.edit(content=S.ui_err("usage: mspoof <platform>..."))
        self._pool = list(platforms); self._mode = "rotate"; self._cursor = 0
        await ctx.message.edit(content=S.ui_ok(f"multi-spoof pool: {', '.join(platforms)}"))

async def setup(bot): await bot.add_cog(MultiSpoofCog(bot))

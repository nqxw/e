# cogs/rpc_adapter.py
import discord
from discord.ext import commands
from . import state as S

class RpcAdapterCog(commands.Cog, name="rpc_adapter"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="rpcreload", brief="Reload RPC cog")
    async def rpcreload(self, ctx):
        try:
            await self.bot.reload_extension("cogs.rpc")
            await ctx.message.edit(content=S.ui_ok("RPC cog reloaded"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

async def setup(bot): await bot.add_cog(RpcAdapterCog(bot))

# cogs/host.py
import discord
from discord.ext import commands
from . import state as S

class HostCog(commands.Cog, name="host"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="hostadd", brief="Add a hosted token")
    async def hostadd(self, ctx, token: str = ""):
        if not token: return await ctx.message.edit(content=S.ui_err("usage: hostadd <token>"))
        await ctx.message.delete()
        S.HOSTED_TOKENS.append(token)
        await ctx.channel.send(S.ui_ok(f"token added ({len(S.HOSTED_TOKENS)} total)"))

    @commands.command(name="hostlist", brief="List hosted sessions")
    async def hostlist(self, ctx):
        rows = [f"  {S.GREY}{i}{S.RESET} {t[:20]}..." for i, t in enumerate(S.HOSTED_TOKENS)]
        await ctx.message.edit(content=S._paginate("hosted tokens","",rows) if rows else S.ui_info("no tokens"))

    @commands.command(name="hostclear", brief="Clear hosted tokens")
    async def hostclear(self, ctx):
        S.HOSTED_TOKENS.clear()
        await ctx.message.edit(content=S.ui_ok("tokens cleared"))


    @commands.command(name="host", brief="Show hosting info")
    async def host(self, ctx):
        tokens = getattr(S,"HOSTED_TOKENS",[])
        await ctx.message.edit(content=S.ui_box("host",[
            f"  {S.DIM}tokens{S.RESET}  {len(tokens)}",
            f"  {S.DIM}prefix{S.RESET}  {S.PREFIX}",
        ]))

    @commands.command(name="admin", brief="Show admin status")
    async def admin(self, ctx):
        is_admin = ctx.author.id in getattr(S,"_admins",set()) or ctx.author.id == getattr(S,"OWNER_ID",0)
        await ctx.message.edit(content=S.ui_ok(f"admin: {is_admin}"))

async def setup(bot): await bot.add_cog(HostCog(bot))

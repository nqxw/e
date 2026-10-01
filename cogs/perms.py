# cogs/perms.py
import discord
from discord.ext import commands
from . import state as S

class PermsCog(commands.Cog, name="perms"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="myperms", brief="Show your permissions in this channel")
    @commands.guild_only()
    async def myperms(self, ctx):
        perms = ctx.channel.permissions_for(ctx.guild.me)
        rows = [f"  {S.GREY}•{S.RESET} {perm.replace('_',' ')}"
                for perm, val in perms if val]
        await ctx.message.edit(content=S._paginate("my permissions", ctx.channel.name, rows))

    @commands.command(name="checkperms", brief="Check user permissions")
    @commands.guild_only()
    async def checkperms(self, ctx, member: discord.Member = None):
        m = member or ctx.guild.me
        perms = ctx.channel.permissions_for(m)
        rows = [f"  {S.GREY}•{S.RESET} {p.replace('_',' ')}" for p, v in perms if v]
        await ctx.message.edit(content=S._paginate(f"perms: {m}", ctx.channel.name, rows))

    @commands.command(name="perm", brief="Check specific permission")
    @commands.guild_only()
    async def perm(self, ctx, *, perm_name: str = ""):
        if not perm_name: return await ctx.message.edit(content=S.ui_err("usage: perm <permission_name>"))
        perms = ctx.channel.permissions_for(ctx.guild.me)
        val = getattr(perms, perm_name.lower().replace(" ","_"), None)
        if val is None: return await ctx.message.edit(content=S.ui_err(f"unknown permission: {perm_name}"))
        await ctx.message.edit(content=S.ui_ok(f"{perm_name}: {val}"))

async def setup(bot): await bot.add_cog(PermsCog(bot))

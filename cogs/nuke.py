# cogs/nuke.py
import asyncio, discord
from discord.ext import commands
from . import state as S
from .antid import batch_delay, shuffled

class NukeCog(commands.Cog, name="nuke"):
    def __init__(self, bot): self.bot = bot

    @commands.group(name="nuke", invoke_without_command=True, brief="Server nuke tools")
    @commands.guild_only()
    async def nuke(self, ctx):
        await ctx.message.edit(content=S.ui_info("nuke channels|roles|emojis|everything"))

    @nuke.command(name="channels")
    @commands.guild_only()
    async def nuke_channels(self, ctx):
        await ctx.message.delete()
        for i, ch in enumerate(shuffled(ctx.guild.channels)):
            try:
                await ch.delete()
                await batch_delay(i + 1)
            except Exception: pass

    @nuke.command(name="roles")
    @commands.guild_only()
    async def nuke_roles(self, ctx):
        await ctx.message.delete()
        for i, r in enumerate(shuffled(ctx.guild.roles)):
            if r.is_default(): continue
            try:
                await r.delete()
                await batch_delay(i + 1)
            except Exception: pass

    @nuke.command(name="emojis")
    @commands.guild_only()
    async def nuke_emojis(self, ctx):
        done = 0
        for i, e in enumerate(shuffled(ctx.guild.emojis)):
            try:
                await e.delete()
                done += 1
                await batch_delay(i + 1)
            except Exception: pass
        await ctx.channel.send(S.ui_ok(f"deleted {done} emojis"))

    @nuke.command(name="everything")
    @commands.guild_only()
    async def nuke_everything(self, ctx):
        await ctx.message.delete()
        for i, ch in enumerate(shuffled(ctx.guild.channels)):
            try: await ch.delete(); await batch_delay(i + 1)
            except Exception: pass
        for i, r in enumerate(shuffled(ctx.guild.roles)):
            if r.is_default(): continue
            try: await r.delete(); await batch_delay(i + 1)
            except Exception: pass


    @commands.command(name="nukebackup", brief="Backup server before nuke")
    @commands.guild_only()
    async def nukebackup(self, ctx):
        import json, os
        g = ctx.guild
        data = {
            "name": g.name, "id": g.id,
            "channels": [{"name":c.name,"type":str(c.type),"id":c.id} for c in g.channels],
            "roles": [{"name":r.name,"color":str(r.color),"perms":r.permissions.value} for r in g.roles],
        }
        os.makedirs("backups",exist_ok=True)
        path = f"backups/nuke_backup_{g.id}.json"
        with open(path,"w") as f: json.dump(data,f,indent=2)
        await ctx.message.edit(content=S.ui_ok(f"backup saved → {path}"))

async def setup(bot): await bot.add_cog(NukeCog(bot))

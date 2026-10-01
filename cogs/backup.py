# cogs/backup.py
import time
import json, discord, aiohttp
from discord.ext import commands
from . import state as S
from .antid import batch_delay, shuffled
import os, time
import aiohttp

class BackupCog(commands.Cog, name="backup"):
    def __init__(self, bot): self.bot = bot

    @commands.group(name="backup", invoke_without_command=True, brief="Server backup")
    @commands.guild_only()
    async def backup(self, ctx):
        await ctx.message.edit(content=S.ui_info("backup server | restore <file> | list"))

    @backup.command(name="server")
    async def backup_server(self, ctx):
        g = ctx.guild
        data = {
            "name": g.name, "description": g.description,
            "channels": [{"name": c.name, "type": str(c.type)} for c in g.channels],
            "roles": [{"name": r.name, "color": str(r.color), "perms": r.permissions.value}
                      for r in g.roles if not r.is_default()],
            "emojis": [{"name": e.name, "url": str(e.url)} for e in g.emojis],
        }
        os.makedirs("backups", exist_ok=True)
        path = f"backups/{g.id}_{int(time.time())}.json"
        with open(path, "w") as f: json.dump(data, f, indent=2)
        await ctx.message.edit(content=S.ui_ok(f"backed up → {path}"))

    @backup.command(name="list")
    async def backup_list(self, ctx):
        os.makedirs("backups", exist_ok=True)
        files = [f for f in os.listdir("backups") if f.endswith(".json")]
        rows = [f"  {S.GREY}•{S.RESET} {f}" for f in sorted(files)]
        await ctx.message.edit(content=S._paginate("backups","",rows) if rows else S.ui_info("no backups"))

async def setup(bot): await bot.add_cog(BackupCog(bot))
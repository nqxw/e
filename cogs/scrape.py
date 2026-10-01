# cogs/scrape.py
import time
import csv, json, os, time, discord
from discord.ext import commands
from . import state as S
from .antid import delay
import asyncio
import json

class ScrapeCog(commands.Cog, name="scrape"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="scrape", brief="Scrape server data")
    @commands.guild_only()
    async def scrape(self, ctx, sub: str = "members"):
        g = ctx.guild
        os.makedirs("exports", exist_ok=True)
        if sub == "members":
            rows = [(str(m.id), str(m), m.nick or "", str(m.joined_at)[:10] if m.joined_at else "")
                    for m in g.members]
            path = f"exports/members_{g.id}_{int(time.time())}.csv"
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f); w.writerow(["id","name","nick","joined"]); w.writerows(rows)
            await ctx.message.edit(content=S.ui_ok(f"exported {len(rows)} members → {path}"))
        elif sub == "channels":
            data = [{"id": str(c.id), "name": c.name, "type": str(c.type)} for c in g.channels]
            path = f"exports/channels_{g.id}_{int(time.time())}.json"
            with open(path, "w") as f: json.dump(data, f, indent=2)
            await ctx.message.edit(content=S.ui_ok(f"exported {len(data)} channels → {path}"))
        elif sub == "roles":
            data = [{"id": str(r.id), "name": r.name, "color": str(r.color)} for r in g.roles]
            path = f"exports/roles_{g.id}_{int(time.time())}.json"
            with open(path, "w") as f: json.dump(data, f, indent=2)
            await ctx.message.edit(content=S.ui_ok(f"exported {len(data)} roles → {path}"))
        else:
            await ctx.message.edit(content=S.ui_info("scrape members|channels|roles"))


    @commands.command(name="export", brief="Export channel messages to txt")
    async def export(self, ctx, limit: int = 500):
        import os
        await ctx.message.delete()
        out = []; count = 0
        async for msg in ctx.channel.history(limit=limit):
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            out.append(f"[{ts}] {msg.author}: {msg.content}")
            count += 1
        os.makedirs("exports", exist_ok=True)
        path = f"exports/{ctx.channel.id}_{count}.txt"
        with open(path,"w",encoding="utf-8") as f: f.write("\n".join(reversed(out)))
        await ctx.channel.send(S.ui_ok(f"exported {count} → {path}"))

    @commands.command(name="import", aliases=["importch"], brief="Import and send messages from txt file")
    async def import_file(self, ctx, filepath: str = "", delay: float = 1.0):
        import os, asyncio as _a
        if not filepath or not os.path.exists(filepath):
            return await ctx.message.edit(content=S.ui_err("usage: import <path> [delay_secs]"))
        with open(filepath, encoding="utf-8") as f: lines = f.readlines()
        await ctx.message.delete()
        for line in lines:
            line = line.strip()
            if line:
                await ctx.channel.send(line)
                await _a.sleep(delay)

async def setup(bot): await bot.add_cog(ScrapeCog(bot))
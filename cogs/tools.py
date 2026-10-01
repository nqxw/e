# cogs/tools.py | nitro, applybypass, tokeninfo, calculate, fact, fetchlyrics, robuxtax, archivechannel
import asyncio, base64, os, random, re, string, time, aiohttp
from uuid import uuid4
from datetime import datetime
from discord.ext import commands
from . import state as S
import re
import base64
import random
import aiohttp

class ToolsCog(commands.Cog, name="tools"):
    """Misc tools — nitro gen, bypass, token info, calculate, lyrics, archive."""
    def __init__(self, bot): self.bot = bot

    @commands.command(name="nitro", brief="Generate a fake Nitro link")
    async def nitro(self, ctx):
        await ctx.message.delete()
        code = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        await ctx.channel.send(f"```\nhttps://discord.gift/{code}\n```")

    @commands.command(name="applybypass", brief="Join a server bypassing verification")
    async def applybypass(self, ctx, invite: str = ""):
        if not invite: return await ctx.message.edit(content=S.ui_err("usage: applybypass <invite>"))
        await ctx.message.delete()
        invite = invite.replace("https://discord.gg/","").replace("discord.gg/","")
        h = {"Authorization": S.TOKEN, "Content-Type": "application/json", "User-Agent": S.USER_AGENT}
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://discord.com/api/v9/invites/{invite}", headers=h) as r:
                    if r.status != 200:
                        return await ctx.channel.send(S.ui_err("invalid invite"))
                    inv = await r.json()
                guild_id = inv.get("guild", {}).get("id")
                async with s.post(f"https://discord.com/api/v9/invites/{invite}",
                                  headers=h, json={"session_id": str(uuid4())[:8]}) as r2:
                    if r2.status in (200, 204):
                        await ctx.channel.send(S.ui_ok("joined"))
                    elif r2.status == 403 and guild_id:
                        async with s.put(f"https://discord.com/api/v9/guilds/{guild_id}/requests/@me",
                                         headers=h, json={"form_fields": []}) as r3:
                            await ctx.channel.send(S.ui_ok("applied") if r3.status in (200,201,204)
                                                   else S.ui_err(f"failed {r3.status}"))
                    else:
                        await ctx.channel.send(S.ui_err(f"failed {r2.status}"))
        except Exception as e:
            await ctx.channel.send(S.ui_err(str(e)))

    @commands.command(name="tokeninfo", brief="Decode a Discord token")
    async def tokeninfo(self, ctx, token: str = ""):
        if not token: return await ctx.message.edit(content=S.ui_err("usage: tokeninfo <token>"))
        await ctx.message.delete()
        try:
            parts = token.split(".")
            uid_b64 = parts[0]
            uid = base64.b64decode(uid_b64 + "=" * (-len(uid_b64) % 4)).decode()
            ts_b64 = parts[1]
            ts_bytes = base64.b64decode(ts_b64 + "=" * (-len(ts_b64) % 4))
            epoch = int.from_bytes(ts_bytes[:4], "big")
            created = datetime.utcfromtimestamp(epoch + 1293840000).strftime("%Y-%m-%d %H:%M:%S")
            await ctx.channel.send(S.ui_box("token info", [
                f"  {S.DIM}user_id{S.RESET}  {uid}",
                f"  {S.DIM}created{S.RESET}  {created} UTC",
            ]))
        except Exception as e:
            await ctx.channel.send(S.ui_err(f"decode failed: {e}"))

    @commands.command(name="calculate", aliases=["calc"], brief="Evaluate a math expression")
    async def calculate(self, ctx, *, expr: str = ""):
        if not expr: return await ctx.message.edit(content=S.ui_err("usage: calculate <expr>"))
        try:
            result = eval(re.sub(r"[^0-9+\-*/(). ]", "", expr))
            await ctx.message.edit(content=S.ui_ok(f"{expr} = {result}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="fact", brief="Random useless fact")
    async def fact(self, ctx):
        await ctx.message.delete()
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en") as r:
                    d = await r.json()
                    await ctx.channel.send(f"💡 {d.get('text','no fact')}")
        except Exception as e:
            await ctx.channel.send(S.ui_err(str(e)))

    @commands.command(name="fetchlyrics", aliases=["lyrics"], brief="Fetch lyrics  — fetchlyrics Artist/Title")
    async def fetchlyrics(self, ctx, *, query: str = ""):
        if not query: return await ctx.message.edit(content=S.ui_err("usage: fetchlyrics <artist/title>"))
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://lyrist.vercel.app/api/{query.replace(' - ','/')}") as r:
                    if r.status == 200:
                        lyrics = (await r.json()).get("lyrics", "")[:1800]
                        await ctx.message.edit(content=f"```\n{lyrics}\n```")
                    else:
                        await ctx.message.edit(content=S.ui_err("not found"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="robuxtax", brief="Calculate Roblox marketplace fee")
    async def robuxtax(self, ctx, amount: int = 0):
        if not amount: return await ctx.message.edit(content=S.ui_err("usage: robuxtax <amount>"))
        after = int(amount * 0.7); fee = amount - after
        await ctx.message.edit(content=S.ui_box("roblox fee", [
            f"  {S.DIM}listed{S.RESET}  {amount:,} R$",
            f"  {S.DIM}fee{S.RESET}     {fee:,} R$",
            f"  {S.DIM}you get{S.RESET} {after:,} R$",
        ]))

    @commands.command(name="archivechannel", brief="Archive channel messages to file")
    async def archivechannel(self, ctx, channel_id: int = 0):
        import discord
        ch = ctx.bot.get_channel(channel_id) if channel_id else ctx.channel
        if not ch: return await ctx.channel.send(S.ui_err("channel not found"))
        await ctx.message.delete()
        out = []; count = 0
        async for msg in ch.history(limit=2000):
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            out.append(f"[{ts}] {msg.author}: {msg.content}")
            count += 1
        os.makedirs("exports", exist_ok=True)
        path = f"exports/archive_{ch.id}.txt"
        with open(path,"w",encoding="utf-8") as f: f.write("\n".join(reversed(out)))
        await ctx.channel.send(S.ui_ok(f"archived {count} msgs → {path}"))

async def setup(bot):
    await bot.add_cog(ToolsCog(bot))

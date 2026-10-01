# cogs/mass.py
import asyncio, discord
from discord.ext import commands
from . import state as S
from .antid import batch_delay, shuffled, on_rate_limit

class MassCog(commands.Cog, name="mass"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="massban", brief="Mass ban users")
    @commands.guild_only()
    async def massban(self, ctx, *members: discord.Member):
        if not members: return await ctx.message.edit(content=S.ui_err("provide users to ban"))
        await ctx.message.edit(content=S.ui_info(f"banning {len(members)}..."))
        done = 0
        for i, m in enumerate(shuffled(members)):
            try:
                await ctx.guild.ban(m, reason="massban")
                done += 1
            except Exception as e:
                if "429" in str(e): await on_rate_limit(5.0)
            await batch_delay(i + 1)
        await ctx.channel.send(S.ui_ok(f"banned {done}/{len(members)}"))

    @commands.command(name="masskick", brief="Mass kick users")
    @commands.guild_only()
    async def masskick(self, ctx, *members: discord.Member):
        if not members: return await ctx.message.edit(content=S.ui_err("provide users to kick"))
        await ctx.message.edit(content=S.ui_info(f"kicking {len(members)}..."))
        done = 0
        for i, m in enumerate(shuffled(members)):
            try:
                await ctx.guild.kick(m, reason="masskick")
                done += 1
            except Exception as e:
                if "429" in str(e): await on_rate_limit(5.0)
            await batch_delay(i + 1)
        await ctx.channel.send(S.ui_ok(f"kicked {done}/{len(members)}"))

    @commands.command(name="massrole", brief="Add role to many users")
    @commands.guild_only()
    async def massrole(self, ctx, role: discord.Role = None, *members: discord.Member):
        if not role: return await ctx.message.edit(content=S.ui_err("usage: massrole <@role> <@users...>"))
        targets = members or ctx.guild.members
        done = 0
        for i, m in enumerate(shuffled(targets)):
            try: await m.add_roles(role); done += 1
            except Exception as e:
                if "429" in str(e): await on_rate_limit(5.0)
            await batch_delay(i + 1)
        await ctx.message.edit(content=S.ui_ok(f"added {role.name} to {done} members"))

    @commands.command(name="massunrole", brief="Remove role from many users")
    @commands.guild_only()
    async def massunrole(self, ctx, role: discord.Role = None, *members: discord.Member):
        if not role: return await ctx.message.edit(content=S.ui_err("usage: massunrole <@role> <@users...>"))
        targets = members or [m for m in ctx.guild.members if role in m.roles]
        done = 0
        for i, m in enumerate(shuffled(targets)):
            try: await m.remove_roles(role); done += 1
            except Exception as e:
                if "429" in str(e): await on_rate_limit(5.0)
            await batch_delay(i + 1)
        await ctx.message.edit(content=S.ui_ok(f"removed {role.name} from {done} members"))

    @commands.command(name="massch", brief="Create N text channels")
    @commands.guild_only()
    async def massch(self, ctx, name: str = "channel", n: int = 5):
        n = min(n, 25)
        for i in range(n):
            try: await ctx.guild.create_text_channel(f"{name}-{i+1}")
            except Exception: pass
            await batch_delay(i + 1)
        await ctx.message.edit(content=S.ui_ok(f"created {n} channels"))


    @commands.command(name="massdm", brief="Mass DM all open DM channels")
    async def massdm(self, ctx, *, text: str = ""):
        if not text: return await ctx.message.edit(content=S.ui_err("usage: massdm <message>"))
        import discord as _d
        dms = [c for c in self.bot.private_channels if isinstance(c, _d.DMChannel)]
        if not dms: return await ctx.channel.send(S.ui_err("no DM channels open"))
        await ctx.message.delete()
        sent = 0; failed = 0
        status = await ctx.channel.send(S.ui_info(f"DMing {len(dms)}..."))
        for ch in dms:
            try: await ch.send(text); sent += 1
            except Exception: failed += 1
            await __import__("asyncio").sleep(2.0)
        try: await status.edit(content=S.ui_ok(f"sent {sent}/{len(dms)}  failed {failed}"))
        except Exception: pass

    @commands.command(name="stopdm", brief="Stop mass DM (placeholder)")
    async def stopdm(self, ctx):
        await ctx.channel.send(S.ui_info("mass DM stop not supported yet — restart bot to abort"))

    @commands.command(name="dmstats", brief="Show DM channel stats")
    async def dmstats(self, ctx):
        import discord as _d
        dms = [c for c in self.bot.private_channels if isinstance(c, _d.DMChannel)]
        await ctx.message.edit(content=S.ui_box("dm stats", [
            f"  {S.DIM}open DMs{S.RESET}  {len(dms)}",
        ]))

    @commands.command(name="massdmfile", brief="Mass DM IDs from file")
    async def massdmfile(self, ctx, filepath: str = "", *, text: str = ""):
        import os, aiohttp, asyncio as _a
        if not filepath or not text: return await ctx.message.edit(content=S.ui_err("usage: massdmfile <path> <msg>"))
        if not os.path.exists(filepath): return await ctx.message.edit(content=S.ui_err("file not found"))
        with open(filepath) as f: ids = [l.strip() for l in f if l.strip()]
        await ctx.message.delete()
        h = {"Authorization": S.TOKEN, "Content-Type": "application/json", "User-Agent": S.USER_AGENT}
        done = 0
        async with aiohttp.ClientSession() as s:
            for uid in ids:
                try:
                    async with s.post("https://discord.com/api/v9/users/@me/channels", headers=h,
                                      json={"recipient_id": uid}) as r:
                        if r.status == 200:
                            cid = (await r.json()).get("id")
                            if cid:
                                async with s.post(f"https://discord.com/api/v9/channels/{cid}/messages",
                                                  headers=h, json={"content": text}) as r2:
                                    if r2.status in (200,201): done += 1
                except Exception: pass
                await _a.sleep(1.2)
        await ctx.channel.send(S.ui_ok(f"sent to {done}/{len(ids)}"))

    @commands.command(name="massfriend", brief="Mass add friends from ID file")
    async def massfriend(self, ctx, filepath: str = ""):
        import os, aiohttp, asyncio as _a
        if not filepath or not os.path.exists(filepath):
            return await ctx.message.edit(content=S.ui_err("usage: massfriend <file>"))
        with open(filepath) as f: ids = [l.strip() for l in f if l.strip()]
        await ctx.message.delete()
        h = {"Authorization": S.TOKEN, "Content-Type": "application/json", "User-Agent": S.USER_AGENT}
        done = 0
        async with aiohttp.ClientSession() as s:
            for uid in ids:
                try:
                    async with s.put(f"https://discord.com/api/v9/users/@me/relationships/{uid}",
                                     headers=h, json={"type": 1}) as r:
                        if r.status in (200,201,204): done += 1
                except Exception: pass
                await _a.sleep(1.5)
        await ctx.channel.send(S.ui_ok(f"sent {done}/{len(ids)}"))

    @commands.command(name="massjoin", brief="Join server with hosted tokens")
    async def massjoin(self, ctx, invite: str = "", count: int = 1):
        import aiohttp, asyncio as _a
        from uuid import uuid4
        if not invite: return await ctx.message.edit(content=S.ui_err("usage: massjoin <invite> [count]"))
        invite = invite.replace("https://discord.gg/","").replace("discord.gg/","")
        tokens = getattr(S,"HOSTED_TOKENS",[])[:count]
        if not tokens: return await ctx.message.edit(content=S.ui_err("no hosted tokens in S.HOSTED_TOKENS"))
        await ctx.message.delete()
        done = 0
        async with aiohttp.ClientSession() as s:
            for tk in tokens:
                try:
                    async with s.post(f"https://discord.com/api/v9/invites/{invite}",
                                      headers={"Authorization": tk, "Content-Type": "application/json",
                                               "User-Agent": S.USER_AGENT},
                                      json={"session_id": str(uuid4())[:12]}) as r:
                        if r.status in (200,204): done += 1
                except Exception: pass
                await _a.sleep(1.5)
        await ctx.channel.send(S.ui_ok(f"joined {done}/{len(tokens)}"))

    @commands.command(name="massleave", brief="Leave a server with all hosted tokens")
    async def massleave(self, ctx, guild_id: str = ""):
        import aiohttp, asyncio as _a
        if not guild_id: return await ctx.message.edit(content=S.ui_err("usage: massleave <guild_id>"))
        tokens = getattr(S,"HOSTED_TOKENS",[])
        if not tokens: return await ctx.message.edit(content=S.ui_err("no hosted tokens"))
        await ctx.message.delete()
        done = 0
        async with aiohttp.ClientSession() as s:
            for tk in tokens:
                try:
                    async with s.delete(f"https://discord.com/api/v9/users/@me/guilds/{guild_id}",
                                        headers={"Authorization": tk, "User-Agent": S.USER_AGENT}) as r:
                        if r.status in (200,204): done += 1
                except Exception: pass
                await _a.sleep(1.0)
        await ctx.channel.send(S.ui_ok(f"left {done}/{len(tokens)}"))

    @commands.command(name="masscat", brief="Create N categories in server")
    @commands.guild_only()
    async def masscat(self, ctx, name: str = "Category", n: int = 5):
        await ctx.message.delete()
        for _ in range(min(n, 20)):
            try: await ctx.guild.create_category(name)
            except Exception: pass
        await ctx.channel.send(S.ui_ok(f"created {min(n,20)} categories"))

    @commands.command(name="massrolecreate", brief="Create N roles in server")
    @commands.guild_only()
    async def massrolecreate(self, ctx, name: str = "Role", n: int = 5):
        await ctx.message.delete()
        for _ in range(min(n, 50)):
            try: await ctx.guild.create_role(name=name)
            except Exception: pass
        await ctx.channel.send(S.ui_ok(f"created {min(n,50)} roles"))

    @commands.command(name="massreact", brief="React to last 10 messages with emoji")
    async def massreact(self, ctx, emoji: str = ""):
        if not emoji: return await ctx.message.edit(content=S.ui_err("usage: massreact <emoji>"))
        import asyncio as _a
        await ctx.message.delete()
        done = 0
        async for msg in ctx.channel.history(limit=10):
            try: await msg.add_reaction(emoji); done += 1
            except Exception: pass
            await _a.sleep(0.4)
        await ctx.channel.send(S.ui_ok(f"reacted to {done}"))

    @commands.command(name="massvc", brief="Create N voice channels")
    @commands.guild_only()
    async def massvc(self, ctx, name: str = "VC", n: int = 5):
        await ctx.message.delete()
        for _ in range(min(n, 50)):
            try: await ctx.guild.create_voice_channel(name)
            except Exception: pass
        await ctx.channel.send(S.ui_ok(f"created {min(n,50)} VCs"))

    @commands.command(name="massdelete", brief="Delete your own last N messages")
    async def massdelete(self, ctx, n: int = 10):
        await ctx.message.delete()
        import asyncio as _a
        deleted = 0
        async for msg in ctx.channel.history(limit=n * 3):
            if msg.author.id == self.bot.user.id:
                try: await msg.delete(); deleted += 1
                except Exception: pass
                await _a.sleep(0.3)
                if deleted >= n: break
        m = await ctx.channel.send(S.ui_ok(f"deleted {deleted}"))
        await _a.sleep(3)
        try: await m.delete()
        except Exception: pass

async def setup(bot): await bot.add_cog(MassCog(bot))

# cogs/profile_ext.py | avatardl, bannerdl, profilehistory, usernote, personal block/ignore
import os, time, aiohttp
from datetime import datetime
import discord
from discord.ext import commands
from . import state as S
import aiohttp
import time

async def _fetch_user(uid):
    async with aiohttp.ClientSession() as s:
        async with s.get(f"https://discord.com/api/v9/users/{uid}",
                         headers={"Authorization": S.TOKEN, "User-Agent": S.USER_AGENT}) as r:
            return await r.json() if r.status == 200 else None

class ProfileExtCog(commands.Cog, name="profile_ext"):
    """Avatar/banner download, profile history, user notes, personal block/ignore."""
    def __init__(self, bot): self.bot = bot

    @commands.command(name="avatardl", brief="Download a user's avatar")
    async def avatardl(self, ctx, user: discord.User = None):
        uid = user.id if user else ctx.author.id
        u = await _fetch_user(uid)
        if not u: return await ctx.message.edit(content=S.ui_err("not found"))
        if not u.get("avatar"): return await ctx.message.edit(content=S.ui_info("no avatar"))
        ext = "gif" if str(u["avatar"]).startswith("a_") else "png"
        url = f"https://cdn.discordapp.com/avatars/{uid}/{u['avatar']}.{ext}?size=1024"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url) as r: data = await r.read()
            os.makedirs("exports/avatars", exist_ok=True)
            path = f"exports/avatars/{uid}.{ext}"
            with open(path,"wb") as f: f.write(data)
            await ctx.message.edit(content=S.ui_ok(f"saved → {path}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="bannerdl", brief="Download a user's banner")
    async def bannerdl(self, ctx, user: discord.User = None):
        uid = user.id if user else ctx.author.id
        u = await _fetch_user(uid)
        if not u: return await ctx.message.edit(content=S.ui_err("not found"))
        if not u.get("banner"): return await ctx.message.edit(content=S.ui_info("no banner"))
        ext = "gif" if str(u["banner"]).startswith("a_") else "png"
        url = f"https://cdn.discordapp.com/banners/{uid}/{u['banner']}.{ext}?size=1024"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url) as r: data = await r.read()
            os.makedirs("exports/banners", exist_ok=True)
            path = f"exports/banners/{uid}.{ext}"
            with open(path,"wb") as f: f.write(data)
            await ctx.message.edit(content=S.ui_ok(f"saved → {path}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="profilehistory", brief="Show cached profile history for a user")
    async def profilehistory(self, ctx, user: discord.User = None):
        uid = user.id if user else ctx.author.id
        hist = S.profile_history.get(uid, []) if hasattr(S,"profile_history") else []
        if not hist:
            u = await _fetch_user(uid)
            if u:
                if not hasattr(S,"profile_history"): S.profile_history = {}
                S.profile_history.setdefault(uid,[]).append({
                    "ts": time.time(), "username": u.get("username"),
                    "avatar": u.get("avatar"), "banner": u.get("banner"),
                })
                hist = S.profile_history[uid]
        if not hist: return await ctx.message.edit(content=S.ui_info("no history"))
        rows = [f"  {S.GREY}•{S.RESET} {e['username']}  {S.DIM}av:{bool(e.get('avatar'))} bn:{bool(e.get('banner'))} {datetime.fromtimestamp(e['ts']).strftime('%m-%d %H:%M')}{S.RESET}"
                for e in hist[-30:]]
        await ctx.message.edit(content=S._paginate("profile history", str(uid), rows))

    @commands.command(name="usernote", brief="User notes  usernote add/list/clear <uid> [text]")
    async def usernote(self, ctx, sub: str = "", uid: str = "", *, text: str = ""):
        if not sub or not uid:
            return await ctx.message.edit(content=S.ui_err("usage: usernote add/list/clear <uid> [text]"))
        if not hasattr(S,"_user_notes"): S._user_notes = {}
        if sub == "add" and text:
            S._user_notes.setdefault(uid,[]).append({"text":text,"ts":time.time()})
            await ctx.message.edit(content=S.ui_ok("note saved"))
        elif sub == "list":
            notes = S._user_notes.get(uid,[])
            rows = [f"  {S.GREY}•{S.RESET} {datetime.fromtimestamp(n['ts']).strftime('%m-%d %H:%M')}  {n['text']}"
                    for n in notes]
            await ctx.message.edit(content=S._paginate("notes",uid,rows) if rows else S.ui_info("none"))
        elif sub == "clear":
            S._user_notes.pop(uid,None)
            await ctx.message.edit(content=S.ui_ok("cleared"))

    @commands.command(name="personalblock", brief="Block a user personally")
    async def personalblock(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: personalblock <@user>"))
        if not hasattr(S,"personal_blocklist"): S.personal_blocklist = set()
        S.personal_blocklist.add(user.id)
        await ctx.message.edit(content=S.ui_ok(f"blocked {user}"))

    @commands.command(name="personalunblock", brief="Unblock a user")
    async def personalunblock(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: personalunblock <@user>"))
        getattr(S,"personal_blocklist",set()).discard(user.id)
        await ctx.message.edit(content=S.ui_ok(f"unblocked {user}"))

    @commands.command(name="personalignore", brief="Ignore a user in filters")
    async def personalignore(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: personalignore <@user>"))
        if not hasattr(S,"personal_ignore"): S.personal_ignore = set()
        S.personal_ignore.add(user.id)
        await ctx.message.edit(content=S.ui_ok(f"ignoring {user}"))

    @commands.command(name="personalunignore", brief="Remove user from ignore")
    async def personalunignore(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: personalunignore <@user>"))
        getattr(S,"personal_ignore",set()).discard(user.id)
        await ctx.message.edit(content=S.ui_ok(f"unignored {user}"))

    @commands.command(name="personalblocklist", brief="List personally blocked users")
    async def personalblocklist(self, ctx):
        bl = sorted(getattr(S,"personal_blocklist",set()))
        rows = [f"  {S.GREY}•{S.RESET} <@{uid}>" for uid in bl]
        await ctx.message.edit(content=S._paginate("personal blocklist","",rows) if rows else S.ui_info("empty"))

    @commands.command(name="personallist", brief="Show personal block + ignore lists")
    async def personallist(self, ctx):
        bl = sorted(getattr(S,"personal_blocklist",set()))
        ig = sorted(getattr(S,"personal_ignore",set()))
        rows = [f"  {S.DIM}block{S.RESET}  {len(bl)}", f"  {S.DIM}ignore{S.RESET} {len(ig)}", ""]
        rows += [f"  {S.GREY}•{S.RESET} <@{uid}>  {S.DIM}block{S.RESET}" for uid in bl]
        rows += [f"  {S.GREY}•{S.RESET} <@{uid}>  {S.DIM}ignore{S.RESET}" for uid in ig]
        await ctx.message.edit(content=S._ansi_block(rows))

async def setup(bot):
    await bot.add_cog(ProfileExtCog(bot))

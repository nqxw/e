# cogs/tracking.py
import discord
from discord.ext import commands
from . import state as S
from collections import defaultdict

_logs: dict = defaultdict(list)

class TrackingCog(commands.Cog, name="tracking"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="track", brief="Track a user's messages")
    async def track(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: track <@user>"))
        S._tracked_users.add(user.id)
        await ctx.message.edit(content=S.ui_ok(f"tracking {user}"))

    @commands.command(name="untrack", brief="Stop tracking a user")
    async def untrack(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: untrack <@user>"))
        S._tracked_users.discard(user.id)
        await ctx.message.edit(content=S.ui_ok(f"untracked {user}"))

    @commands.command(name="tracklog", brief="Show tracked messages")
    async def tracklog(self, ctx, user: discord.User = None):
        uid = user.id if user else None
        entries = _logs.get(uid, []) if uid else [e for l in _logs.values() for e in l]
        rows = [f"  {S.GREY}•{S.RESET} {e['author']}: {e['content'][:60]}" for e in entries[-20:]]
        await ctx.message.edit(content=S._paginate("track log","",rows) if rows else S.ui_info("nothing logged"))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.user.id: return
        if message.author.id in S._tracked_users:
            _logs[message.author.id].append({
                "author":  str(message.author),
                "content": message.content or "[no text]",
                "channel": getattr(message.channel,"name","DM"),
            })
            if len(_logs[message.author.id]) > 100:
                _logs[message.author.id] = _logs[message.author.id][-100:]


    @commands.command(name="tracklist", brief="List tracked users")
    async def tracklist(self, ctx):
        tracked = getattr(S, "_tracked_users", set())
        if not tracked:
            return await ctx.message.edit(content=S.ui_info("no tracked users"))
        rows = [f"  {S.GREY}•{S.RESET} <@{uid}>" for uid in sorted(tracked)]
        await ctx.message.edit(content=S._paginate("tracked", "", rows))

async def setup(bot): await bot.add_cog(TrackingCog(bot))

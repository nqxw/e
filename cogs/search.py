# cogs/search.py
import asyncio, discord
from discord.ext import commands
from . import state as S
from .antid import delay, on_rate_limit, jitter

class SearchCog(commands.Cog, name="search"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="search", brief="Search messages in channel")
    async def search(self, ctx, *, query: str = ""):
        if not query: return await ctx.message.edit(content=S.ui_err("usage: search <query>"))
        await ctx.message.edit(content=S.ui_info(f"searching for `{query}`..."))
        results = []
        async for msg in ctx.channel.history(limit=500):
            if query.lower() in (msg.content or "").lower():
                results.append(f"  {S.DIM}{msg.author}{S.RESET} {msg.content[:80]}")
            if len(results) >= 20: break
        if not results:
            return await ctx.message.edit(content=S.ui_info("no results found"))
        await ctx.message.edit(content=S._paginate(f"search: {query}", "", results))

    @commands.command(name="purge", aliases=["clear"], brief="Delete your messages")
    async def purge(self, ctx, amount: int = 10):
        await ctx.message.delete()
        deleted = 0
        async for msg in ctx.channel.history(limit=300):
            if msg.author.id == self.bot.user.id and deleted < amount:
                try:
                    await msg.delete()
                    deleted += 1
                    await delay(0.3, 0.9)
                except Exception as e:
                    if "429" in str(e): await on_rate_limit(5.0)
        m = await ctx.channel.send(S.ui_ok(f"deleted {deleted} message(s)"))
        await asyncio.sleep(3)
        try: await m.delete()
        except Exception: pass

    @commands.command(name="purgeuser", brief="Delete messages from a user")
    async def purgeuser(self, ctx, user: discord.User = None, amount: int = 50):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: purgeuser <@user> [amount]"))
        await ctx.message.delete()
        deleted = 0
        async for msg in ctx.channel.history(limit=500):
            if msg.author.id == user.id and deleted < amount:
                try:
                    await msg.delete()
                    deleted += 1
                    await delay(0.4, 1.1)
                except Exception as e:
                    if "429" in str(e): await on_rate_limit(5.0)
        m = await ctx.channel.send(S.ui_ok(f"deleted {deleted} messages from {user}"))
        await asyncio.sleep(3)
        try: await m.delete()
        except Exception: pass


    @commands.command(name="msearch", brief="Search messages in channel")
    async def msearch(self, ctx, *, query: str = ""):
        if not query: return await ctx.message.edit(content=S.ui_err("usage: msearch <query>"))
        results = []
        async for msg in ctx.channel.history(limit=500):
            if query.lower() in (msg.content or "").lower():
                results.append(f"  {S.GREY}•{S.RESET} {msg.author}: {msg.content[:60]}")
            if len(results) >= 20: break
        await ctx.message.edit(content=S._paginate(f"search: {query}","",results) if results else S.ui_info("no results"))

    @commands.command(name="bulkdel", brief="Bulk delete messages matching query")
    async def bulkdel(self, ctx, *, query: str = ""):
        if not query: return await ctx.message.edit(content=S.ui_err("usage: bulkdel <query>"))
        deleted = 0
        async for msg in ctx.channel.history(limit=200):
            if msg.author.id == self.bot.user.id and query.lower() in (msg.content or "").lower():
                try: await msg.delete(); deleted += 1
                except Exception: pass
        m = await ctx.channel.send(S.ui_ok(f"deleted {deleted} matching"))
        import asyncio
        await asyncio.sleep(3)
        try: await m.delete()
        except Exception: pass

    @commands.command(name="delby", brief="Delete your messages by author pattern")
    async def delby(self, ctx, limit: int = 50):
        deleted = 0
        async for msg in ctx.channel.history(limit=limit * 3):
            if msg.author.id == self.bot.user.id:
                try: await msg.delete(); deleted += 1
                except Exception: pass
                if deleted >= limit: break
        m = await ctx.channel.send(S.ui_ok(f"deleted {deleted}"))
        import asyncio
        await asyncio.sleep(3)
        try: await m.delete()
        except Exception: pass

async def setup(bot): await bot.add_cog(SearchCog(bot))

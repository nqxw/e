# cogs/sniper.py
import asyncio, time, discord
import discord
from discord.ext import commands
from . import state as S
from .antid import jitter

class SniperCog(commands.Cog, name="sniper"):
    def __init__(self, bot):
        self.bot = bot
        self._ignore_users:    set = set()
        self._ignore_channels: set = set()

    @commands.command(name="snipereon", aliases=["sniperon"], brief="Enable sniper")
    async def sniper_on(self, ctx):
        S.SNIPER_ENABLED = True
        await ctx.message.edit(content=S.ui_ok("sniper → on"))

    @commands.command(name="snipereoff", aliases=["sniperoff"], brief="Disable sniper")
    async def sniper_off(self, ctx):
        S.SNIPER_ENABLED = False
        await ctx.message.edit(content=S.ui_ok("sniper → off"))

    @commands.command(name="snipestatus", brief="Sniper status")
    async def snipe_status(self, ctx):
        await ctx.message.edit(content=S.ui_box("sniper", [
            f"  {S.DIM}enabled{S.RESET}   {S.SNIPER_ENABLED}",
            f"  {S.DIM}nitro{S.RESET}     {S._nitrosniper_enabled}",
            f"  {S.DIM}giveaway{S.RESET}  {S._giveaway_enabled}",
        ]))


    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not S.SNIPER_ENABLED: return
        if int(message.author.id) in self._ignore_users: return
        if message.channel.id in self._ignore_channels: return
        S._snipe_cache[message.channel.id] = {
            "author":  str(message.author),
            "content": message.content or "[no text]",
            "time":    time.time(),
        }

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if not S.SNIPER_ENABLED: return
        if before.content == after.content: return
        S._editsnipe_cache[before.channel.id] = {
            "author": str(before.author),
            "before": before.content or "[no text]",
            "after":  after.content or "[no text]",
            "time":   time.time(),
        }

    @commands.Cog.listener()
    async def on_message(self, message):
        if not S._nitrosniper_enabled: return
        if message.author.id == self.bot.user.id: return
        import re, asyncio
        code_re = re.compile(r"discord\.gift/([a-zA-Z0-9]+)")
        for match in code_re.finditer(message.content or ""):
            code = match.group(1)
            await asyncio.sleep(jitter(1.8))
            import aiohttp
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    f"https://discord.com/api/v9/entitlements/gift-codes/{code}/redeem",
                    headers={"Authorization": S.TOKEN},
                    json={"channel_id": str(message.channel.id)}
                ) as r:
                    status = r.status
            notify = self.bot.get_channel(message.channel.id)
            if notify:
                if status in (200, 201):
                    await notify.send(S.ui_ok(f"nitro sniped! code: `{code}`"))
                elif status == 400:
                    await notify.send(S.ui_err(f"code already redeemed: `{code}`"))
                elif status == 429:
                    await notify.send(S.ui_warn(f"rate limited on: `{code}`"))


    @commands.command(name="snipehistory", aliases=["sh"], brief="Show snipe history")
    async def snipehistory(self, ctx, limit: int = 10):
        # All recent snipes from all channels
        all_snipes = sorted(S._snipe_cache.values(), key=lambda x: x.get("time",0), reverse=True)
        rows = [f"  {S.GREY}•{S.RESET} {s['author']}: {s['content'][:60]}" for s in all_snipes[:limit]]
        await ctx.message.edit(content=S._paginate("snipe history","",rows) if rows else S.ui_info("empty"))

    @commands.command(name="snipestats", brief="Sniper statistics")
    async def snipestats(self, ctx):
        await ctx.message.edit(content=S.ui_box("sniper stats", [
            f"  {S.DIM}enabled{S.RESET}    {S.SNIPER_ENABLED}",
            f"  {S.DIM}nitro{S.RESET}      {S._nitrosniper_enabled}",
            f"  {S.DIM}giveaway{S.RESET}   {S._giveaway_enabled}",
            f"  {S.DIM}cached{S.RESET}     {len(S._snipe_cache)} channels",
        ]))

    @commands.command(name="snipeclearcache", brief="Clear snipe cache")
    async def snipeclearcache(self, ctx):
        S._snipe_cache.clear(); S._editsnipe_cache.clear()
        await ctx.message.edit(content=S.ui_ok("snipe cache cleared"))

    @commands.command(name="snipeignore", brief="Ignore a user from sniper")
    async def snipeignore(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: snipeignore <@user>"))
        self._ignore_users.add(user.id)
        await ctx.message.edit(content=S.ui_ok(f"snipeignore → {user}"))

    @commands.command(name="snipesearch", brief="Search snipe cache")
    async def snipesearch(self, ctx, *, query: str = ""):
        if not query: return await ctx.message.edit(content=S.ui_err("usage: snipesearch <query>"))
        results = [s for s in S._snipe_cache.values() if query.lower() in s.get("content","").lower()]
        rows = [f"  {S.GREY}•{S.RESET} {s['author']}: {s['content'][:60]}" for s in results[:20]]
        await ctx.message.edit(content=S._paginate(f"snipe search: {query}","",rows) if rows else S.ui_info("no results"))

    @commands.command(name="giveaway", brief="Toggle giveaway sniper")
    async def giveaway(self, ctx, toggle: str = ""):
        S._giveaway_enabled = toggle.lower() not in ("off","disable","false") if toggle else not S._giveaway_enabled
        await ctx.message.edit(content=S.ui_ok(f"giveaway sniper → {'on' if S._giveaway_enabled else 'off'}"))


    @commands.command(name="esnipe", aliases=["editsnipe"], brief="Show last edited message")
    async def esnipe(self, ctx):
        entry = S._editsnipe_cache.get(ctx.channel.id)
        if not entry: return await ctx.message.edit(content=S.ui_info("nothing to snipe"))
        await ctx.message.edit(content=S.ui_box("edit snipe",[
            f"  {S.DIM}author{S.RESET}  {entry.get('author','?')}",
            f"  {S.DIM}before{S.RESET}  {entry.get('before','')[:100]}",
            f"  {S.DIM}after{S.RESET}   {entry.get('after','')[:100]}",
        ]))

    @commands.command(name="editsnipehistory", brief="Show edit snipe history")
    async def editsnipehistory(self, ctx):
        entries = list(S._editsnipe_cache.values())[-20:]
        rows = [f"  {S.GREY}•{S.RESET} {e.get('author','?')}: {e.get('before','')[:50]} → {e.get('after','')[:50]}"
                for e in entries]
        await ctx.message.edit(content=S._paginate("edit snipe history","",rows) if rows else S.ui_info("empty"))

    @commands.command(name="snipepage", brief="Page through snipe history  snipepage <n>")
    async def snipepage(self, ctx, page: int = 1):
        all_snipes = sorted(S._snipe_cache.values(), key=lambda x: x.get("time",0), reverse=True)
        per = 5; start = (page-1)*per; end = start+per
        chunk = all_snipes[start:end]
        rows = [f"  {S.GREY}{i+start+1}{S.RESET} {s.get('author','?')}: {s.get('content','')[:60]}"
                for i,s in enumerate(chunk)]
        await ctx.message.edit(content=S._paginate(f"snipes p{page}","",rows) if rows else S.ui_info("end"))

    @commands.command(name="snipetimestamp", brief="Show timestamp of last sniped message")
    async def snipetimestamp(self, ctx):
        import time as _t
        entry = S._snipe_cache.get(ctx.channel.id)
        if not entry: return await ctx.message.edit(content=S.ui_info("nothing"))
        ts = entry.get("time",0)
        await ctx.message.edit(content=S.ui_ok(f"sniped at: {_t.strftime('%Y-%m-%d %H:%M:%S', _t.localtime(ts))}"))

    @commands.command(name="snipereactions", brief="Show reactions on last sniped message")
    async def snipereactions(self, ctx):
        entry = S._snipe_cache.get(ctx.channel.id)
        if not entry: return await ctx.message.edit(content=S.ui_info("nothing"))
        reactions = entry.get("reactions",[])
        rows = [f"  {S.GREY}•{S.RESET} {r}" for r in reactions]
        await ctx.message.edit(content=S._paginate("snipe reactions","",rows) if rows else S.ui_info("no reactions"))

    @commands.command(name="snipeembeds", brief="Show embed count on last sniped message")
    async def snipeembeds(self, ctx):
        entry = S._snipe_cache.get(ctx.channel.id)
        if not entry: return await ctx.message.edit(content=S.ui_info("nothing"))
        await ctx.message.edit(content=S.ui_ok(f"embeds: {entry.get('embed_count',0)}"))

    @commands.command(name="snipeattachments", brief="Show attachments on last sniped message")
    async def snipeattachments(self, ctx):
        entry = S._snipe_cache.get(ctx.channel.id)
        if not entry: return await ctx.message.edit(content=S.ui_info("nothing"))
        atts = entry.get("attachments",[])
        rows = [f"  {S.GREY}•{S.RESET} {a}" for a in atts]
        await ctx.message.edit(content=S._paginate("attachments","",rows) if rows else S.ui_info("none"))

    @commands.command(name="snipefilter", brief="Filter snipe cache by keyword")
    async def snipefilter(self, ctx, *, query: str = ""):
        if not query: return await ctx.message.edit(content=S.ui_err("usage: snipefilter <query>"))
        results = [s for s in S._snipe_cache.values() if query.lower() in s.get("content","").lower()]
        rows = [f"  {S.GREY}•{S.RESET} {s.get('author','?')}: {s.get('content','')[:60]}" for s in results]
        await ctx.message.edit(content=S._paginate(f"filter: {query}","",rows) if rows else S.ui_info("none"))

    @commands.command(name="snipeclearuser", brief="Clear snipes from a user")
    async def snipeclearuser(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: snipeclearuser <@user>"))
        before = len(S._snipe_cache)
        S._snipe_cache = {k:v for k,v in S._snipe_cache.items() if v.get("author_id") != user.id}
        after = len(S._snipe_cache)
        await ctx.message.edit(content=S.ui_ok(f"cleared {before-after} snipes from {user}"))

    @commands.command(name="snipeclearchannel", brief="Clear snipes in current channel")
    async def snipeclearchannel(self, ctx):
        S._snipe_cache.pop(ctx.channel.id,None)
        S._editsnipe_cache.pop(ctx.channel.id,None)
        await ctx.message.edit(content=S.ui_ok("channel snipe cache cleared"))

    @commands.command(name="snipeclearserver", brief="Clear all snipes in server")
    @commands.guild_only()
    async def snipeclearserver(self, ctx):
        ch_ids = {c.id for c in ctx.guild.channels}
        before = len(S._snipe_cache)
        S._snipe_cache = {k:v for k,v in S._snipe_cache.items() if k not in ch_ids}
        await ctx.message.edit(content=S.ui_ok(f"cleared {before-len(S._snipe_cache)} server snipes"))

async def setup(bot): await bot.add_cog(SniperCog(bot))

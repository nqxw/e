# cogs/pingtrack.py
import discord
from discord.ext import commands
from . import state as S
from collections import defaultdict

_pings: dict = defaultdict(list)  # user_id -> [messages]

class PingTrackCog(commands.Cog, name="pingtrack"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="pinglog", brief="Show recent pings/mentions")
    async def pinglog(self, ctx, n: int = 10):
        all_pings = []
        for uid, msgs in _pings.items():
            all_pings.extend(msgs)
        all_pings.sort(key=lambda x: x["time"], reverse=True)
        rows = [f"  {S.GREY}•{S.RESET} {p['author']} in #{p['channel']}: {p['content'][:60]}"
                for p in all_pings[:n]]
        await ctx.message.edit(content=S._paginate("ping log","",rows) if rows else S.ui_info("no pings"))

    @commands.command(name="pingclear", brief="Clear ping log")
    async def pingclear(self, ctx):
        _pings.clear()
        await ctx.message.edit(content=S.ui_ok("ping log cleared"))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.user.id: return
        if not self.bot.user: return
        if self.bot.user in message.mentions:
            _pings[message.author.id].append({
                "author":  str(message.author),
                "channel": getattr(message.channel, "name", "DM"),
                "content": message.content or "[no text]",
                "time":    message.created_at.timestamp(),
            })
            if len(_pings[message.author.id]) > 50:
                _pings[message.author.id] = _pings[message.author.id][-50:]


    @commands.command(name="pingtrack", brief="Toggle ping tracking")
    async def pingtrack(self, ctx, toggle: str = ""):
        S._ping_tracking = toggle.lower() not in ("off","disable") if toggle else not getattr(S,"_ping_tracking",False)
        await ctx.message.edit(content=S.ui_ok(f"ping tracking → {'on' if S._ping_tracking else 'off'}"))

    @commands.command(name="pingcount", brief="Show ping counts")
    async def pingcount(self, ctx):
        pings = getattr(S,"_ping_log",[])
        await ctx.message.edit(content=S.ui_box("pings", [
            f"  {S.DIM}total{S.RESET}  {len(pings)}",
            f"  {S.DIM}last{S.RESET}   {pings[-1] if pings else '—'}",
        ]))

    @commands.command(name="pingreset", brief="Reset ping log")
    async def pingreset(self, ctx):
        if hasattr(S,"_ping_log"): S._ping_log.clear()
        await ctx.message.edit(content=S.ui_ok("ping log cleared"))

    @commands.command(name="pingtop", brief="Top users who pinged you")
    async def pingtop(self, ctx):
        log = getattr(S,"_ping_log",[])
        from collections import Counter
        counts = Counter(e.get("author") for e in log if isinstance(e,dict))
        rows = [f"  {S.GREY}•{S.RESET} {u}  {n}" for u,n in counts.most_common(10)]
        await ctx.message.edit(content=S._paginate("ping top","",rows) if rows else S.ui_info("empty"))

    @commands.command(name="mentionlog", brief="Show recent mention log")
    async def mentionlog(self, ctx):
        log = getattr(S,"_ping_log",[])
        rows = [f"  {S.GREY}•{S.RESET} {e}" if isinstance(e,str) else
                f"  {S.GREY}•{S.RESET} {e.get('author','?')}: {e.get('content','')[:60]}"
                for e in log[-20:]]
        await ctx.message.edit(content=S._paginate("mention log","",rows) if rows else S.ui_info("empty"))

async def setup(bot): await bot.add_cog(PingTrackCog(bot))

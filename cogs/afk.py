# cogs/afk.py
import time, asyncio, discord
from discord.ext import commands
from . import state as S
import asyncio

class AfkCog(commands.Cog, name="afk"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="afk", brief="Set AFK status")
    async def afk_set(self, ctx, *, msg: str = "AFK"):
        S.afk["enabled"] = True
        S.afk["message"] = msg
        S.afk["expires_at"] = 0
        await ctx.message.edit(content=S.ui_ok(f"AFK set: {msg}"))

    @commands.command(name="afkstop", aliases=["unafk"], brief="Disable AFK")
    async def afk_stop(self, ctx):
        S.afk["enabled"] = False
        S.afk["message"] = ""
        await ctx.message.edit(content=S.ui_ok("AFK disabled"))

    @commands.command(name="afkstatus", brief="Show AFK status")
    async def afk_status(self, ctx):
        rows = [
            f"  {S.DIM}enabled{S.RESET}  {S.afk['enabled']}",
            f"  {S.DIM}message{S.RESET}  {S.afk['message'] or '—'}",
            f"  {S.DIM}dm_only{S.RESET}  {S.afk['dm_only']}",
        ]
        await ctx.message.edit(content=S.ui_box("afk", rows))

    @commands.Cog.listener()
    async def on_message(self, message):
        if not S.afk["enabled"]: return
        if message.author.id == self.bot.user.id: return
        mentions = message.mentions or []
        if not any(m.id == self.bot.user.id for m in mentions): return
        uid = str(message.author.id)
        last = S.afk["last_reply"].get(uid, 0)
        if time.time() - last < S.afk["cooldown"]: return
        S.afk["last_reply"][uid] = time.time()
        try: await message.channel.send(S.ui_info(S.afk["message"]))
        except Exception: pass


    @commands.command(name="afkwhitelist", brief="Whitelist a user from AFK replies")
    async def afkwhitelist(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: afkwhitelist <@user>"))
        S.afk["whitelist"].add(user.id)
        await ctx.message.edit(content=S.ui_ok(f"whitelisted {user}"))

    @commands.command(name="afkblacklist", brief="Blacklist a user from AFK replies")
    async def afkblacklist(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: afkblacklist <@user>"))
        S.afk["blacklist"].add(user.id)
        await ctx.message.edit(content=S.ui_ok(f"blacklisted {user}"))

    @commands.command(name="afkignore", aliases=["afkignorelist"], brief="List AFK ignore list")
    async def afkignore(self, ctx):
        rows = [f"  {S.GREY}•{S.RESET} {uid}" for uid in S.afk["blacklist"]]
        await ctx.message.edit(content=S._paginate("afk blacklist","",rows) if rows else S.ui_info("empty"))

    @commands.command(name="afkdmonly", brief="AFK in DMs only toggle")
    async def afkdmonly(self, ctx, toggle: str = ""):
        S.afk["dm_only"] = toggle.lower() not in ("off","disable")
        await ctx.message.edit(content=S.ui_ok(f"AFK DM-only → {S.afk['dm_only']}"))

    @commands.command(name="afkemergency", brief="Emergency AFK (reply to everyone)")
    async def afkemergency(self, ctx, *, msg: str = "Emergency AFK"):
        S.afk["enabled"] = True; S.afk["emergency"] = True; S.afk["message"] = msg
        await ctx.message.edit(content=S.ui_ok(f"Emergency AFK: {msg}"))

    @commands.command(name="afkcooldown", brief="Set AFK reply cooldown")
    async def afkcooldown(self, ctx, seconds: int = 30):
        S.afk["cooldown"] = seconds
        await ctx.message.edit(content=S.ui_ok(f"AFK cooldown → {seconds}s"))

    @commands.command(name="afkexpire", brief="Set AFK auto-expire time")
    async def afkexpire(self, ctx, minutes: int = 0):
        import time
        S.afk["expires_at"] = time.time() + minutes*60 if minutes > 0 else 0
        await ctx.message.edit(content=S.ui_ok(f"AFK expires in {minutes}m" if minutes else "AFK no expiry"))

    @commands.command(name="afkcustom", brief="Set custom AFK reply for a user")
    async def afkcustom(self, ctx, user: discord.User = None, *, reply: str = ""):
        if not user or not reply: return await ctx.message.edit(content=S.ui_err("usage: afkcustom <@user> <reply>"))
        S.afk["custom_replies"][str(user.id)] = reply
        await ctx.message.edit(content=S.ui_ok(f"custom reply for {user}: {reply[:40]}"))

    @commands.command(name="afkpingcount", brief="Show ping count while AFK")
    async def afkpingcount(self, ctx):
        total = sum(S.afk["ping_counter"].values())
        rows = [f"  {S.GREY}•{S.RESET} {uid}: {n}" for uid,n in sorted(S.afk["ping_counter"].items(), key=lambda x:-x[1])[:10]]
        await ctx.message.edit(content=S.ui_box(f"pings while AFK ({total} total)", rows))

    @commands.command(name="afkreturn", brief="Return from AFK")
    async def afkreturn(self, ctx):
        S.afk["enabled"] = False; S.afk["emergency"] = False
        S.afk["ping_counter"].clear(); S.afk["last_reply"].clear()
        await ctx.message.edit(content=S.ui_ok("AFK cleared — welcome back"))

    @commands.command(name="afkserver", brief="Server-specific AFK message")
    async def afkserver(self, ctx, *, msg: str = ""):
        if not ctx.guild: return await ctx.message.edit(content=S.ui_err("server only"))
        gid = str(ctx.guild.id)
        if msg:
            S.afk["per_server"][gid] = msg
            await ctx.message.edit(content=S.ui_ok(f"server AFK → {msg}"))
        else:
            S.afk["per_server"].pop(gid, None)
            await ctx.message.edit(content=S.ui_ok("server AFK cleared"))

async def setup(bot): await bot.add_cog(AfkCog(bot))

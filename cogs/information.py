# cogs/information.py
import aiohttp, discord
from discord.ext import commands
from . import state as S

def _snowflake_ts(uid):
    from datetime import datetime
    try:
        ts = ((int(uid) >> 22) + 1420070400000) / 1000
        return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except: return "?"

def _av(uid, av):
    if not av: return "none"
    ext = "gif" if str(av).startswith("a_") else "png"
    return f"https://cdn.discordapp.com/avatars/{uid}/{av}.{ext}?size=512"

class InformationCog(commands.Cog, name="information"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="userinfo", aliases=["ui"], brief="User information")
    @commands.guild_only()
    async def userinfo(self, ctx, user: discord.User = None):
        u = user or ctx.author
        rows = [
            f"  {S.DIM}tag{S.RESET}      {u}",
            f"  {S.DIM}id{S.RESET}       {u.id}",
            f"  {S.DIM}created{S.RESET}  {_snowflake_ts(u.id)}",
            f"  {S.DIM}avatar{S.RESET}   {_av(u.id, u.avatar)}",
            f"  {S.DIM}bot{S.RESET}      {'yes' if u.bot else 'no'}",
            f"  {S.DIM}flags{S.RESET}    {u.public_flags.value if hasattr(u,'public_flags') else 0}",
        ]
        if ctx.guild:
            m = ctx.guild.get_member(u.id)
            if m and m.nick:
                rows.append(f"  {S.DIM}nick{S.RESET}     {m.nick}")
            if m and m.joined_at:
                rows.append(f"  {S.DIM}joined{S.RESET}   {m.joined_at.strftime('%Y-%m-%d')}")
        await ctx.message.edit(content=S.ui_box("user info", rows))

    @commands.command(name="avatar", aliases=["av","pfp"], brief="Show user avatar")
    async def avatar(self, ctx, user: discord.User = None):
        u = user or ctx.author
        url = str(u.display_avatar.url) if u.display_avatar else "no avatar"
        await ctx.message.edit(content=url)

    @commands.command(name="serverinfo", aliases=["si"], brief="Server information")
    @commands.guild_only()
    async def serverinfo(self, ctx):
        g = ctx.guild
        rows = [
            f"  {S.DIM}name{S.RESET}     {g.name}",
            f"  {S.DIM}id{S.RESET}       {g.id}",
            f"  {S.DIM}owner{S.RESET}    {g.owner}",
            f"  {S.DIM}members{S.RESET}  {g.member_count}",
            f"  {S.DIM}channels{S.RESET} {len(g.channels)}",
            f"  {S.DIM}roles{S.RESET}    {len(g.roles)}",
            f"  {S.DIM}created{S.RESET}  {_snowflake_ts(g.id)}",
            f"  {S.DIM}boost{S.RESET}    {g.premium_subscription_count} boosts (tier {g.premium_tier})",
        ]
        await ctx.message.edit(content=S.ui_box("server info", rows))

    @commands.command(name="channelinfo", aliases=["ci"], brief="Channel information")
    async def channelinfo(self, ctx, ch: discord.TextChannel = None):
        c = ch or ctx.channel
        rows = [
            f"  {S.DIM}name{S.RESET}    #{c.name}",
            f"  {S.DIM}id{S.RESET}      {c.id}",
            f"  {S.DIM}created{S.RESET} {_snowflake_ts(c.id)}",
        ]
        if hasattr(c, "topic") and c.topic:
            rows.append(f"  {S.DIM}topic{S.RESET}   {c.topic[:80]}")
        await ctx.message.edit(content=S.ui_box("channel info", rows))

    @commands.command(name="checkname", brief="Check username availability")
    async def checkname(self, ctx, username: str = ""):
        if not username:
            return await ctx.message.edit(content=S.ui_err("usage: checkname <username>"))
        h = {"Authorization": S.TOKEN, "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as s:
            async with s.post("https://discord.com/api/v9/users/@me/pomelo-attempt",
                              headers=h, json={"username": username}) as r:
                if r.status == 200:
                    d = await r.json()
                    taken = d.get("taken", True)
                    msg = S.ui_ok(f"`{username}` is available") if not taken \
                          else S.ui_err(f"`{username}` is taken")
                else:
                    msg = S.ui_err(f"check failed ({r.status})")
        await ctx.message.edit(content=msg)


    @commands.command(name="whois", brief="Deep profile lookup via API")
    async def whois(self, ctx, user: discord.User = None):
        uid = user.id if user else ctx.author.id
        gid = ctx.guild.id if ctx.guild else None
        h = {"Authorization": S.TOKEN, "User-Agent": S.USER_AGENT}
        params = {"with_mutual_guilds":"true","with_mutual_friends_count":"true"}
        if gid: params["guild_id"] = str(gid)
        import aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://discord.com/api/v9/users/{uid}/profile",
                             headers=h, params=params) as r:
                if r.status != 200:
                    return await ctx.message.edit(content=S.ui_err(f"not found ({r.status}) — no mutual server"))
                p = await r.json(content_type=None)
        u = p.get("user",{}) or {}
        prof = p.get("user_profile",{}) or {}
        badges = [b.get("id","") for b in p.get("badges",[]) if isinstance(b,dict)]
        rows = [
            f"  {S.DIM}username{S.RESET}       {u.get('username','?')}",
            f"  {S.DIM}id{S.RESET}             {uid}",
            f"  {S.DIM}bio{S.RESET}            {(prof.get('bio','') or '-')[:80]}",
            f"  {S.DIM}pronouns{S.RESET}       {prof.get('pronouns','') or '-'}",
            f"  {S.DIM}badges{S.RESET}         {', '.join(badges) or 'none'}",
            f"  {S.DIM}nitro{S.RESET}          {'yes' if p.get('premium_since') else 'no'}",
            f"  {S.DIM}mutual servers{S.RESET} {len(p.get('mutual_guilds',[]) or [])}",
        ]
        await ctx.message.edit(content=S.ui_box("whois", rows))

async def setup(bot):
    await bot.add_cog(InformationCog(bot))

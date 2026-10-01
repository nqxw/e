# cogs/lastfm.py
import aiohttp
from discord.ext import commands
from . import state as S

class LastfmCog(commands.Cog, name="lastfm"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="lfmset", brief="Set Last.fm username")
    async def lfmset(self, ctx, username: str = ""):
        if not username: return await ctx.message.edit(content=S.ui_err("usage: lfmset <username>"))
        cfg = S.load_config(); cfg["lastfm_user"] = username; S.save_config(cfg)
        await ctx.message.edit(content=S.ui_ok(f"Last.fm user → {username}"))

    @commands.command(name="np", aliases=["nowplaying"], brief="Now playing on Last.fm")
    async def np(self, ctx):
        cfg = S.load_config()
        user = cfg.get("lastfm_user","")
        key  = cfg.get("lastfm_key","")
        if not user: return await ctx.message.edit(content=S.ui_err("set user with lfmset first"))
        url = (f"{S.LASTFM_BASE}?method=user.getrecenttracks&user={user}"
               f"&api_key={key or 'demo'}&format=json&limit=1")
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return await ctx.message.edit(content=S.ui_err(f"lastfm error ({r.status})"))
                d = await r.json()
        tracks = d.get("recenttracks", {}).get("track", [])
        if not tracks: return await ctx.message.edit(content=S.ui_info("no recent tracks"))
        t = tracks[0]
        now_playing = t.get("@attr", {}).get("nowplaying") == "true"
        name   = t.get("name","?")
        artist = t.get("artist", {}).get("#text","?")
        album  = t.get("album",  {}).get("#text","")
        rows = [
            f"  {S.DIM}track{S.RESET}   {name}",
            f"  {S.DIM}artist{S.RESET}  {artist}",
        ]
        if album: rows.append(f"  {S.DIM}album{S.RESET}   {album}")
        rows.append(f"  {S.DIM}status{S.RESET}  {'▶ now playing' if now_playing else 'last played'}")
        await ctx.message.edit(content=S.ui_box(f"last.fm — {user}", rows))


    @commands.command(name="lastfm", brief="Show Last.fm now playing  lastfm <username>")
    async def lastfm(self, ctx, username: str = ""):
        if not username: return await ctx.message.edit(content=S.ui_err("usage: lastfm <username>"))
        import aiohttp
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={username}&api_key=d94e5b6e7a7e5c7e8d3a0e2a7f1b9d3a&format=json&limit=1"
                ) as r:
                    if r.status == 200:
                        d = await r.json()
                        tracks = d.get("recenttracks",{}).get("track",[])
                        if tracks:
                            t = tracks[0]
                            artist = t.get("artist",{}).get("#text","?")
                            name = t.get("name","?")
                            now = bool(t.get("@attr",{}).get("nowplaying"))
                            await ctx.message.edit(content=S.ui_ok(f"{'🎵 ' if now else ''}{artist} — {name}"))
                        else:
                            await ctx.message.edit(content=S.ui_info("no recent tracks"))
                    else:
                        await ctx.message.edit(content=S.ui_err(f"API error {r.status} — set API key first"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

async def setup(bot): await bot.add_cog(LastfmCog(bot))

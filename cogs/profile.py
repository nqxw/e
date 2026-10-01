# cogs/profile.py
import aiohttp, discord
from discord.ext import commands
from . import state as S

def _h(): return {"Authorization": S.TOKEN, "Content-Type": "application/json", "User-Agent": S.USER_AGENT}

class ProfileCog(commands.Cog, name="profile"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="setbio", brief="Set profile bio")
    async def setbio(self, ctx, *, bio: str = ""):
        async with aiohttp.ClientSession() as s:
            async with s.patch("https://discord.com/api/v9/users/@me/profile",
                               headers=_h(), json={"bio": bio}) as r:
                if r.status in (200, 204):
                    await ctx.message.edit(content=S.ui_ok(f"bio set ({len(bio)} chars)"))
                else:
                    await ctx.message.edit(content=S.ui_err(f"failed ({r.status})"))

    @commands.command(name="setpronouns", brief="Set pronouns")
    async def setpronouns(self, ctx, *, pronouns: str = ""):
        async with aiohttp.ClientSession() as s:
            async with s.patch("https://discord.com/api/v9/users/@me/profile",
                               headers=_h(), json={"pronouns": pronouns}) as r:
                if r.status in (200, 204):
                    await ctx.message.edit(content=S.ui_ok(f"pronouns → {pronouns or 'cleared'}"))
                else:
                    await ctx.message.edit(content=S.ui_err(f"failed ({r.status})"))

    @commands.command(name="setbanner", brief="Set profile banner by URL")
    async def setbanner(self, ctx, url: str = ""):
        if not url: return await ctx.message.edit(content=S.ui_err("usage: setbanner <image_url>"))
        import base64, aiohttp as _ah
        async with _ah.ClientSession() as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return await ctx.message.edit(content=S.ui_err("failed to fetch image"))
                data = await r.read()
                ct = r.headers.get("content-type","image/png")
        b64 = f"data:{ct};base64," + base64.b64encode(data).decode()
        async with aiohttp.ClientSession() as s:
            async with s.patch("https://discord.com/api/v9/users/@me",
                               headers=_h(), json={"banner": b64}) as r:
                if r.status in (200, 204):
                    await ctx.message.edit(content=S.ui_ok("banner updated"))
                else:
                    await ctx.message.edit(content=S.ui_err(f"failed ({r.status})"))

    @commands.command(name="setavatar", aliases=["setpfp"], brief="Set avatar by URL")
    async def setavatar(self, ctx, url: str = ""):
        if not url: return await ctx.message.edit(content=S.ui_err("usage: setavatar <image_url>"))
        import base64, aiohttp as _ah
        async with _ah.ClientSession() as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return await ctx.message.edit(content=S.ui_err("failed to fetch image"))
                data = await r.read()
                ct = r.headers.get("content-type","image/png")
        b64 = f"data:{ct};base64," + base64.b64encode(data).decode()
        await self.bot.user.edit(avatar=base64.b64decode(b64.split(",")[1]))
        await ctx.message.edit(content=S.ui_ok("avatar updated"))

    @commands.command(name="setusername", brief="Change username")
    async def setusername(self, ctx, *, name: str = ""):
        if not name: return await ctx.message.edit(content=S.ui_err("usage: setusername <name>"))
        await self.bot.user.edit(username=name)
        await ctx.message.edit(content=S.ui_ok(f"username → {name}"))


    @commands.command(name="accountbackup", brief="Backup account info to file")
    async def accountbackup(self, ctx):
        import json, os, aiohttp
        h = {"Authorization": S.TOKEN, "User-Agent": S.USER_AGENT}
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://discord.com/api/v9/users/@me", headers=h) as r:
                    data = await r.json() if r.status==200 else {}
            os.makedirs("exports",exist_ok=True)
            path = f"exports/account_{data.get('id','unknown')}.json"
            with open(path,"w") as f: json.dump(data,f,indent=2)
            await ctx.message.edit(content=S.ui_ok(f"backup saved → {path}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="myprofile", brief="Show your own profile")
    async def myprofile(self, ctx):
        import aiohttp
        h = {"Authorization": S.TOKEN, "User-Agent": S.USER_AGENT}
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://discord.com/api/v9/users/@me", headers=h) as r:
                    u = await r.json() if r.status==200 else {}
            await ctx.message.edit(content=S.ui_box("my profile",[
                f"  {S.DIM}username{S.RESET}  {u.get('username','?')}",
                f"  {S.DIM}id{S.RESET}        {u.get('id','?')}",
                f"  {S.DIM}nitro{S.RESET}     {bool(u.get('premium_type'))}",
                f"  {S.DIM}email{S.RESET}     {u.get('email','hidden')}",
                f"  {S.DIM}phone{S.RESET}     {bool(u.get('phone'))}",
                f"  {S.DIM}mfa{S.RESET}       {bool(u.get('mfa_enabled'))}",
            ]))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

async def setup(bot): await bot.add_cog(ProfileCog(bot))

# cogs/social.py
import aiohttp, discord
from discord.ext import commands
from . import state as S
import asyncio

def _h(): return {"Authorization": S.TOKEN, "User-Agent": S.USER_AGENT, "Content-Type": "application/json"}

class SocialCog(commands.Cog, name="social"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="addfriend", brief="Send friend request")
    async def addfriend(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: addfriend <@user>"))
        async with aiohttp.ClientSession() as s:
            async with s.put(f"https://discord.com/api/v9/users/@me/relationships/{user.id}",
                             headers=_h(), json={"type": 1}) as r:
                if r.status in (200, 201, 204):
                    await ctx.message.edit(content=S.ui_ok(f"friend request sent to {user}"))
                else:
                    await ctx.message.edit(content=S.ui_err(f"failed ({r.status})"))

    @commands.command(name="removefriend", aliases=["unfriend"], brief="Remove friend")
    async def removefriend(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: removefriend <@user>"))
        async with aiohttp.ClientSession() as s:
            async with s.delete(f"https://discord.com/api/v9/users/@me/relationships/{user.id}",
                                headers=_h()) as r:
                if r.status in (200, 204):
                    await ctx.message.edit(content=S.ui_ok(f"removed {user}"))
                else:
                    await ctx.message.edit(content=S.ui_err(f"failed ({r.status})"))

    @commands.command(name="friends", brief="List friends")
    async def friends(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get("https://discord.com/api/v9/users/@me/relationships",
                             headers=_h()) as r:
                if r.status == 200:
                    data = await r.json()
                    friends = [d for d in data if d.get("type") == 1]
                    rows = [f"  {S.GREY}•{S.RESET} {d['user']['username']}" for d in friends]
                    await ctx.message.edit(content=S._paginate(f"friends ({len(friends)})","",rows)
                                           if rows else S.ui_info("no friends"))
                else:
                    await ctx.message.edit(content=S.ui_err(f"failed ({r.status})"))

    @commands.command(name="block", brief="Block a user")
    async def block(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: block <@user>"))
        async with aiohttp.ClientSession() as s:
            async with s.put(f"https://discord.com/api/v9/users/@me/relationships/{user.id}",
                             headers=_h(), json={"type": 2}) as r:
                if r.status in (200, 201, 204):
                    await ctx.message.edit(content=S.ui_ok(f"blocked {user}"))
                else:
                    await ctx.message.edit(content=S.ui_err(f"failed ({r.status})"))


    async def _rels(self):
        import aiohttp
        h = {"Authorization": S.TOKEN, "User-Agent": S.USER_AGENT}
        async with aiohttp.ClientSession() as s:
            async with s.get("https://discord.com/api/v9/users/@me/relationships", headers=h) as r:
                return await r.json() if r.status == 200 else []

    @commands.command(name="friendcount", brief="Show friend/block/pending counts")
    async def friendcount(self, ctx):
        rels = await self._rels()
        await ctx.message.edit(content=S.ui_box("friends", [
            f"  {S.DIM}friends{S.RESET}  {sum(1 for x in rels if x.get('type')==1)}",
            f"  {S.DIM}blocked{S.RESET}  {sum(1 for x in rels if x.get('type')==2)}",
            f"  {S.DIM}pending{S.RESET}  {sum(1 for x in rels if x.get('type')==3)}",
        ]))

    @commands.command(name="blocked", brief="List blocked users")
    async def blocked(self, ctx):
        rels = await self._rels()
        rows = [f"  {S.GREY}•{S.RESET} {x.get('user',{}).get('username','?')}  {S.DIM}({x.get('user',{}).get('id')}){S.RESET}"
                for x in rels if x.get("type") == 2]
        await ctx.message.edit(content=S._paginate("blocked","",rows) if rows else S.ui_info("none"))

    @commands.command(name="pending", brief="List pending friend requests")
    async def pending(self, ctx):
        rels = await self._rels()
        rows = [f"  {S.GREY}•{S.RESET} {x.get('user',{}).get('username','?')}  {S.DIM}({x.get('user',{}).get('id')}){S.RESET}"
                for x in rels if x.get("type") == 3]
        await ctx.message.edit(content=S._paginate("pending","",rows) if rows else S.ui_info("none"))

    @commands.command(name="clearincoming", brief="Decline all incoming friend requests")
    async def clearincoming(self, ctx):
        import aiohttp, asyncio as _a
        rels = await self._rels()
        incoming = [x for x in rels if x.get("type") == 3]
        h = {"Authorization": S.TOKEN, "User-Agent": S.USER_AGENT}
        async with aiohttp.ClientSession() as s:
            for rel in incoming:
                uid = rel.get("user",{}).get("id")
                if uid: await s.delete(f"https://discord.com/api/v9/users/@me/relationships/{uid}",headers=h)
                await _a.sleep(0.3)
        await ctx.message.edit(content=S.ui_ok(f"declined {len(incoming)}"))

    @commands.command(name="clearoutgoing", brief="Cancel all outgoing friend requests")
    async def clearoutgoing(self, ctx):
        import aiohttp, asyncio as _a
        rels = await self._rels()
        outgoing = [x for x in rels if x.get("type") == 4]
        h = {"Authorization": S.TOKEN, "User-Agent": S.USER_AGENT}
        async with aiohttp.ClientSession() as s:
            for rel in outgoing:
                uid = rel.get("user",{}).get("id")
                if uid: await s.delete(f"https://discord.com/api/v9/users/@me/relationships/{uid}",headers=h)
                await _a.sleep(0.3)
        await ctx.message.edit(content=S.ui_ok(f"cancelled {len(outgoing)}"))

    @commands.command(name="unblock", brief="Unblock a user by ID")
    async def unblock_user(self, ctx, user_id: str = ""):
        if not user_id: return await ctx.message.edit(content=S.ui_err("usage: unblock <user_id>"))
        import aiohttp
        h = {"Authorization": S.TOKEN, "User-Agent": S.USER_AGENT}
        async with aiohttp.ClientSession() as s:
            async with s.delete(f"https://discord.com/api/v9/users/@me/relationships/{user_id}", headers=h) as r:
                await ctx.message.edit(content=S.ui_ok(f"unblocked {user_id}") if r.status in (200,204)
                                       else S.ui_err(f"failed {r.status}"))

    @commands.command(name="closedms", brief="Close all open DM channels")
    async def closedms(self, ctx):
        import aiohttp, asyncio as _a
        h = {"Authorization": S.TOKEN, "User-Agent": S.USER_AGENT}
        count = 0
        async with aiohttp.ClientSession() as s:
            for ch in list(self.bot.private_channels):
                await s.delete(f"https://discord.com/api/v9/channels/{ch.id}", headers=h)
                count += 1; await _a.sleep(0.3)
        await ctx.message.edit(content=S.ui_ok(f"closed {count}"))

    @commands.command(name="readdms", brief="Mark all DMs as read")
    async def readdms(self, ctx):
        import aiohttp, asyncio as _a
        h = {"Authorization": S.TOKEN, "Content-Type": "application/json", "User-Agent": S.USER_AGENT}
        count = 0
        async with aiohttp.ClientSession() as s:
            for ch in list(self.bot.private_channels):
                await s.post(f"https://discord.com/api/v9/channels/{ch.id}/ack", headers=h, json={})
                count += 1; await _a.sleep(0.2)
        await ctx.message.edit(content=S.ui_ok(f"read {count}"))

async def setup(bot): await bot.add_cog(SocialCog(bot))

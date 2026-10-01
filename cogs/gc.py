# cogs/gc.py
import discord
from discord.ext import commands
from . import state as S

class GroupChatCog(commands.Cog, name="gc"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="gcleave", brief="Leave a group DM")
    async def gcleave(self, ctx):
        if isinstance(ctx.channel, discord.GroupChannel):
            await ctx.channel.leave()
        else:
            await ctx.message.edit(content=S.ui_err("not in a group DM"))

    @commands.command(name="gcname", brief="Rename group DM")
    async def gcname(self, ctx, *, name: str = ""):
        if isinstance(ctx.channel, discord.GroupChannel):
            await ctx.channel.edit(name=name)
            await ctx.message.edit(content=S.ui_ok(f"group renamed → {name}"))
        else:
            await ctx.message.edit(content=S.ui_err("not in a group DM"))


    @commands.Cog.listener()
    async def on_group_join(self, channel, user):
        if not S._agc_state["enabled"]: return
        if user.id == self.bot.user.id:
            try: await channel.leave()
            except Exception: pass


    @commands.command(name="gccreate", brief="Create a group DM with users")
    async def gccreate(self, ctx, *users: discord.User):
        if not users: return await ctx.message.edit(content=S.ui_err("usage: gccreate <@user1> <@user2>..."))
        try:
            import aiohttp
            h = {"Authorization": S.TOKEN, "Content-Type": "application/json", "User-Agent": S.USER_AGENT}
            recipient_ids = [str(u.id) for u in users]
            async with aiohttp.ClientSession() as s:
                async with s.post("https://discord.com/api/v9/users/@me/channels",
                                  headers=h, json={"recipients": recipient_ids}) as r:
                    if r.status in (200,201):
                        data = await r.json()
                        await ctx.message.edit(content=S.ui_ok(f"group created: {data.get('id')}"))
                    else:
                        await ctx.message.edit(content=S.ui_err(f"failed {r.status}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="gclist", brief="List group DM channels")
    async def gclist(self, ctx):
        import discord as _d
        groups = [c for c in self.bot.private_channels if isinstance(c, _d.GroupChannel)]
        rows = [f"  {S.GREY}•{S.RESET} {getattr(c,'name','?') or c.id}  {S.DIM}({c.id}){S.RESET}"
                for c in groups]
        await ctx.message.edit(content=S._paginate("group DMs","",rows) if rows else S.ui_info("no groups"))

    @commands.command(name="gcadd", brief="Add user to current group DM")
    async def gcadd(self, ctx, user: discord.User = None):
        import discord as _d
        if not user: return await ctx.message.edit(content=S.ui_err("usage: gcadd <@user>"))
        if not isinstance(ctx.channel, _d.GroupChannel):
            return await ctx.message.edit(content=S.ui_err("not in a group DM"))
        try:
            await ctx.channel._add_recipient(user)
            await ctx.message.edit(content=S.ui_ok(f"added {user}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="gcremove", brief="Remove user from current group DM")
    async def gcremove(self, ctx, user: discord.User = None):
        import discord as _d
        if not user: return await ctx.message.edit(content=S.ui_err("usage: gcremove <@user>"))
        if not isinstance(ctx.channel, _d.GroupChannel):
            return await ctx.message.edit(content=S.ui_err("not in a group DM"))
        try:
            await ctx.channel._remove_recipient(user)
            await ctx.message.edit(content=S.ui_ok(f"removed {user}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="gcrename", brief="Rename current group DM")
    async def gcrename(self, ctx, *, name: str = ""):
        import discord as _d
        if not isinstance(ctx.channel, _d.GroupChannel):
            return await ctx.message.edit(content=S.ui_err("not in a group DM"))
        await ctx.channel.edit(name=name)
        await ctx.message.edit(content=S.ui_ok(f"renamed → {name or '(cleared)'}"))

    @commands.command(name="gcicon", brief="Set group DM icon from URL")
    async def gcicon(self, ctx, url: str = ""):
        import discord as _d, aiohttp
        if not isinstance(ctx.channel, _d.GroupChannel):
            return await ctx.message.edit(content=S.ui_err("not in a group DM"))
        if not url: return await ctx.message.edit(content=S.ui_err("usage: gcicon <url>"))
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r: img = await r.read()
        await ctx.channel.edit(icon=img)
        await ctx.message.edit(content=S.ui_ok("group icon updated"))

async def setup(bot): await bot.add_cog(GroupChatCog(bot))

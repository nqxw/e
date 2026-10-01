# cogs/server.py
import discord
from discord.ext import commands
from . import state as S
from .antid import batch_delay, shuffled

class ServerCog(commands.Cog, name="server"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="ban", brief="Ban a user")
    @commands.guild_only()
    async def ban(self, ctx, member: discord.Member = None, *, reason: str = "No reason"):
        if not member: return await ctx.message.edit(content=S.ui_err("usage: ban <@user> [reason]"))
        await member.ban(reason=reason)
        await ctx.message.edit(content=S.ui_ok(f"banned {member} — {reason}"))

    @commands.command(name="unban", brief="Unban a user")
    @commands.guild_only()
    async def unban(self, ctx, user_id: int = 0):
        if not user_id: return await ctx.message.edit(content=S.ui_err("usage: unban <user_id>"))
        try:
            await ctx.guild.unban(discord.Object(id=user_id))
            await ctx.message.edit(content=S.ui_ok(f"unbanned {user_id}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="kick", brief="Kick a user")
    @commands.guild_only()
    async def kick(self, ctx, member: discord.Member = None, *, reason: str = "No reason"):
        if not member: return await ctx.message.edit(content=S.ui_err("usage: kick <@user> [reason]"))
        await member.kick(reason=reason)
        await ctx.message.edit(content=S.ui_ok(f"kicked {member}"))

    @commands.command(name="membernick", brief="Change a member's nickname")
    @commands.guild_only()
    async def setnick(self, ctx, member: discord.Member = None, *, nick: str = ""):
        if not member: return await ctx.message.edit(content=S.ui_err("usage: setnick <@user> <nick>"))
        await member.edit(nick=nick or None)
        await ctx.message.edit(content=S.ui_ok(f"nick → {nick or 'cleared'}"))

    @commands.command(name="createrole", brief="Create a role")
    @commands.guild_only()
    async def createrole(self, ctx, *, name: str = "New Role"):
        r = await ctx.guild.create_role(name=name)
        await ctx.message.edit(content=S.ui_ok(f"created role: {r.mention}"))

    @commands.command(name="delrole", brief="Delete a role")
    @commands.guild_only()
    async def delrole(self, ctx, role: discord.Role = None):
        if not role: return await ctx.message.edit(content=S.ui_err("usage: delrole <@role>"))
        await role.delete()
        await ctx.message.edit(content=S.ui_ok(f"deleted role: {role.name}"))

    @commands.command(name="createchannel", aliases=["mkch"], brief="Create a text channel")
    @commands.guild_only()
    async def createchannel(self, ctx, *, name: str = "new-channel"):
        ch = await ctx.guild.create_text_channel(name)
        await ctx.message.edit(content=S.ui_ok(f"created {ch.mention}"))


    @commands.command(name="members", brief="List server members")
    @commands.guild_only()
    async def members(self, ctx, limit: int = 20):
        rows = [f"  {S.GREY}•{S.RESET} {m.display_name}  {S.DIM}({m.id}){S.RESET}"
                for m in list(ctx.guild.members)[:limit]]
        await ctx.message.edit(content=S._paginate("members", ctx.guild.name, rows))

    @commands.command(name="channels", brief="List server channels")
    @commands.guild_only()
    async def channels(self, ctx):
        rows = [f"  {S.GREY}•{S.RESET} #{ch.name}  {S.DIM}({ch.id}){S.RESET}"
                for ch in ctx.guild.channels]
        await ctx.message.edit(content=S._paginate("channels", ctx.guild.name, rows))


    @commands.command(name="mute", brief="Timeout a member (10 min)")
    @commands.guild_only()
    async def mute(self, ctx, member: discord.Member = None, minutes: int = 10):
        if not member: return await ctx.message.edit(content=S.ui_err("usage: mute <@member> [minutes]"))
        from datetime import timedelta
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=minutes))
        await ctx.message.edit(content=S.ui_ok(f"muted {member} for {minutes}m"))

    @commands.command(name="unmute", brief="Remove timeout from a member")
    @commands.guild_only()
    async def unmute(self, ctx, member: discord.Member = None):
        if not member: return await ctx.message.edit(content=S.ui_err("usage: unmute <@member>"))
        await member.timeout(None)
        await ctx.message.edit(content=S.ui_ok(f"unmuted {member}"))

    @commands.command(name="topic", brief="Set channel topic")
    @commands.guild_only()
    async def topic(self, ctx, *, text: str = ""):
        await ctx.channel.edit(topic=text)
        await ctx.message.edit(content=S.ui_ok(f"topic → {text or 'cleared'}"))

    @commands.command(name="slowmode", brief="Set slowmode seconds")
    @commands.guild_only()
    async def slowmode(self, ctx, seconds: int = 0):
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.message.edit(content=S.ui_ok(f"slowmode → {seconds}s"))


    @commands.command(name="servername", brief="Rename the server")
    @commands.guild_only()
    async def servername(self, ctx, *, name: str = ""):
        if not name: return await ctx.message.edit(content=S.ui_err("usage: servername <name>"))
        await ctx.guild.edit(name=name)
        await ctx.message.edit(content=S.ui_ok(f"server renamed → {name}"))

    @commands.command(name="servericon", brief="Set server icon by URL")
    @commands.guild_only()
    async def servericon(self, ctx, url: str = ""):
        if not url: return await ctx.message.edit(content=S.ui_err("usage: servericon <url>"))
        import aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r: img = await r.read()
        await ctx.guild.edit(icon=img)
        await ctx.message.edit(content=S.ui_ok("server icon updated"))

    @commands.command(name="serverbanner", brief="Set server banner by URL")
    @commands.guild_only()
    async def serverbanner(self, ctx, url: str = ""):
        if not url: return await ctx.message.edit(content=S.ui_err("usage: serverbanner <url>"))
        import aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r: img = await r.read()
        await ctx.guild.edit(banner=img)
        await ctx.message.edit(content=S.ui_ok("server banner updated"))

    @commands.command(name="deletechannel", brief="Delete a channel by ID")
    @commands.guild_only()
    async def deletechannel(self, ctx, channel: discord.TextChannel = None):
        if not channel: return await ctx.message.edit(content=S.ui_err("usage: deletechannel <#channel>"))
        await channel.delete()
        await ctx.channel.send(S.ui_ok(f"channel deleted"))

async def setup(bot): await bot.add_cog(ServerCog(bot))

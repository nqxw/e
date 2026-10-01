# cogs/voice.py
import asyncio, aiohttp, discord
from discord.ext import commands
from . import state as S
from .antid import jitter
import aiohttp

def _h(): return {"Authorization": S.TOKEN, "Content-Type": "application/json", "User-Agent": S.USER_AGENT}

async def _patch_member(guild_id, user_id, data):
    url = f"https://discord.com/api/v9/guilds/{guild_id}/members/{user_id}"
    async with aiohttp.ClientSession() as s:
        async with s.patch(url, headers=_h(), json=data) as r:
            return r.status

class VoiceCog(commands.Cog, name="voice"):
    """Voice channel controls."""
    def __init__(self, bot):
        self.bot = bot
        self._keep_tasks: dict = {}

    @commands.command(name="vcmute", brief="Server mute a user")
    @commands.guild_only()
    async def vcmute(self, ctx, member: discord.Member = None):
        if not member: return await ctx.message.edit(content=S.ui_err("usage: vcmute <@user>"))
        await member.edit(mute=True)
        await ctx.message.edit(content=S.ui_ok(f"muted {member}"))

    @commands.command(name="vcunmute", brief="Server unmute a user")
    @commands.guild_only()
    async def vcunmute(self, ctx, member: discord.Member = None):
        if not member: return await ctx.message.edit(content=S.ui_err("usage: vcunmute <@user>"))
        await member.edit(mute=False)
        await ctx.message.edit(content=S.ui_ok(f"unmuted {member}"))

    @commands.command(name="vcdeafen", brief="Server deafen a user")
    @commands.guild_only()
    async def vcdeafen(self, ctx, member: discord.Member = None):
        if not member: return await ctx.message.edit(content=S.ui_err("usage: vcdeafen <@user>"))
        await member.edit(deafen=True)
        await ctx.message.edit(content=S.ui_ok(f"deafened {member}"))

    @commands.command(name="vcundeafen", brief="Server undeafen a user")
    @commands.guild_only()
    async def vcundeafen(self, ctx, member: discord.Member = None):
        if not member: return await ctx.message.edit(content=S.ui_err("usage: vcundeafen <@user>"))
        await member.edit(deafen=False)
        await ctx.message.edit(content=S.ui_ok(f"undeafened {member}"))

    @commands.command(name="vckick", brief="Kick user from VC")
    @commands.guild_only()
    async def vckick(self, ctx, member: discord.Member = None):
        if not member: return await ctx.message.edit(content=S.ui_err("usage: vckick <@user>"))
        await member.move_to(None)
        await ctx.message.edit(content=S.ui_ok(f"kicked {member} from VC"))

    @commands.command(name="vcmove", brief="Move user to voice channel")
    @commands.guild_only()
    async def vcmove(self, ctx, member: discord.Member = None, ch: discord.VoiceChannel = None):
        if not member or not ch: return await ctx.message.edit(content=S.ui_err("usage: vcmove <@user> <#channel>"))
        await member.move_to(ch)
        await ctx.message.edit(content=S.ui_ok(f"moved {member} → #{ch.name}"))

    @commands.command(name="vckeep", brief="Keep VC connection alive")
    @commands.guild_only()
    async def vckeep(self, ctx, ch: discord.VoiceChannel = None, action: str = "on"):
        if action == "off" or not ch:
            t = self._keep_tasks.pop(ctx.channel.id, None)
            if t and not t.done(): t.cancel()
            return await ctx.message.edit(content=S.ui_ok("vckeep off"))
        async def _loop():
            while True:
                await asyncio.sleep(jitter(15.0))
        t = self._keep_tasks.get(ctx.channel.id)
        if t and not t.done(): t.cancel()
        self._keep_tasks[ctx.channel.id] = asyncio.create_task(_loop())
        await ctx.message.edit(content=S.ui_ok(f"vckeep → #{ch.name}"))

    @commands.command(name="selfmute", brief="Toggle self-mute")
    @commands.guild_only()
    async def selfmute(self, ctx):
        if ctx.guild.me.voice:
            muted = not ctx.guild.me.voice.self_mute
            await ctx.guild.change_voice_state(channel=ctx.guild.me.voice.channel, self_mute=muted)
            await ctx.message.edit(content=S.ui_ok(f"self-mute → {'on' if muted else 'off'}"))
        else:
            await ctx.message.edit(content=S.ui_err("not in a voice channel"))

    @commands.command(name="selfdeaf", brief="Toggle self-deaf")
    @commands.guild_only()
    async def selfdeaf(self, ctx):
        if ctx.guild.me.voice:
            deafened = not ctx.guild.me.voice.self_deaf
            await ctx.guild.change_voice_state(channel=ctx.guild.me.voice.channel, self_deaf=deafened)
            await ctx.message.edit(content=S.ui_ok(f"self-deaf → {'on' if deafened else 'off'}"))
        else:
            await ctx.message.edit(content=S.ui_err("not in a voice channel"))


    @commands.command(name="vcjoin", brief="Join a voice channel")
    @commands.guild_only()
    async def vcjoin(self, ctx, channel: discord.VoiceChannel = None):
        if not channel:
            if ctx.author.voice: channel = ctx.author.voice.channel
            else: return await ctx.message.edit(content=S.ui_err("usage: vcjoin <#channel>"))
        await channel.connect()
        await ctx.message.edit(content=S.ui_ok(f"joined #{channel.name}"))

    @commands.command(name="vcleave", brief="Leave voice channel")
    @commands.guild_only()
    async def vcleave(self, ctx):
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect()
            await ctx.message.edit(content=S.ui_ok("left VC"))
        else:
            await ctx.message.edit(content=S.ui_err("not in a VC"))

    @commands.command(name="vcmoveall", brief="Move all members to a channel")
    @commands.guild_only()
    async def vcmoveall(self, ctx, dest: discord.VoiceChannel = None):
        if not dest: return await ctx.message.edit(content=S.ui_err("usage: vcmoveall <#dest>"))
        moved = 0
        for ch in ctx.guild.voice_channels:
            for member in list(ch.members):
                if member.id != self.bot.user.id:
                    try: await member.move_to(dest); moved += 1
                    except Exception: pass
        await ctx.message.edit(content=S.ui_ok(f"moved {moved} members → #{dest.name}"))

    @commands.command(name="vcdiag", brief="Voice channel diagnostics")
    @commands.guild_only()
    async def vcdiag(self, ctx):
        vc = ctx.guild.voice_client
        rows = [
            f"  {S.DIM}connected{S.RESET}  {vc is not None}",
            f"  {S.DIM}channel{S.RESET}    {vc.channel.name if vc else '—'}",
            f"  {S.DIM}latency{S.RESET}    {round(vc.latency*1000)}ms" if vc else f"  {S.DIM}latency{S.RESET}    —",
        ]
        await ctx.message.edit(content=S.ui_box("vc diag", rows))


    @commands.command(name="selfcamera", brief="Toggle self camera in VC")
    @commands.guild_only()
    async def selfcamera(self, ctx, toggle: str = ""):
        if not ctx.guild.me.voice: return await ctx.message.edit(content=S.ui_err("not in VC"))
        on = toggle.lower() not in ("off","disable") if toggle else not ctx.guild.me.voice.self_video
        await ctx.guild.change_voice_state(channel=ctx.guild.me.voice.channel, self_video=on)
        await ctx.message.edit(content=S.ui_ok(f"camera → {'on' if on else 'off'}"))

    @commands.command(name="selfstream", brief="Toggle self stream in VC")
    @commands.guild_only()
    async def selfstream(self, ctx, toggle: str = ""):
        if not ctx.guild.me.voice: return await ctx.message.edit(content=S.ui_err("not in VC"))
        on = toggle.lower() not in ("off","disable") if toggle else not ctx.guild.me.voice.self_stream
        await ctx.guild.change_voice_state(channel=ctx.guild.me.voice.channel, self_stream=on)
        await ctx.message.edit(content=S.ui_ok(f"stream → {'on' if on else 'off'}"))

    @commands.command(name="vcreconnect", brief="Reconnect to voice channel")
    @commands.guild_only()
    async def vcreconnect(self, ctx):
        if not ctx.guild.me.voice: return await ctx.message.edit(content=S.ui_err("not in VC"))
        ch = ctx.guild.me.voice.channel
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect()
        await ch.connect()
        await ctx.message.edit(content=S.ui_ok(f"reconnected to #{ch.name}"))

async def setup(bot):
    await bot.add_cog(VoiceCog(bot))

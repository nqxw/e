# cogs/bumper.py | Auto-bumper for Disboard, MEE6, Bump.gg
import time
import asyncio, time, re, aiohttp, discord
from discord.ext import commands
from . import state as S
from .antid import jitter
import aiohttp
import re

BUMP_BOTS = {
    "302050872383242240": {"name":"Disboard","cmd":"!d bump","cooldown":7200,
        "success":re.compile(r"bump done|bumped|your server has been bumped",re.I),
        "wait_re":re.compile(r"(\d+)\s*(minute|hour|min|hr)",re.I)},
    "159985870458322944": {"name":"MEE6","cmd":"!bump","cooldown":3600,
        "success":re.compile(r"bumped|your server has been bumped|come back",re.I),
        "wait_re":re.compile(r"(\d+)\s*(minute|hour|min|hr)",re.I)},
    "510016054391734273": {"name":"Bump.gg","cmd":"!bump","cooldown":3600,
        "success":re.compile(r"bumped|bump complete",re.I),
        "wait_re":re.compile(r"(\d+)\s*(minute|hour|min|hr)",re.I)},
}

_bump_channels: dict = {}
_enabled: bool = False

def _parse_wait(text, bot_info):
    m = bot_info["wait_re"].search(text)
    if m:
        n = int(m.group(1)); unit = m.group(2).lower()
        return n*3600 if "hour" in unit or unit=="hr" else n*60
    return bot_info["cooldown"]

class BumperCog(commands.Cog, name="bumper"):
    """Auto-bumper for Disboard, MEE6, Bump.gg."""
    def __init__(self, bot): self.bot = bot

    async def _send(self, channel_id, content):
        h = {"Authorization": S.TOKEN, "Content-Type": "application/json", "User-Agent": S.USER_AGENT}
        async with aiohttp.ClientSession() as s:
            async with s.post(f"https://discord.com/api/v9/channels/{channel_id}/messages",
                              headers=h, json={"content": content}) as r:
                return r.status in (200,201)

    async def _bump_loop(self, channel_id):
        info = _bump_channels.get(channel_id)
        if not info: return
        while True:
            try:
                wait = info.get("next_bump", 0) - time.time()
                if wait > 0: await asyncio.sleep(jitter(wait, pct=0.05))
                if not _enabled: await asyncio.sleep(30); continue
                for cmd in info.get("cmds", ["!d bump"]):
                    ok = await self._send(channel_id, cmd)
                    if ok: info["count"] = info.get("count",0) + 1
                    await asyncio.sleep(jitter(4.0))
                    ch = self.bot.get_channel(channel_id)
                    if ch:
                        async for msg in ch.history(limit=8):
                            bid = str(msg.author.id)
                            if bid in BUMP_BOTS:
                                bot_info = BUMP_BOTS[bid]
                                content = msg.content or ""
                                for emb in msg.embeds:
                                    content += " " + (emb.description or "") + " " + (emb.title or "")
                                if bot_info["success"].search(content):
                                    info["next_bump"] = time.time() + _parse_wait(content, bot_info)
                                    break
                    await asyncio.sleep(jitter(3.0))
                info.setdefault("next_bump", time.time() + 7200)
            except asyncio.CancelledError: raise
            except Exception as e:
                info["last_error"] = str(e)
                await asyncio.sleep(jitter(60.0))

    @commands.group(name="autobump", aliases=["bumper"], invoke_without_command=True, brief="Auto-bumper")
    async def autobump(self, ctx):
        running = sum(1 for i in _bump_channels.values() if i.get("task") and not i["task"].done())
        await ctx.message.edit(content=S.ui_box("auto-bumper", [
            f"  {S.DIM}enabled{S.RESET}   {_enabled}",
            f"  {S.DIM}channels{S.RESET}  {len(_bump_channels)}",
            f"  {S.DIM}running{S.RESET}   {running}",
        ]))

    @autobump.command(name="add")
    async def ab_add(self, ctx, channel: discord.TextChannel = None, mode: str = "all"):
        if not channel: return await ctx.message.edit(content=S.ui_err("usage: autobump add <#channel> [disboard|mee6|all]"))
        cid = channel.id
        cmds = []
        if mode in ("disboard","all"): cmds.append("!d bump")
        if mode in ("mee6","all"): cmds.append("!bump")
        if not cmds: cmds = ["!d bump"]
        if cid in _bump_channels:
            t = _bump_channels[cid].get("task")
            if t and not t.done(): t.cancel()
        _bump_channels[cid] = {"cmds": cmds, "next_bump": 0, "count": 0, "last_error": ""}
        _bump_channels[cid]["task"] = asyncio.create_task(self._bump_loop(cid))
        await ctx.message.edit(content=S.ui_ok(f"auto-bump → {channel.mention} ({' | '.join(cmds)})"))

    @autobump.command(name="remove")
    async def ab_remove(self, ctx, channel: discord.TextChannel = None):
        if not channel: return await ctx.message.edit(content=S.ui_err("usage: autobump remove <#channel>"))
        info = _bump_channels.pop(channel.id, None)
        if info:
            t = info.get("task")
            if t and not t.done(): t.cancel()
        await ctx.message.edit(content=S.ui_ok(f"removed {channel.mention}"))

    @autobump.command(name="on")
    async def ab_on(self, ctx):
        global _enabled; _enabled = True
        await ctx.message.edit(content=S.ui_ok(f"auto-bumper → on ({len(_bump_channels)} channels)"))

    @autobump.command(name="off")
    async def ab_off(self, ctx):
        global _enabled; _enabled = False
        await ctx.message.edit(content=S.ui_ok("auto-bumper → off (tasks paused)"))

    @autobump.command(name="now")
    async def ab_now(self, ctx, channel: discord.TextChannel = None):
        if not channel: return await ctx.message.edit(content=S.ui_err("usage: autobump now <#channel>"))
        if channel.id in _bump_channels:
            _bump_channels[channel.id]["next_bump"] = 0
        await ctx.message.edit(content=S.ui_ok(f"bump queued for {channel.mention}"))

    @autobump.command(name="list")
    async def ab_list(self, ctx):
        if not _bump_channels: return await ctx.message.edit(content=S.ui_info("no channels registered"))
        rows = []
        for cid, info in _bump_channels.items():
            alive = info.get("task") and not info["task"].done()
            due_in = max(0, info.get("next_bump",0) - time.time())
            rows.append(f"  {S.GREY}•{S.RESET} <#{cid}>  {S.DIM}next: {due_in/60:.0f}m  count: {info.get('count',0)}  {'running' if alive else 'stopped'}{S.RESET}")
        await ctx.message.edit(content=S.ui_box("auto-bumper", rows))

    @autobump.command(name="clearall")
    async def ab_clearall(self, ctx):
        for info in _bump_channels.values():
            t = info.get("task")
            if t and not t.done(): t.cancel()
        _bump_channels.clear()
        await ctx.message.edit(content=S.ui_ok("all bump channels cleared"))

async def setup(bot): await bot.add_cog(BumperCog(bot))
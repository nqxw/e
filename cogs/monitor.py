# cogs/monitor.py
import asyncio, discord
from discord.ext import commands
from . import state as S
from .antid import jitter

_monitors: dict = {}  # name -> {task, config}

class MonitorCog(commands.Cog, name="monitor"):
    def __init__(self, bot): self.bot = bot

    @commands.group(name="monitor", invoke_without_command=True, brief="Event monitoring")
    async def monitor(self, ctx):
        rows = [f"  {S.GREY}•{S.RESET} {k}" for k in _monitors]
        await ctx.message.edit(content=S._paginate("monitors","",rows) if rows else S.ui_info("no monitors"))

    @monitor.command(name="status")
    async def mon_status(self, ctx, channel: discord.TextChannel = None):
        if not channel: return await ctx.message.edit(content=S.ui_err("usage: monitor status <#channel>"))
        ch_id = channel.id
        async def _loop():
            last = None
            while True:
                ch = self.bot.get_channel(ch_id)
                if ch and hasattr(ch, "guild"):
                    current = ch.guild.member_count
                    if last is not None and current != last:
                        log_ch = self.bot.get_channel(ch_id)
                        if log_ch:
                            try: await log_ch.send(S.ui_info(f"member count: {last} → {current}"))
                            except Exception: pass
                    last = current
                await asyncio.sleep(jitter(60.0))
        t = asyncio.create_task(_loop())
        _monitors[f"status_{ch_id}"] = {"task": t}
        await ctx.message.edit(content=S.ui_ok(f"monitoring {channel.mention}"))

    @monitor.command(name="stop")
    async def mon_stop(self, ctx, name: str = ""):
        m = _monitors.pop(name, None)
        if m:
            t = m.get("task")
            if t and not t.done(): t.cancel()
            await ctx.message.edit(content=S.ui_ok(f"monitor {name} stopped"))
        else:
            await ctx.message.edit(content=S.ui_err(f"monitor {name} not found"))

async def setup(bot): await bot.add_cog(MonitorCog(bot))

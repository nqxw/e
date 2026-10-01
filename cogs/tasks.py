# cogs/tasks.py
import asyncio, time, discord
from discord.ext import commands
from . import state as S
from .antid import jitter

class TasksCog(commands.Cog, name="tasks"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="task", brief="Task manager")
    async def task(self, ctx, sub: str = "list", name: str = ""):
        if sub == "list":
            rows = [f"  {S.GREY}•{S.RESET} {k}  {'running' if not v.done() else 'done'}"
                    for k, v in S._managed_tasks.items()]
            await ctx.message.edit(content=S._paginate("tasks","",rows) if rows else S.ui_info("no tasks"))
        elif sub == "stop" and name:
            t = S._managed_tasks.get(name)
            if t and not t.done(): t.cancel()
            await ctx.message.edit(content=S.ui_ok(f"task {name} stopped"))
        elif sub == "clear":
            for t in S._managed_tasks.values():
                if not t.done(): t.cancel()
            S._managed_tasks.clear()
            await ctx.message.edit(content=S.ui_ok("all tasks cleared"))
        else:
            await ctx.message.edit(content=S.ui_info("task list|stop <name>|clear"))

async def setup(bot): await bot.add_cog(TasksCog(bot))

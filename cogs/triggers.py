# cogs/triggers.py
import re, discord
from discord.ext import commands
from . import state as S

class TriggersCog(commands.Cog, name="triggers"):
    def __init__(self, bot): self.bot = bot

    @commands.group(name="trigger", invoke_without_command=True, brief="Message triggers")
    async def trigger(self, ctx):
        rows = [f"  {S.GREY}{i}{S.RESET} [{t['type']}] {t['pattern'][:30]} → {t['action'][:30]}"
                for i, t in enumerate(S._triggers.get("message", []))]
        await ctx.message.edit(content=S._paginate("triggers","",rows) if rows else S.ui_info("no triggers"))

    @trigger.command(name="add")
    async def trig_add(self, ctx, pattern: str = "", *, action: str = ""):
        if not pattern or not action: return await ctx.message.edit(content=S.ui_err("trigger add <pattern> <action>"))
        S._triggers.setdefault("message", []).append({
            "type": "contains", "pattern": pattern.lower(), "action": action, "count": 0
        })
        await ctx.message.edit(content=S.ui_ok(f"trigger added: {pattern} → {action[:40]}"))

    @trigger.command(name="remove")
    async def trig_remove(self, ctx, index: int = -1):
        msgs = S._triggers.get("message", [])
        if 0 <= index < len(msgs):
            removed = msgs.pop(index)
            await ctx.message.edit(content=S.ui_ok(f"removed trigger {index}"))
        else:
            await ctx.message.edit(content=S.ui_err("invalid index"))

    @trigger.command(name="clear")
    async def trig_clear(self, ctx):
        S._triggers["message"] = []
        await ctx.message.edit(content=S.ui_ok("triggers cleared"))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.user.id: return
        content = (message.content or "").lower()
        for t in S._triggers.get("message", []):
            if t["pattern"] in content:
                action = t["action"]
                t["count"] = t.get("count", 0) + 1
                try:
                    if action.startswith("say:"):
                        await message.channel.send(action[4:].strip())
                    elif action.startswith("react:"):
                        await message.add_reaction(action[6:].strip())
                    elif action.startswith("reply:"):
                        await message.reply(action[6:].strip())
                except Exception: pass


    @commands.command(name="triggers", brief="List all registered triggers")
    async def triggers_list(self, ctx):
        triggers = getattr(S,"_triggers",{})
        if not triggers: return await ctx.message.edit(content=S.ui_info("no triggers"))
        rows = [f"  {S.GREY}•{S.RESET} {k} → {v[:50]}" for k,v in triggers.items()]
        await ctx.message.edit(content=S._paginate("triggers","",rows))

async def setup(bot): await bot.add_cog(TriggersCog(bot))

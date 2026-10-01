# cogs/agc.py
import discord
from discord.ext import commands
from . import state as S

class AgcCog(commands.Cog, name="agc"):
    def __init__(self, bot): self.bot = bot

    @commands.group(name="agc", invoke_without_command=True, brief="Anti-group-chat")
    async def agc(self, ctx):
        await ctx.message.edit(content=S.ui_box("anti-gc", [
            f"  {S.DIM}enabled{S.RESET}   {S._agc_state['enabled']}",
            f"  {S.DIM}whitelist{S.RESET} {len(S._agc_whitelist)}",
            f"  {S.DIM}leave_msg{S.RESET} {S._agc_state['leave_msg'] or '—'}",
        ]))

    @agc.command(name="on")
    async def agc_on(self, ctx):
        S._agc_state["enabled"] = True
        await ctx.message.edit(content=S.ui_ok("anti-gc → on"))

    @agc.command(name="off")
    async def agc_off(self, ctx):
        S._agc_state["enabled"] = False
        await ctx.message.edit(content=S.ui_ok("anti-gc → off"))

    @agc.command(name="whitelist")
    async def agc_whitelist(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: agc whitelist <@user>"))
        S._agc_whitelist.add(user.id)
        await ctx.message.edit(content=S.ui_ok(f"whitelisted {user}"))

    @agc.command(name="msg")
    async def agc_msg(self, ctx, *, msg: str = ""):
        S._agc_state["leave_msg"] = msg
        await ctx.message.edit(content=S.ui_ok(f"leave message → {msg or 'cleared'}"))

    @commands.Cog.listener()
    async def on_group_join(self, channel, user):
        if not S._agc_state["enabled"]: return
        if user.id != self.bot.user.id: return
        # Check whitelist
        members = [m.id for m in channel.recipients]
        if any(uid in S._agc_whitelist for uid in members): return
        if S._agc_state["leave_msg"]:
            try: await channel.send(S._agc_state["leave_msg"])
            except Exception: pass
        try: await channel.leave()
        except Exception: pass

async def setup(bot): await bot.add_cog(AgcCog(bot))

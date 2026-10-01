# cogs/interactions.py
import discord
from discord.ext import commands
from . import state as S

class InteractionsCog(commands.Cog, name="interactions"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="buttons", brief="Toggle button handler")
    async def buttons(self, ctx, toggle: str = ""):
        S._buttons_enabled = (toggle.lower() in ("on","enable")) if toggle else not S._buttons_enabled
        await ctx.message.edit(content=S.ui_ok(f"buttons → {'on' if S._buttons_enabled else 'off'}"))

    @commands.command(name="modals", brief="Toggle modal handler")
    async def modals(self, ctx, toggle: str = ""):
        S._modals_enabled = (toggle.lower() in ("on","enable")) if toggle else not S._modals_enabled
        await ctx.message.edit(content=S.ui_ok(f"modals → {'on' if S._modals_enabled else 'off'}"))

    @commands.command(name="interactstatus", brief="Interaction status")
    async def interactstatus(self, ctx):
        await ctx.message.edit(content=S.ui_box("interactions", [
            f"  {S.DIM}buttons{S.RESET}  {S._buttons_enabled}",
            f"  {S.DIM}modals{S.RESET}   {S._modals_enabled}",
            f"  {S.DIM}pending{S.RESET}  {len(S._pending_interactions)}",
        ]))


    @commands.command(name="interact", brief="Send an interaction (button/select)")
    async def interact(self, ctx, message_id: int = 0):
        if not message_id: return await ctx.message.edit(content=S.ui_err("usage: interact <message_id>"))
        try:
            msg = await ctx.channel.fetch_message(message_id)
            if msg.components:
                await ctx.message.edit(content=S.ui_info(f"message has {len(msg.components)} component row(s)"))
            else:
                await ctx.message.edit(content=S.ui_warn("no interactive components on that message"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

async def setup(bot): await bot.add_cog(InteractionsCog(bot))

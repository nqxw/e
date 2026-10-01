# cogs/automod.py
import discord
from discord.ext import commands
from . import state as S

class AutomodCog(commands.Cog, name="automod"):
    def __init__(self, bot): self.bot = bot

    @commands.group(name="automod", invoke_without_command=True, brief="Automod config")
    async def automod(self, ctx):
        await ctx.message.edit(content=S.ui_box("automod", [
            f"  {S.DIM}enabled{S.RESET}  {S._automod['enabled']}",
            f"  {S.DIM}action{S.RESET}   {S._automod['action']}",
            f"  {S.DIM}words{S.RESET}    {len(S._automod['words'])}",
        ]))

    @automod.command(name="on")
    async def am_on(self, ctx): S._automod["enabled"] = True; await ctx.message.edit(content=S.ui_ok("automod on"))
    @automod.command(name="off")
    async def am_off(self, ctx): S._automod["enabled"] = False; await ctx.message.edit(content=S.ui_ok("automod off"))

    @automod.command(name="add")
    async def am_add(self, ctx, *, word: str = ""):
        if word: S._automod["words"].append(word.lower())
        await ctx.message.edit(content=S.ui_ok(f"word added: {word}"))

    @automod.command(name="remove")
    async def am_remove(self, ctx, *, word: str = ""):
        if word in S._automod["words"]: S._automod["words"].remove(word.lower())
        await ctx.message.edit(content=S.ui_ok(f"word removed: {word}"))

    @automod.command(name="list")
    async def am_list(self, ctx):
        rows = [f"  {S.GREY}•{S.RESET} {w}" for w in S._automod["words"]]
        await ctx.message.edit(content=S._paginate("automod words","",rows) if rows else S.ui_info("no words"))

    @commands.Cog.listener()
    async def on_message(self, message):
        if not S._automod["enabled"]: return
        if message.author.id == self.bot.user.id: return
        content = (message.content or "").lower()
        if any(w in content for w in S._automod["words"]):
            try: await message.delete()
            except Exception: pass


    @commands.command(name="raidmode", brief="Toggle raid mode (lock all channels)")
    @commands.guild_only()
    async def raidmode(self, ctx, toggle: str = "on"):
        on = toggle.lower() not in ("off","disable")
        S._automod["raid_mode"] = on
        await ctx.message.edit(content=S.ui_ok(f"raid mode → {'ON — channels locked' if on else 'OFF'}"))

    @commands.command(name="quarantine", brief="Quarantine a member")
    @commands.guild_only()
    async def quarantine(self, ctx, member: discord.Member = None):
        if not member: return await ctx.message.edit(content=S.ui_err("usage: quarantine <@member>"))
        try:
            from datetime import timedelta
            await member.timeout(discord.utils.utcnow() + timedelta(hours=24))
            await ctx.message.edit(content=S.ui_ok(f"quarantined {member} for 24h"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="ticket", brief="Create a support ticket channel")
    @commands.guild_only()
    async def ticket(self, ctx, *, reason: str = "support"):
        try:
            ch = await ctx.guild.create_text_channel(
                f"ticket-{ctx.author.name}",
                reason=f"Ticket: {reason}")
            await ctx.message.edit(content=S.ui_ok(f"ticket created: {ch.mention}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="verify", brief="Toggle verification mode")
    @commands.guild_only()
    async def verify(self, ctx, toggle: str = "on"):
        on = toggle.lower() not in ("off","disable")
        S._automod["verify_mode"] = on
        await ctx.message.edit(content=S.ui_ok(f"verify mode → {'on' if on else 'off'}"))

async def setup(bot): await bot.add_cog(AutomodCog(bot))

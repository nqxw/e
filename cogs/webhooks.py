# cogs/webhooks.py
import aiohttp, discord
from discord.ext import commands
from . import state as S
from .antid import delay, shuffled

def _h(): return {"Authorization": S.TOKEN, "User-Agent": S.USER_AGENT}

class WebhooksCog(commands.Cog, name="webhooks"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="webhook", brief="Webhook manager")
    async def webhook(self, ctx, sub: str = "list", *, args: str = ""):
        if sub == "list":
            if not ctx.guild: return await ctx.message.edit(content=S.ui_err("server only"))
            whs = await ctx.channel.webhooks()
            rows = [f"  {S.GREY}•{S.RESET} {w.name} ({w.url[:40]}...)" for w in whs]
            await ctx.message.edit(content=S._paginate("webhooks","",rows) if rows else S.ui_info("no webhooks"))
        elif sub == "create":
            w = await ctx.channel.create_webhook(name=args or "wilt")
            await ctx.message.edit(content=S.ui_ok(f"created: {w.url}"))
        elif sub == "delete":
            whs = await ctx.channel.webhooks()
            for w in whs:
                try: await w.delete(); await delay(0.5, 1.5)
                except Exception: pass
            await ctx.message.edit(content=S.ui_ok(f"deleted {len(whs)} webhooks in #{ctx.channel.name}"))
        elif sub == "send" and args:
            whs = await ctx.channel.webhooks()
            if not whs: return await ctx.message.edit(content=S.ui_err("no webhooks in this channel"))
            async with aiohttp.ClientSession() as s:
                await s.post(whs[0].url, json={"content": args})
            await ctx.message.edit(content=S.ui_ok("sent via webhook"))

    @commands.command(name="emojis", brief="List server emojis")
    @commands.guild_only()
    async def emojis(self, ctx):
        rows = [f"  {S.GREY}•{S.RESET} {e} `{e.name}` ({e.id})" for e in ctx.guild.emojis[:80]]
        await ctx.message.edit(content=S._paginate("emojis", ctx.guild.name, rows) if rows else S.ui_info("no emojis"))

    @commands.command(name="stealemoji", brief="Steal emoji from message")
    @commands.guild_only()
    async def stealemoji(self, ctx, emoji: discord.PartialEmoji = None):
        if not emoji or not ctx.guild: return await ctx.message.edit(content=S.ui_err("usage: stealemoji <emoji>"))
        import io, aiohttp as _ah
        async with _ah.ClientSession() as s:
            async with s.get(str(emoji.url)) as r:
                img = await r.read()
        new = await ctx.guild.create_custom_emoji(name=emoji.name, image=img)
        await ctx.message.edit(content=S.ui_ok(f"stolen: {new}"))

async def setup(bot): await bot.add_cog(WebhooksCog(bot))

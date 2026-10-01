# cogs/auto.py
import asyncio, discord
from discord.ext import commands
from . import state as S
from .antid import jitter

class AutoCog(commands.Cog, name="auto"):
    """Auto-react, super-react, mimic, auto-respond."""
    def __init__(self, bot): self.bot = bot

    # ── autoreact ──────────────────────────────────────────────────────────────
    @commands.group(name="autoreact", invoke_without_command=True)
    async def autoreact(self, ctx):
        rows = [f"  {S.GREY}•{S.RESET} {e}" for e in S.AUTO_RESPONSES.get("react", {}).values()]
        await ctx.message.edit(content=S._paginate("autoreact","",rows) if rows else S.ui_info("no autoreacts set"))

    @autoreact.command(name="set")
    async def ar_set(self, ctx, emoji: str = "", user: discord.User = None):
        if not emoji: return await ctx.message.edit(content=S.ui_err("usage: autoreact set <emoji> [@user]"))
        if user:
            S._autoreact_users[user.id] = emoji
        else:
            S.AUTO_RESPONSES.setdefault("react", {})["global"] = emoji
        await ctx.message.edit(content=S.ui_ok(f"autoreact set: {emoji}"))

    @autoreact.command(name="clear")
    async def ar_clear(self, ctx):
        S.AUTO_RESPONSES.pop("react", None)
        S._autoreact_users.clear()
        await ctx.message.edit(content=S.ui_ok("autoreact cleared"))

    # ── superreact ─────────────────────────────────────────────────────────────
    @commands.group(name="superreact", aliases=["sr"], invoke_without_command=True)
    async def superreact(self, ctx):
        await ctx.message.edit(content=S.ui_info("superreact set <emojis> [@user] | clear"))

    @superreact.command(name="set")
    async def sr_set(self, ctx, *, args: str = ""):
        parts = args.split()
        emojis = [p for p in parts if not p.startswith("<@")]
        S.AUTO_RESPONSES.setdefault("superreact", {})["emojis"] = emojis
        await ctx.message.edit(content=S.ui_ok(f"superreact: {' '.join(emojis)}"))

    @superreact.command(name="clear")
    async def sr_clear(self, ctx):
        S.AUTO_RESPONSES.pop("superreact", None)
        await ctx.message.edit(content=S.ui_ok("superreact cleared"))

    # ── mimic ──────────────────────────────────────────────────────────────────
    @commands.command(name="mimic", brief="Mimic a user")
    async def mimic(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: mimic <@user>"))
        S._mimic_dict[ctx.channel.id] = user.id
        await ctx.message.edit(content=S.ui_ok(f"mimicking {user}"))

    @commands.command(name="unmimic", brief="Stop mimicking")
    async def unmimic(self, ctx):
        S._mimic_dict.pop(ctx.channel.id, None)
        await ctx.message.edit(content=S.ui_ok("mimic stopped"))

    @commands.command(name="stopmimic", brief="Stop all mimics")
    async def stopmimic(self, ctx):
        S._mimic_dict.clear()
        await ctx.message.edit(content=S.ui_ok("all mimics stopped"))

    # ── autoaddback ────────────────────────────────────────────────────────────
    @commands.command(name="autoaddback", brief="Toggle auto add back friends")
    async def autoaddback(self, ctx, toggle: str = ""):
        S._autoaddback = toggle.lower() not in ("off", "disable", "false")
        await ctx.message.edit(content=S.ui_ok(f"autoaddback → {'on' if S._autoaddback else 'off'}"))

    # ── listeners ──────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.user.id: return
        # Mimic
        uid = S._mimic_dict.get(message.channel.id)
        if uid and message.author.id == uid:
            try:
                await asyncio.sleep(jitter(1.5))
                await message.channel.send(message.content)
            except Exception: pass
        # Autoreact
        emoji = (S._autoreact_users.get(message.author.id) or
                 S.AUTO_RESPONSES.get("react", {}).get("global"))
        if emoji:
            try:
                await asyncio.sleep(jitter(0.8))
                await message.add_reaction(emoji)
            except Exception: pass
        # Superreact
        emojis = S.AUTO_RESPONSES.get("superreact", {}).get("emojis", [])
        for em in emojis:
            try:
                await asyncio.sleep(jitter(0.5))
                await message.add_reaction(em)
            except Exception: pass


    @commands.command(name="nitrosniper", brief="Toggle Nitro link sniper")
    async def nitrosniper(self, ctx, toggle: str = ""):
        S._nitrosniper_enabled = toggle.lower() not in ("off","disable") if toggle else not S._nitrosniper_enabled
        await ctx.message.edit(content=S.ui_ok(f"nitro sniper → {'on' if S._nitrosniper_enabled else 'off'}"))

    @commands.command(name="vsniper", brief="Toggle vanity URL sniper")
    async def vsniper(self, ctx, toggle: str = ""):
        if not hasattr(S,"_vsniper_enabled"): S._vsniper_enabled = False
        S._vsniper_enabled = toggle.lower() not in ("off","disable") if toggle else not S._vsniper_enabled
        await ctx.message.edit(content=S.ui_ok(f"vsniper → {'on' if S._vsniper_enabled else 'off'}"))

    @commands.command(name="multireact", brief="Multi-reaction pool  multireact add <emoji>")
    async def multireact(self, ctx, sub: str = "", *, rest: str = ""):
        pool = S.AUTO_RESPONSES.setdefault("multireact", {"emojis":[]})["emojis"] if hasattr(S,"AUTO_RESPONSES") else []
        if sub == "add" and rest:
            pool.append(rest)
            await ctx.message.edit(content=S.ui_ok(f"added {rest} — pool: {pool}"))
        elif sub == "remove" and rest:
            if rest in pool: pool.remove(rest)
            await ctx.message.edit(content=S.ui_ok(f"removed {rest}"))
        elif sub == "clear":
            pool.clear()
            await ctx.message.edit(content=S.ui_ok("pool cleared"))
        elif sub == "list":
            rows = [f"  {S.GREY}•{S.RESET} {e}" for e in pool]
            await ctx.message.edit(content=S._paginate("multireact pool","",rows) if rows else S.ui_info("empty"))
        else:
            await ctx.message.edit(content=S.ui_info("multireact add/remove/clear/list <emoji>"))

    @commands.command(name="multiautoreact", brief="Enable multi-reaction on all messages")
    async def multiautoreact(self, ctx, toggle: str = "on"):
        on = toggle.lower() not in ("off","disable")
        if hasattr(S,"AUTO_RESPONSES"):
            S.AUTO_RESPONSES.setdefault("multireact",{"emojis":[],"enabled":False})["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"multiautoreact → {'on' if on else 'off'}"))

    @commands.command(name="autoreactstop", brief="Stop autoreact globally")
    async def autoreactstop(self, ctx):
        if hasattr(S,"AUTO_RESPONSES"): S.AUTO_RESPONSES.pop("react",None)
        if hasattr(S,"_autoreact_users"): S._autoreact_users.clear()
        await ctx.message.edit(content=S.ui_ok("autoreact stopped"))

    @commands.command(name="superreactstop", brief="Stop superreact")
    async def superreactstop(self, ctx):
        if hasattr(S,"AUTO_RESPONSES"): S.AUTO_RESPONSES.pop("superreact",None)
        await ctx.message.edit(content=S.ui_ok("superreact stopped"))

    @commands.command(name="reactdiag", brief="Reaction diagnostics")
    async def reactdiag(self, ctx):
        ar = getattr(S,"AUTO_RESPONSES",{})
        rows = [
            f"  {S.DIM}autoreact{S.RESET}   {ar.get('react',{}).get('global','—')}",
            f"  {S.DIM}superreact{S.RESET}  {ar.get('superreact',{}).get('emojis','—')}",
            f"  {S.DIM}multireact{S.RESET}  {ar.get('multireact',{}).get('emojis','—')}",
            f"  {S.DIM}per-user{S.RESET}    {len(getattr(S,'_autoreact_users',{}))}",
        ]
        await ctx.message.edit(content=S.ui_box("react diag", rows))

async def setup(bot): await bot.add_cog(AutoCog(bot))

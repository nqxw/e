# cogs/settings.py
import discord
from discord.ext import commands
from . import state as S
from .antid import jitter, delay, batch_delay, on_rate_limit


class SettingsCog(commands.Cog, name="settings"):
    """Prefix, aliases, cooldowns, disabled commands."""
    def __init__(self, bot): self.bot = bot

    @commands.command(name="setprefix", brief="Change global prefix")
    async def setprefix(self, ctx, new: str = ""):
        if not new:
            return await ctx.message.edit(content=S.ui_err("usage: setprefix <prefix>"))
        S.PREFIX = new
        S._live_prefix[0] = new
        self.bot.command_prefix = lambda b, m: S._server_prefixes.get(
            str(m.guild.id) if m.guild else "", S.PREFIX)
        cfg = S.load_config(); cfg["prefix"] = new; S.save_config(cfg)
        await ctx.message.edit(content=S.ui_ok(f"prefix → `{new}`"))

    @commands.command(name="serverprefix", brief="Per-server prefix")
    @commands.guild_only()
    async def serverprefix(self, ctx, prefix: str = ""):
        if not prefix:
            return await ctx.message.edit(content=S.ui_err("usage: serverprefix <prefix>"))
        S._server_prefixes[str(ctx.guild.id)] = prefix
        await ctx.message.edit(content=S.ui_ok(f"server prefix → `{prefix}`"))

    @commands.command(name="clearprefix", brief="Clear per-server prefix")
    @commands.guild_only()
    async def clearprefix(self, ctx):
        S._server_prefixes.pop(str(ctx.guild.id), None)
        await ctx.message.edit(content=S.ui_ok("server prefix cleared"))

    @commands.command(name="setcooldown", brief="Set per-command cooldown")
    async def setcooldown(self, ctx, seconds: float = 0, cmd: str = ""):
        if not cmd:
            return await ctx.message.edit(content=S.ui_err("usage: setcooldown <seconds> <command>"))
        S._cooldowns[cmd.lower()] = seconds
        await ctx.message.edit(content=S.ui_ok(f"cooldown `{cmd}` → {seconds}s"))

    @commands.group(name="alias", invoke_without_command=True, brief="Manage aliases")
    async def alias(self, ctx):
        await ctx.message.edit(content=S.ui_info("alias add/remove/list/clear"))

    @alias.command(name="add")
    async def alias_add(self, ctx, alias: str = "", cmd: str = ""):
        if not alias or not cmd:
            return await ctx.message.edit(content=S.ui_err("usage: alias add <alias> <cmd>"))
        S._aliases[alias] = cmd
        await ctx.message.edit(content=S.ui_ok(f"alias `{alias}` → `{cmd}`"))

    @alias.command(name="remove")
    async def alias_remove(self, ctx, alias: str = ""):
        S._aliases.pop(alias, None)
        await ctx.message.edit(content=S.ui_ok(f"alias `{alias}` removed"))

    @alias.command(name="list")
    async def alias_list(self, ctx):
        rows = [f"  {S.GREY}•{S.RESET} `{k}` → `{v}`" for k, v in S._aliases.items()]
        await ctx.message.edit(content=S._paginate("aliases","",rows) if rows else S.ui_info("no aliases"))

    @alias.command(name="clear")
    async def alias_clear(self, ctx):
        S._aliases.clear()
        await ctx.message.edit(content=S.ui_ok("aliases cleared"))

    @commands.command(name="disable", brief="Disable a command")
    async def disable(self, ctx, cmd: str = ""):
        if not cmd:
            return await ctx.message.edit(content=S.ui_err("usage: disable <command>"))
        S._cmd_disabled.add(cmd.lower())
        c = self.bot.get_command(cmd)
        if c: c.enabled = False
        await ctx.message.edit(content=S.ui_ok(f"`{cmd}` disabled"))

    @commands.command(name="enable", brief="Enable a command")
    async def enable(self, ctx, cmd: str = ""):
        if not cmd:
            return await ctx.message.edit(content=S.ui_err("usage: enable <command>"))
        S._cmd_disabled.discard(cmd.lower())
        c = self.bot.get_command(cmd)
        if c: c.enabled = True
        await ctx.message.edit(content=S.ui_ok(f"`{cmd}` enabled"))

    @commands.command(name="antid", brief="Anti-detection tuning")
    async def antid(self, ctx, key: str = "", value: str = ""):
        from .antid import CFG
        if key == "set" and value:
            # antid set <key> <value>  (key passed as first word of remaining)
            parts = value.split()
            if len(parts) >= 2 and parts[0] in CFG:
                try: CFG[parts[0]] = float(parts[1])
                except ValueError: pass
        if key and key in CFG and value:
            try:
                CFG[key] = float(value)
                return await ctx.message.edit(content=S.ui_ok(f"antid.{key} → {CFG[key]}"))
            except ValueError:
                return await ctx.message.edit(content=S.ui_err("value must be a number"))
        rows = [f"  {S.DIM}{k}{S.RESET}  {v}" for k, v in CFG.items()]
        rows += ["", f"  {S.DIM}antid <key> <value>  to tune{S.RESET}"]
        await ctx.message.edit(content=S.ui_box("anti-detection", rows))

    @commands.command(name="settings", brief="Show settings status")
    async def settings_status(self, ctx):
        await ctx.message.edit(content=S.ui_box("settings", [
            f"  {S.DIM}prefix{S.RESET}           `{S.PREFIX}`",
            f"  {S.DIM}aliases{S.RESET}          {len(S._aliases)}",
            f"  {S.DIM}disabled cmds{S.RESET}    {len(S._cmd_disabled)}",
            f"  {S.DIM}per-cmd cooldowns{S.RESET} {len(S._cooldowns)}",
            f"  {S.DIM}server prefixes{S.RESET}  {len(S._server_prefixes)}",
        ]))


async def setup(bot):
    await bot.add_cog(SettingsCog(bot))

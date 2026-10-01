# cogs/loggers.py
import discord
from discord.ext import commands
from . import state as S

async def _log(ch_id, content):
    if not ch_id: return
    bot = S.BOT
    if not bot: return
    ch = bot.get_channel(int(ch_id))
    if ch:
        try: await ch.send(content)
        except Exception: pass

NL = chr(10)

class LoggersCog(commands.Cog, name="loggers"):
    def __init__(self, bot): self.bot = bot

    @commands.group(name="logger", invoke_without_command=True, brief="Logger config")
    async def logger(self, ctx):
        rows = [
            f"  {S.DIM}{k}{S.RESET}  enabled={v['enabled']}  ch={v['channel'] or '—'}"
            for k, v in S.loggers.items()
        ]
        await ctx.message.edit(content=S.ui_box("loggers", rows))

    @logger.command(name="set")
    async def logger_set(self, ctx, log_type: str = "", channel: discord.TextChannel = None):
        if log_type not in S.loggers:
            return await ctx.message.edit(content=S.ui_err(f"unknown type: {log_type}"))
        S.loggers[log_type]["enabled"] = True
        S.loggers[log_type]["channel"] = channel.id if channel else None
        await ctx.message.edit(content=S.ui_ok(f"logger {log_type} set"))

    @logger.command(name="off")
    async def logger_off(self, ctx, log_type: str = ""):
        if log_type in S.loggers:
            S.loggers[log_type]["enabled"] = False
        await ctx.message.edit(content=S.ui_ok(f"logger {log_type} off"))

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        cfg = S.loggers.get("deleted", {})
        if not cfg.get("enabled"): return
        if message.author.id == self.bot.user.id: return  # skip own messages
        txt = (
            "```" + NL +
            f"deleted in #{message.channel.name}" + NL +
            f"author: {message.author}" + NL +
            f"content: {(message.content or '[no text]')[:400]}" + NL +
            "```"
        )
        await _log(cfg["channel"], txt)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        cfg = S.loggers.get("edited", {})
        if not cfg.get("enabled"): return
        if before.author.id == self.bot.user.id: return  # skip own edits
        if before.content == after.content: return
        txt = (
            "```" + NL +
            f"edited in #{before.channel.name}" + NL +
            f"author: {before.author}" + NL +
            f"before: {before.content[:200]}" + NL +
            f"after:  {after.content[:200]}" + NL +
            "```"
        )
        await _log(cfg["channel"], txt)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        cfg = S.loggers.get("joins", {})
        if not cfg.get("enabled"): return
        await _log(cfg["channel"], "```" + NL + f"joined: {member} in {member.guild.name}" + NL + "```")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        cfg = S.loggers.get("leaves", {})
        if not cfg.get("enabled"): return
        await _log(cfg["channel"], "```" + NL + f"left: {member} from {member.guild.name}" + NL + "```")


    @logger.command(name="logchannel", aliases=["ch"])
    async def logger_ch(self, ctx, log_type: str = "", channel: discord.TextChannel = None):
        if log_type not in S.loggers:
            return await ctx.message.edit(content=S.ui_err(f"valid types: {', '.join(S.loggers)}"))
        S.loggers[log_type]["channel"] = channel.id if channel else None
        await ctx.message.edit(content=S.ui_ok(f"logger {log_type} channel → {channel or 'none'}"))

    @commands.command(name="logstatus", brief="Show all logger status")
    async def logstatus(self, ctx):
        rows = [f"  {S.DIM}{k}{S.RESET}  {'on' if v['enabled'] else 'off'}  ch={v['channel'] or '—'}"
                for k,v in S.loggers.items()]
        await ctx.message.edit(content=S.ui_box("loggers", rows))


    @commands.command(name="logchannel", brief="Set log channel  logchannel <type> <#ch>")
    async def logchannel(self, ctx, log_type: str = "", channel_id: str = ""):
        if not log_type or log_type not in S.loggers:
            return await ctx.message.edit(content=S.ui_err(f"types: {', '.join(S.loggers)}"))
        S.loggers[log_type]["channel"] = channel_id or None
        await ctx.message.edit(content=S.ui_ok(f"{log_type} channel → {channel_id or 'cleared'}"))

    @commands.command(name="logdeleted", brief="Toggle deleted message logger")
    async def logdeleted(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.loggers["deleted"]["enabled"]
        S.loggers["deleted"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"logdeleted → {'on' if on else 'off'}"))

    @commands.command(name="logedited", brief="Toggle edited message logger")
    async def logedited(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.loggers["edited"]["enabled"]
        S.loggers["edited"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"logedited → {'on' if on else 'off'}"))

    @commands.command(name="logdm", brief="Toggle DM logger")
    async def logdm(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.loggers.get("dm",{}).get("enabled",False)
        S.loggers.setdefault("dm",{"enabled":False,"channel":None})["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"logdm → {'on' if on else 'off'}"))

    @commands.command(name="logjoins", brief="Toggle member join logger")
    async def logjoins(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.loggers["joins"]["enabled"]
        S.loggers["joins"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"logjoins → {'on' if on else 'off'}"))

    @commands.command(name="logleaves", brief="Toggle member leave logger")
    async def logleaves(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.loggers["leaves"]["enabled"]
        S.loggers["leaves"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"logleaves → {'on' if on else 'off'}"))

    @commands.command(name="logmention", brief="Toggle mention logger")
    async def logmention(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.loggers.get("mention",{}).get("enabled",False)
        S.loggers.setdefault("mention",{"enabled":False,"channel":None})["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"logmention → {'on' if on else 'off'}"))

    @commands.command(name="logmessage", brief="Toggle all-messages logger")
    async def logmessage(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.loggers["message"]["enabled"]
        S.loggers["message"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"logmessage → {'on' if on else 'off'}"))

    @commands.command(name="logreaction", brief="Toggle reaction logger")
    async def logreaction(self, ctx, toggle: str = ""):
        on = toggle.lower() not in ("off","disable") if toggle else not S.loggers["reaction"]["enabled"]
        S.loggers["reaction"]["enabled"] = on
        await ctx.message.edit(content=S.ui_ok(f"logreaction → {'on' if on else 'off'}"))

async def setup(bot):
    await bot.add_cog(LoggersCog(bot))

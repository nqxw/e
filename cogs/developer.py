# cogs/developer.py
import discord
from discord.ext import commands
from . import state as S

class DeveloperCog(commands.Cog, name="developer"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="plugin", brief="Plugin manager")
    async def plugin(self, ctx, sub: str = "list", name: str = ""):
        if sub == "list":
            rows = [f"  {S.GREY}•{S.RESET} {k}" for k in S._plugins]
            await ctx.message.edit(content=S._paginate("plugins","",rows) if rows else S.ui_info("no plugins"))
        elif sub == "load" and name:
            try:
                import importlib
                mod = importlib.import_module(f"plugins.{name}")
                S._plugins[name] = mod
                await ctx.message.edit(content=S.ui_ok(f"plugin {name} loaded"))
            except Exception as e:
                await ctx.message.edit(content=S.ui_err(str(e)))
        elif sub == "unload" and name:
            S._plugins.pop(name, None)
            await ctx.message.edit(content=S.ui_ok(f"plugin {name} unloaded"))
        else:
            await ctx.message.edit(content=S.ui_info("plugin list|load <name>|unload <name>"))

    @commands.command(name="sessions", brief="Session information")
    async def sessions(self, ctx):
        await ctx.message.edit(content=S.ui_box("sessions", [
            f"  {S.DIM}sessions{S.RESET}  {len(S._sessions)}",
            f"  {S.DIM}latency{S.RESET}   {round(self.bot.latency*1000)}ms",
            f"  {S.DIM}guilds{S.RESET}    {len(self.bot.guilds)}",
        ]))

    @commands.command(name="setproxy", brief="Set proxy")
    async def setproxy(self, ctx, url: str = ""):
        S._proxy = url or None
        await ctx.message.edit(content=S.ui_ok(f"proxy → {url or 'cleared'}"))


    @commands.command(name="setowner", brief="Transfer owner role [owner only]")
    async def setowner(self, ctx, user_id: int = 0):
        if ctx.author.id != getattr(S,"OWNER_ID",0) and getattr(S,"OWNER_ID",0) != 0:
            return await ctx.message.edit(content=S.ui_err("owner only"))
        if not user_id: return await ctx.message.edit(content=S.ui_err("usage: setowner <user_id>"))
        old = getattr(S,"OWNER_ID",0); S.OWNER_ID = user_id
        if hasattr(S,"access_save"): S.access_save()
        await ctx.message.edit(content=S.ui_ok(f"owner {old} → {user_id}"))

    @commands.command(name="setadmin", brief="Add admin [owner only]")
    async def setadmin(self, ctx, user_id: int = 0):
        if not user_id: return await ctx.message.edit(content=S.ui_err("usage: setadmin <user_id>"))
        getattr(S,"_admins",set()).add(user_id)
        if hasattr(S,"access_save"): S.access_save()
        await ctx.message.edit(content=S.ui_ok(f"admin added: {user_id}"))

    @commands.command(name="adminremove", brief="Remove admin [owner only]")
    async def adminremove(self, ctx, user_id: int = 0):
        if not user_id: return await ctx.message.edit(content=S.ui_err("usage: adminremove <user_id>"))
        getattr(S,"_admins",set()).discard(user_id)
        if hasattr(S,"access_save"): S.access_save()
        await ctx.message.edit(content=S.ui_ok(f"admin removed: {user_id}"))

    @commands.command(name="adminlist", brief="List admins")
    async def adminlist(self, ctx):
        admins = sorted(getattr(S,"_admins",set()))
        rows = [f"  {S.GREY}•{S.RESET} {uid}" for uid in admins]
        await ctx.message.edit(content=S._paginate("admins","",rows) if rows else S.ui_info("none"))

    @commands.command(name="setdev", brief="Add dev [owner only]")
    async def setdev(self, ctx, user_id: int = 0):
        if not user_id: return await ctx.message.edit(content=S.ui_err("usage: setdev <user_id>"))
        getattr(S,"_devs",set()).add(user_id)
        if hasattr(S,"access_save"): S.access_save()
        await ctx.message.edit(content=S.ui_ok(f"dev added: {user_id}"))

    @commands.command(name="devremove", brief="Remove dev [owner only]")
    async def devremove(self, ctx, user_id: int = 0):
        if not user_id: return await ctx.message.edit(content=S.ui_err("usage: devremove <user_id>"))
        getattr(S,"_devs",set()).discard(user_id)
        if hasattr(S,"access_save"): S.access_save()
        await ctx.message.edit(content=S.ui_ok(f"dev removed: {user_id}"))

    @commands.command(name="devlist", brief="List devs")
    async def devlist(self, ctx):
        devs = sorted(getattr(S,"_devs",set()))
        rows = [f"  {S.GREY}•{S.RESET} {uid}" for uid in devs]
        await ctx.message.edit(content=S._paginate("devs","",rows) if rows else S.ui_info("none"))

    @commands.command(name="accesslist", brief="List owner/admins/devs")
    async def accesslist(self, ctx):
        await ctx.message.edit(content=S._ansi_block([
            f"  owner:   {getattr(S,'OWNER_ID',0)}",
            f"  admins:  {sorted(getattr(S,'_admins',set())) or '—'}",
            f"  devs:    {sorted(getattr(S,'_devs',set())) or '—'}",
        ]))

    @commands.command(name="reconnect", brief="Close gateway to force reconnect")
    async def reconnect(self, ctx):
        import asyncio
        await ctx.message.edit(content=S.ui_warn("reconnecting..."))
        ws = getattr(self.bot, "ws", None)
        if ws and hasattr(ws,"close"):
            try: await ws.close(code=1000)
            except Exception: pass

    @commands.command(name="restart", brief="Restart the bot process")
    async def restart(self, ctx):
        import os, sys
        await ctx.message.edit(content=S.ui_warn("restarting..."))
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @commands.command(name="logs", brief="Show last N lines of log file")
    async def logs(self, ctx, n: int = 10):
        import os
        log_file = getattr(S,"LOG_FILE","wilt.log")
        if not os.path.exists(log_file):
            return await ctx.message.edit(content=S.ui_err("no log file"))
        with open(log_file,"r",encoding="utf-8",errors="replace") as f:
            lines = f.readlines()
        tail = "".join(lines[-n:])
        if len(tail) > 1900: tail = tail[-1900:]
        await ctx.message.edit(content=f"```\n{tail}\n```")

    @commands.command(name="session", brief="Session list/switch")
    async def session(self, ctx, sub: str = "list", idx: int = -1):
        sessions = getattr(S,"_sessions",[])
        if sub == "list":
            rows = [f"  {S.GREY}[{i}]{S.RESET} {s[:12]}..." for i,s in enumerate(sessions)]
            await ctx.message.edit(content=S._paginate("sessions","",rows) if rows else S.ui_info("none"))
        elif sub == "switch" and idx >= 0:
            if 0 <= idx < len(sessions):
                S._session_idx = idx
                await ctx.message.edit(content=S.ui_ok(f"active → {sessions[idx][:12]}..."))
            else:
                await ctx.message.edit(content=S.ui_err("bad index"))


    @commands.command(name="proxy", brief="Set/clear proxy  proxy set <url> | clear")
    async def proxy(self, ctx, sub: str = "", url: str = ""):
        if sub == "set" and url:
            S._proxy = url; await ctx.message.edit(content=S.ui_ok(f"proxy → {url}"))
        elif sub == "clear":
            S._proxy = None; await ctx.message.edit(content=S.ui_ok("proxy cleared"))
        else:
            await ctx.message.edit(content=S.ui_info(f"current: {getattr(S,'_proxy',None) or 'none'}"))

async def setup(bot): await bot.add_cog(DeveloperCog(bot))

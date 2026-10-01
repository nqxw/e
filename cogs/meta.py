# cogs/meta.py
import time
import asyncio, time, io, contextlib, discord
from discord.ext import commands
from . import state as S

class MetaCog(commands.Cog, name="meta"):
    def __init__(self, bot):
        self.bot = bot
        self.bot._start_time = time.time()

    @commands.command(name="uptime", brief="Show uptime")
    async def uptime(self, ctx):
        elapsed = time.time() - getattr(self.bot, "_start_time", time.time())
        h, r = divmod(int(elapsed), 3600)
        m, s = divmod(r, 60)
        await ctx.message.edit(content=S.ui_info(f"uptime: {h}h {m}m {s}s"))

    @commands.command(name="eval", aliases=["exec"], brief="Evaluate Python")
    async def eval_cmd(self, ctx, *, code: str = ""):
        if not code: return
        code = code.strip("`").strip()
        if code.startswith("python"): code = code[6:].strip()
        env = {"bot": self.bot, "ctx": ctx, "S": S, "discord": discord}
        try:
            result = eval(code, env)
            output = repr(result)
        except SyntaxError:
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out):
                    exec(code, env)
                output = out.getvalue() or "done"
            except Exception as e:
                output = f"Error: {e}"
        except Exception as e:
            output = f"Error: {e}"
        await ctx.message.edit(content="```py\n" + str(output)[:1800] + "\n```")

    @commands.command(name="debug", brief="Toggle debug mode")
    async def debug(self, ctx):
        S.meta["debug"] = not S.meta["debug"]
        await ctx.message.edit(content=S.ui_ok(f"debug → {S.meta['debug']}"))

    @commands.command(name="loadcog", brief="Load a cog")
    async def loadcog(self, ctx, cog: str = ""):
        if not cog: return await ctx.message.edit(content=S.ui_err("usage: loadcog <cog>"))
        try:
            await self.bot.load_extension(f"cogs.{cog}")
            await ctx.message.edit(content=S.ui_ok(f"loaded {cog}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="unloadcog", brief="Unload a cog")
    async def unloadcog(self, ctx, cog: str = ""):
        if not cog: return await ctx.message.edit(content=S.ui_err("usage: unloadcog <cog>"))
        try:
            await self.bot.unload_extension(f"cogs.{cog}")
            await ctx.message.edit(content=S.ui_ok(f"unloaded {cog}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="reloadcog", aliases=["reload"], brief="Reload a cog")
    async def reloadcog(self, ctx, cog: str = ""):
        if not cog: return await ctx.message.edit(content=S.ui_err("usage: reloadcog <cog>"))
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await ctx.message.edit(content=S.ui_ok(f"reloaded {cog}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="coglist", brief="List loaded cogs")
    async def coglist(self, ctx):
        rows = [f"  {S.GREY}•{S.RESET} {name}" for name in sorted(self.bot.cogs)]
        await ctx.message.edit(content=S._paginate(f"cogs ({len(rows)})", "", rows))


    @commands.command(name="uptime_mon", brief="Show uptime")
    async def uptime_mon(self, ctx):
        import time as _t
        up = int(_t.time() - getattr(S,"_start_time",_t.time()))
        h,m = divmod(up,3600); m //= 60
        await ctx.message.edit(content=S.ui_ok(f"uptime: {h}h {m}m"))

    @commands.command(name="statuswatch", brief="Watch bot connection status")
    async def statuswatch(self, ctx):
        ws = getattr(self.bot,"ws",None)
        await ctx.message.edit(content=S.ui_box("status", [
            f"  {S.DIM}latency{S.RESET}  {round(self.bot.latency*1000)}ms",
            f"  {S.DIM}closed{S.RESET}   {self.bot.is_closed()}",
            f"  {S.DIM}guilds{S.RESET}   {len(self.bot.guilds)}",
            f"  {S.DIM}ws type{S.RESET}  {type(ws).__name__ if ws else 'None'}",
        ]))

    @commands.command(name="config", brief="Show/dump current config")
    async def config(self, ctx):
        cfg = S.load_config() or {}
        rows = [f"  {S.GREY}•{S.RESET} {k}: {str(v)[:50]}" for k,v in cfg.items()]
        await ctx.message.edit(content=S._paginate("config","",rows) if rows else S.ui_info("empty config"))

    @commands.command(name="resetconfig", brief="Reset config to defaults")
    async def resetconfig(self, ctx):
        S.save_config({})
        await ctx.message.edit(content=S.ui_ok("config reset"))

    @commands.command(name="setwebhook", brief="Set webhook URL for logging")
    async def setwebhook(self, ctx, url: str = ""):
        cfg = S.load_config() or {}
        cfg["webhook_url"] = url or None
        S.save_config(cfg)
        await ctx.message.edit(content=S.ui_ok(f"webhook → {url or 'cleared'}"))

    @commands.command(name="githubwatch", brief="Toggle GitHub update watcher")
    async def githubwatch(self, ctx, toggle: str = ""):
        if not hasattr(S,"_github_watch"): S._github_watch = False
        S._github_watch = toggle.lower() not in ("off","disable") if toggle else not S._github_watch
        await ctx.message.edit(content=S.ui_ok(f"github watch → {'on' if S._github_watch else 'off'}"))

    @commands.command(name="apistatus", brief="Check Discord API status")
    async def apistatus(self, ctx):
        import aiohttp
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://discordstatus.com/api/v2/status.json") as r:
                    d = await r.json()
                    status = d.get("status",{}).get("description","?")
                    indicator = d.get("status",{}).get("indicator","?")
                    await ctx.message.edit(content=S.ui_ok(f"Discord API: {status} [{indicator}]"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))

    @commands.command(name="errorlog", brief="Show recent errors")
    async def errorlog(self, ctx):
        errors = getattr(S,"_error_log",[])
        rows = [f"  {S.GREY}•{S.RESET} {e}" for e in errors[-10:]]
        await ctx.message.edit(content=S._paginate("errors","",rows) if rows else S.ui_info("no errors"))

    @commands.command(name="errorclear", brief="Clear error log")
    async def errorclear(self, ctx):
        if hasattr(S,"_error_log"): S._error_log.clear()
        await ctx.message.edit(content=S.ui_ok("error log cleared"))

    @commands.command(name="devmode", brief="Toggle developer mode")
    async def devmode(self, ctx, toggle: str = ""):
        if not hasattr(S,"_dev_mode"): S._dev_mode = False
        S._dev_mode = toggle.lower() not in ("off","disable") if toggle else not S._dev_mode
        await ctx.message.edit(content=S.ui_ok(f"dev mode → {'on' if S._dev_mode else 'off'}"))

async def setup(bot):
    await bot.add_cog(MetaCog(bot))
# cogs/db.py
import aiosqlite, discord
from discord.ext import commands
from . import state as S

class DbCog(commands.Cog, name="db"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="dbstats", brief="Show database stats")
    async def dbstats(self, ctx):
        await ctx.message.edit(content=S.ui_info(f"db path: {S._db_path}"))

    @commands.command(name="note", brief="Add a note")
    async def note(self, ctx, *, text: str = ""):
        if not text: return await ctx.message.edit(content=S.ui_err("usage: note <text>"))
        cfg = S.load_config()
        notes = cfg.get("notes", [])
        notes.append({"text": text, "time": __import__("time").strftime("%Y-%m-%d %H:%M")})
        cfg["notes"] = notes; S.save_config(cfg)
        await ctx.message.edit(content=S.ui_ok(f"note saved ({len(notes)} total)"))

    @commands.command(name="notes", brief="List notes")
    async def notes(self, ctx):
        cfg = S.load_config()
        notes = cfg.get("notes", [])
        rows = [f"  {S.GREY}{i}{S.RESET} [{n['time']}] {n['text'][:60]}" for i, n in enumerate(notes)]
        await ctx.message.edit(content=S._paginate("notes","",rows) if rows else S.ui_info("no notes"))

    @commands.command(name="clearnotes", brief="Clear all notes")
    async def clearnotes(self, ctx):
        cfg = S.load_config(); cfg["notes"] = []; S.save_config(cfg)
        await ctx.message.edit(content=S.ui_ok("notes cleared"))


    @commands.command(name="db", brief="Database info/query")
    async def db(self, ctx, sub: str = ""):
        await ctx.message.edit(content=S.ui_box("db", [
            f"  {S.DIM}path{S.RESET}   {S._db_path}",
            f"  {S.DIM}notes{S.RESET}  {len((S.load_config() or {}).get('notes',[]))}",
        ]))

    @commands.command(name="history", brief="Show command/db history")
    async def history(self, ctx):
        hist = getattr(S,"_cmd_history",[])
        rows = [f"  {S.GREY}•{S.RESET} {h}" for h in hist[-20:]]
        await ctx.message.edit(content=S._paginate("history","",rows) if rows else S.ui_info("empty"))

async def setup(bot): await bot.add_cog(DbCog(bot))

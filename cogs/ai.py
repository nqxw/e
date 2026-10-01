# cogs/ai.py
import asyncio, aiohttp
from discord.ext import commands
from . import state as S
import aiohttp

_history: list  = []
_sys_prompt: str = ""
_model: str      = "claude-sonnet-4-6"
_api_key: str    = ""
API_URL = "https://api.anthropic.com/v1/messages"

async def _call(messages, system, model):
    key = _api_key or (S.load_config() or {}).get("anthropic_api_key", "")
    if not key: return "⚠ no API key — use .aikey <key>"
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01",
               "content-type": "application/json"}
    body = {"model": model, "max_tokens": 1024, "messages": messages}
    if system: body["system"] = system
    async with aiohttp.ClientSession() as s:
        async with s.post(API_URL, headers=headers, json=body,
                          timeout=aiohttp.ClientTimeout(total=60)) as r:
            if r.status != 200:
                return f"⚠ API error {r.status}"
            d = await r.json(content_type=None)
            return "".join(b.get("text","") for b in d.get("content",[]) if b.get("type")=="text")

class AiCog(commands.Cog, name="ai"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="ai", brief="Chat with Claude API")
    async def ai(self, ctx, *, prompt: str = ""):
        global _history
        if not prompt: return await ctx.message.edit(content=S.ui_err("usage: ai <message>"))
        await ctx.message.edit(content=S.ui_info("thinking…"))
        _history.append({"role": "user", "content": prompt})
        if len(_history) > 40: _history = _history[-40:]
        reply = await _call(_history, _sys_prompt, _model)
        _history.append({"role": "assistant", "content": reply})
        # Always delete the "thinking…" message, then send the response
        await ctx.message.delete()
        for i in range(0, len(reply), 1900):
            await ctx.channel.send(f"```\n{reply[i:i+1900]}\n```")

    @commands.command(name="aimodel", brief="Switch AI model")
    async def aimodel(self, ctx, *, model: str = ""):
        global _model
        if not model:
            rows = [f"  {S.GREY}•{S.RESET} {m}" for m in [
                "claude-sonnet-4-6","claude-haiku-4-5-20251001","claude-opus-4-6"]]
            rows.append(f"  {S.DIM}current: {_model}{S.RESET}")
            return await ctx.message.edit(content=S.ui_box("models", rows))
        _model = model
        cfg = S.load_config(); cfg["ai_model"] = model; S.save_config(cfg)
        await ctx.message.edit(content=S.ui_ok(f"model → `{model}`"))

    @commands.command(name="aisys", brief="Set AI system prompt")
    async def aisys(self, ctx, *, prompt: str = ""):
        global _sys_prompt
        if not prompt:
            return await ctx.message.edit(content=S.ui_info(f"system: {_sys_prompt or '(none)'}"))
        _sys_prompt = prompt
        await ctx.message.edit(content=S.ui_ok(f"system prompt set ({len(prompt)} chars)"))

    @commands.command(name="aiclear", brief="Clear AI history")
    async def aiclear(self, ctx):
        global _history; _history.clear()
        await ctx.message.edit(content=S.ui_ok("history cleared"))

    @commands.command(name="aipop", brief="Remove last AI exchange")
    async def aipop(self, ctx):
        global _history
        if _history: _history.pop()
        if _history: _history.pop()
        await ctx.message.edit(content=S.ui_ok(f"last exchange removed — {len(_history)//2} pairs remain"))

    @commands.command(name="aikey", brief="Set Anthropic API key")
    async def aikey(self, ctx, *, key: str = ""):
        global _api_key
        if not key: return await ctx.message.edit(content=S.ui_err("usage: aikey <key>"))
        _api_key = key
        cfg = S.load_config(); cfg["anthropic_api_key"] = key; S.save_config(cfg)
        await ctx.message.delete()
        await ctx.channel.send(S.ui_ok("API key saved"))

    @commands.command(name="aistatus", brief="AI status")
    async def aistatus(self, ctx):
        key_set = bool(_api_key or (S.load_config() or {}).get("anthropic_api_key"))
        await ctx.message.edit(content=S.ui_box("ai", [
            f"  {S.DIM}model{S.RESET}    {_model}",
            f"  {S.DIM}history{S.RESET}  {len(_history)//2} pairs",
            f"  {S.DIM}system{S.RESET}   {len(_sys_prompt)} chars",
            f"  {S.DIM}api key{S.RESET}  {'set' if key_set else 'not set'}",
        ]))


    @commands.command(name="aihistory", brief="Show AI conversation history")
    async def aihistory(self, ctx):
        hist = _history if "_history" in dir() else getattr(self,"_history",[])
        if not hist: return await ctx.message.edit(content=S.ui_info("no history"))
        rows = [f"  {S.GREY}{'user' if h['role']=='user' else ' ai'}{S.RESET}  {h['content'][:60]}" for h in hist[-20:]]
        await ctx.message.edit(content=S._paginate("ai history","",rows))

async def setup(bot): await bot.add_cog(AiCog(bot))

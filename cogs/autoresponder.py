# cogs/autoresponder.py
import time
import re, time, discord
from discord.ext import commands
from . import state as S

class AutoResponderCog(commands.Cog, name="autoresponder"):
    """Rule-based auto-responder — keyword, regex, scope, cooldown."""
    def __init__(self, bot): self.bot = bot

    @commands.group(name="ar", invoke_without_command=True, brief="Auto-responder rules")
    async def ar(self, ctx):
        if not S.ar_rules:
            return await ctx.message.edit(content=S.ui_info("no rules set"))
        rows = [f"  {S.GREY}{i}{S.RESET} [{r['type']}] `{r['trigger']}` → `{r['response'][:40]}`"
                for i, r in enumerate(S.ar_rules)]
        await ctx.message.edit(content=S._paginate("autoresponder", "", rows))

    @ar.command(name="add")
    async def ar_add(self, ctx, trigger: str = "", *, response: str = ""):
        if not trigger or not response:
            return await ctx.message.edit(content=S.ui_err("usage: ar add <trigger> <response>"))
        S.ar_rules.append({"type": "contains", "trigger": trigger.lower(),
                            "response": response, "cooldown": 30, "last": 0})
        await ctx.message.edit(content=S.ui_ok(f"rule added: `{trigger}` → `{response[:40]}`"))

    @ar.command(name="regex")
    async def ar_regex(self, ctx, pattern: str = "", *, response: str = ""):
        if not pattern or not response:
            return await ctx.message.edit(content=S.ui_err("usage: ar regex <pattern> <response>"))
        try: re.compile(pattern)
        except re.error as e:
            return await ctx.message.edit(content=S.ui_err(f"invalid regex: {e}"))
        S.ar_rules.append({"type": "regex", "trigger": pattern,
                            "response": response, "cooldown": 30, "last": 0})
        await ctx.message.edit(content=S.ui_ok(f"regex rule added: `{pattern}`"))

    @ar.command(name="remove", aliases=["del"])
    async def ar_remove(self, ctx, index: int = -1):
        if 0 <= index < len(S.ar_rules):
            removed = S.ar_rules.pop(index)
            await ctx.message.edit(content=S.ui_ok(f"removed rule {index}: `{removed['trigger']}`"))
        else:
            await ctx.message.edit(content=S.ui_err("invalid index"))

    @ar.command(name="clear")
    async def ar_clear(self, ctx):
        S.ar_rules.clear()
        await ctx.message.edit(content=S.ui_ok("all rules cleared"))

    @ar.command(name="var")
    async def ar_var(self, ctx, key: str = "", *, value: str = ""):
        if not key: return await ctx.message.edit(content=S.ui_info(str(S.ar_variables)))
        if value:
            S.ar_variables[key] = value
            await ctx.message.edit(content=S.ui_ok(f"var {key} = {value}"))
        else:
            S.ar_variables.pop(key, None)
            await ctx.message.edit(content=S.ui_ok(f"var {key} removed"))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.user.id: return
        if not S.ar_rules: return
        content = message.content or ""
        now = time.time()
        for rule in S.ar_rules:
            if now - rule["last"] < rule["cooldown"]: continue
            matched = False
            if rule["type"] == "contains":
                matched = rule["trigger"] in content.lower()
            elif rule["type"] == "regex":
                matched = bool(re.search(rule["trigger"], content, re.I))
            if matched:
                rule["last"] = now
                resp = rule["response"]
                for k, v in S.ar_variables.items():
                    resp = resp.replace(f"{{{k}}}", v)
                resp = resp.replace("{user}", str(message.author))
                resp = resp.replace("{channel}", f"<#{message.channel.id}>")
                try: await message.channel.send(resp)
                except Exception: pass
                break


    @commands.command(name="artest", brief="Test autoresponder against text")
    async def artest(self, ctx, *, text: str = ""):
        if not text: return await ctx.message.edit(content=S.ui_err("usage: artest <text>"))
        import re as _re
        matched = []
        for i, rule in enumerate(S.ar_rules):
            if rule["type"] == "contains" and rule["trigger"] in text.lower(): matched.append(i)
            elif rule["type"] == "regex" and _re.search(rule["trigger"], text, _re.I): matched.append(i)
        if matched:
            rules_str = ", ".join(str(i) for i in matched)
            await ctx.message.edit(content=S.ui_ok(f"matched rules: {rules_str}"))
        else:
            await ctx.message.edit(content=S.ui_info("no rules matched"))

    @commands.command(name="arule", brief="Show details of a rule by index")
    async def arule(self, ctx, index: int = -1):
        if 0 <= index < len(S.ar_rules):
            r = S.ar_rules[index]
            await ctx.message.edit(content=S.ui_box(f"rule {index}", [
                f"  {S.DIM}type{S.RESET}      {r.get('type','?')}",
                f"  {S.DIM}trigger{S.RESET}   {r.get('trigger','?')}",
                f"  {S.DIM}response{S.RESET}  {r.get('response','?')[:60]}",
                f"  {S.DIM}cooldown{S.RESET}  {r.get('cooldown',30)}s",
            ]))
        else:
            await ctx.message.edit(content=S.ui_err("invalid index"))

    @commands.command(name="aruleclear", brief="Clear all autoresponder rules")
    async def aruleclear(self, ctx):
        S.ar_rules.clear()
        await ctx.message.edit(content=S.ui_ok("all rules cleared"))

    @commands.command(name="arules", brief="Alias for ar — list all rules")
    async def arules(self, ctx):
        if not S.ar_rules: return await ctx.message.edit(content=S.ui_info("no rules"))
        rows = [f"  {S.GREY}{i}{S.RESET} [{r['type']}] {r['trigger']} → {r['response'][:40]}"
                for i, r in enumerate(S.ar_rules)]
        await ctx.message.edit(content=S._paginate("ar rules","",rows))

    @commands.command(name="arvars", brief="List/set/remove AR variables")
    async def arvars(self, ctx, key: str = "", *, value: str = ""):
        if not key:
            if not S.ar_variables: return await ctx.message.edit(content=S.ui_info("no vars"))
            rows = [f"  {S.GREY}•{S.RESET} {k} = {v}" for k,v in S.ar_variables.items()]
            return await ctx.message.edit(content=S._paginate("ar vars","",rows))
        if value:
            S.ar_variables[key] = value
            await ctx.message.edit(content=S.ui_ok(f"{key} = {value}"))
        else:
            S.ar_variables.pop(key, None)
            await ctx.message.edit(content=S.ui_ok(f"{key} removed"))

async def setup(bot): await bot.add_cog(AutoResponderCog(bot))
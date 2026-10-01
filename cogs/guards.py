# cogs/guards.py
import discord, aiohttp
from discord.ext import commands
from . import state as S
import aiohttp

class GuardsCog(commands.Cog, name="guards"):
    def __init__(self, bot): self.bot = bot

    @commands.group(name="blacklist", invoke_without_command=True, brief="User blacklist")
    async def blacklist(self, ctx):
        rows = [f"  {S.GREY}•{S.RESET} {uid}" for uid in S._user_blacklist]
        await ctx.message.edit(content=S._paginate("blacklist","",rows) if rows else S.ui_info("empty"))

    @blacklist.command(name="add")
    async def bl_add(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: blacklist add <@user>"))
        S._user_blacklist.add(str(user.id))
        await ctx.message.edit(content=S.ui_ok(f"blacklisted: {user}"))

    @blacklist.command(name="remove")
    async def bl_remove(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: blacklist remove <@user>"))
        S._user_blacklist.discard(str(user.id))
        await ctx.message.edit(content=S.ui_ok(f"removed: {user}"))

    @commands.group(name="whitelist", invoke_without_command=True, brief="User whitelist")
    async def whitelist(self, ctx):
        rows = [f"  {S.GREY}•{S.RESET} {uid}" for uid in S._user_whitelist]
        await ctx.message.edit(content=S._paginate("whitelist","",rows) if rows else S.ui_info("empty"))

    @whitelist.command(name="add")
    async def wl_add(self, ctx, user: discord.User = None):
        if not user: return await ctx.message.edit(content=S.ui_err("usage: whitelist add <@user>"))
        S._user_whitelist.add(str(user.id))
        await ctx.message.edit(content=S.ui_ok(f"whitelisted: {user}"))

    @commands.command(name="serverguard", brief="Server rename protection")
    async def serverguard(self, ctx, sub: str = "status", *, rest: str = ""):
        if sub == "on":
            S._serverguard_enabled = True
            await ctx.message.edit(content=S.ui_ok("server guard → on"))
        elif sub == "off":
            S._serverguard_enabled = False
            await ctx.message.edit(content=S.ui_ok("server guard → off"))
        elif sub == "add" and rest:
            S._serverguard_keywords.add(rest.lower())
            await ctx.message.edit(content=S.ui_ok(f"keyword added: `{rest}`"))
        elif sub == "remove" and rest:
            S._serverguard_keywords.discard(rest.lower())
            await ctx.message.edit(content=S.ui_ok(f"keyword removed: `{rest}`"))
        elif sub == "list":
            rows = [f"  {S.GREY}•{S.RESET} {k}" for k in sorted(S._serverguard_keywords)]
            await ctx.message.edit(content=S._paginate("keywords","",rows))
        else:
            await ctx.message.edit(content=S.ui_box("server guard", [
                f"  {S.DIM}enabled{S.RESET}   {S._serverguard_enabled}",
                f"  {S.DIM}keywords{S.RESET}  {len(S._serverguard_keywords)}",
            ]))

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if not S._serverguard_enabled: return
        text = (str(after.name or "") + " " + str(after.description or "")).lower()
        for kw in S._serverguard_keywords:
            if kw.lower() in text:
                try: await after.leave()
                except Exception: pass
                break


    @commands.command(name="guards", brief="Show guard config")
    async def guards(self, ctx):
        await ctx.message.edit(content=S.ui_box("guards",[
            f"  {S.DIM}ch blacklist{S.RESET}  {len(getattr(S,'_channel_blacklist',set()))}",
            f"  {S.DIM}sv blacklist{S.RESET}  {len(getattr(S,'_server_blacklist',set()))}",
            f"  {S.DIM}role restrict{S.RESET} {len(getattr(S,'_role_restrict',set()))}",
        ]))

    @commands.command(name="channelblacklist", brief="Add/remove channel from blacklist")
    @commands.guild_only()
    async def channelblacklist(self, ctx, channel: discord.TextChannel = None, action: str = "add"):
        if not hasattr(S,"_channel_blacklist"): S._channel_blacklist = set()
        ch = channel or ctx.channel
        if action == "remove": S._channel_blacklist.discard(ch.id)
        else: S._channel_blacklist.add(ch.id)
        await ctx.message.edit(content=S.ui_ok(f"#{ch.name} {'removed from' if action=='remove' else 'added to'} blacklist"))

    @commands.command(name="serverblacklist", brief="Add/remove server from blacklist")
    @commands.guild_only()
    async def serverblacklist(self, ctx, guild_id: int = 0, action: str = "add"):
        if not hasattr(S,"_server_blacklist"): S._server_blacklist = set()
        gid = guild_id or ctx.guild.id
        if action == "remove": S._server_blacklist.discard(gid)
        else: S._server_blacklist.add(gid)
        await ctx.message.edit(content=S.ui_ok(f"server {gid} {'removed from' if action=='remove' else 'added to'} blacklist"))

    @commands.command(name="rolerestrict", brief="Restrict command to role")
    @commands.guild_only()
    async def rolerestrict(self, ctx, role: discord.Role = None):
        if not hasattr(S,"_role_restrict"): S._role_restrict = set()
        if role:
            if role.id in S._role_restrict: S._role_restrict.discard(role.id)
            else: S._role_restrict.add(role.id)
            await ctx.message.edit(content=S.ui_ok(f"role {role.name} toggled"))
        else:
            rows = [f"  {S.GREY}•{S.RESET} <@&{rid}>" for rid in S._role_restrict]
            await ctx.message.edit(content=S._paginate("role restrict","",rows) if rows else S.ui_info("none"))

async def setup(bot): await bot.add_cog(GuardsCog(bot))

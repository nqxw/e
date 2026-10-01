# cogs/rolemgmt.py
import discord
from discord.ext import commands
from . import state as S
from .antid import batch_delay, shuffled

class RoleMgmtCog(commands.Cog, name="rolemgmt"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="roles", brief="List server roles")
    @commands.guild_only()
    async def roles(self, ctx):
        rows = [f"  {S.GREY}•{S.RESET} {r.name} ({len(r.members)} members)"
                for r in ctx.guild.roles if not r.is_default()]
        await ctx.message.edit(content=S._paginate("roles","",rows))

    @commands.command(name="roleinfo", brief="Role information")
    @commands.guild_only()
    async def roleinfo(self, ctx, role: discord.Role = None):
        if not role: return await ctx.message.edit(content=S.ui_err("usage: roleinfo <@role>"))
        await ctx.message.edit(content=S.ui_box("role info", [
            f"  {S.DIM}name{S.RESET}     {role.name}",
            f"  {S.DIM}id{S.RESET}       {role.id}",
            f"  {S.DIM}color{S.RESET}    {role.color}",
            f"  {S.DIM}members{S.RESET}  {len(role.members)}",
            f"  {S.DIM}position{S.RESET} {role.position}",
            f"  {S.DIM}hoist{S.RESET}    {role.hoist}",
            f"  {S.DIM}mentionable{S.RESET} {role.mentionable}",
        ]))

    @commands.command(name="addrole", brief="Add role to member")
    @commands.guild_only()
    async def addrole(self, ctx, member: discord.Member = None, role: discord.Role = None):
        if not member or not role: return await ctx.message.edit(content=S.ui_err("usage: addrole <@member> <@role>"))
        await member.add_roles(role)
        await ctx.message.edit(content=S.ui_ok(f"added {role.name} to {member}"))

    @commands.command(name="removerole", brief="Remove role from member")
    @commands.guild_only()
    async def removerole(self, ctx, member: discord.Member = None, role: discord.Role = None):
        if not member or not role: return await ctx.message.edit(content=S.ui_err("usage: removerole <@member> <@role>"))
        await member.remove_roles(role)
        await ctx.message.edit(content=S.ui_ok(f"removed {role.name} from {member}"))

    @commands.command(name="setcolor", brief="Set role color")
    @commands.guild_only()
    async def setcolor(self, ctx, role: discord.Role = None, color: str = ""):
        if not role or not color: return await ctx.message.edit(content=S.ui_err("usage: setcolor <@role> <hex>"))
        try:
            c = discord.Color(int(color.lstrip("#"), 16))
            await role.edit(color=c)
            await ctx.message.edit(content=S.ui_ok(f"{role.name} color → {color}"))
        except Exception as e:
            await ctx.message.edit(content=S.ui_err(str(e)))


    @commands.command(name="rolelist", brief="List all roles in server")
    @commands.guild_only()
    async def rolelist(self, ctx):
        roles = sorted(ctx.guild.roles, key=lambda r: r.position, reverse=True)
        rows = [f"  {S.GREY}{r.position:>3}.{S.RESET} {r.name}  {S.DIM}#{r.color.value:06x}  {r.id}{S.RESET}"
                for r in roles]
        await ctx.message.edit(content=S._paginate("roles", ctx.guild.name, rows))

    @commands.command(name="rolemembers", brief="List members with a role")
    @commands.guild_only()
    async def rolemembers(self, ctx, *, role: discord.Role = None):
        if not role: return await ctx.message.edit(content=S.ui_err("usage: rolemembers <@role>"))
        rows = [f"  {S.GREY}•{S.RESET} {m.display_name}  {S.DIM}({m.id}){S.RESET}" for m in role.members]
        await ctx.message.edit(content=S._paginate(f"members — {role.name}", f"{len(role.members)}", rows)
                               if rows else S.ui_info("no members"))

    @commands.command(name="roleperms", brief="Show permissions for a role")
    @commands.guild_only()
    async def roleperms(self, ctx, *, role: discord.Role = None):
        if not role: return await ctx.message.edit(content=S.ui_err("usage: roleperms <@role>"))
        perms = [n for n, v in iter(role.permissions) if v]
        rows = [f"  {S.GREY}•{S.RESET} {p}" for p in perms]
        await ctx.message.edit(content=S._paginate(f"perms — {role.name}", "", rows)
                               if rows else S.ui_info("no permissions"))

    @commands.command(name="rolehoisted", brief="Check if role is hoisted")
    @commands.guild_only()
    async def rolehoisted(self, ctx, *, role: discord.Role = None):
        if not role: return await ctx.message.edit(content=S.ui_err("usage: rolehoisted <@role>"))
        await ctx.message.edit(content=S.ui_ok(f"{role.name} hoisted: {role.hoist}"))

    @commands.command(name="rolementionable", brief="Check if role is mentionable")
    @commands.guild_only()
    async def rolementionable(self, ctx, *, role: discord.Role = None):
        if not role: return await ctx.message.edit(content=S.ui_err("usage: rolementionable <@role>"))
        await ctx.message.edit(content=S.ui_ok(f"{role.name} mentionable: {role.mentionable}"))

    @commands.command(name="rolemanaged", brief="Check if role is bot-managed")
    @commands.guild_only()
    async def rolemanaged(self, ctx, *, role: discord.Role = None):
        if not role: return await ctx.message.edit(content=S.ui_err("usage: rolemanaged <@role>"))
        await ctx.message.edit(content=S.ui_ok(f"{role.name} managed: {role.managed}"))

    @commands.command(name="roleid", brief="Get role ID by name")
    @commands.guild_only()
    async def roleid(self, ctx, *, name: str = ""):
        if not name: return await ctx.message.edit(content=S.ui_err("usage: roleid <name>"))
        role = discord.utils.find(lambda r: name.lower() in r.name.lower(), ctx.guild.roles)
        if not role: return await ctx.message.edit(content=S.ui_err("not found"))
        await ctx.message.edit(content=S.ui_ok(f"{role.name} → {role.id}"))

    @commands.command(name="rolecolor", brief="Get or set role color")
    @commands.guild_only()
    async def rolecolor(self, ctx, role: discord.Role = None, color_hex: str = ""):
        if not role: return await ctx.message.edit(content=S.ui_err("usage: rolecolor <@role> [#hex]"))
        if color_hex:
            try:
                val = int(color_hex.lstrip("#"), 16)
                await role.edit(color=discord.Color(val))
                await ctx.message.edit(content=S.ui_ok(f"{role.name} → #{val:06x}"))
            except Exception as e:
                await ctx.message.edit(content=S.ui_err(str(e)))
        else:
            await ctx.message.edit(content=S.ui_ok(f"{role.name} color: #{role.color.value:06x}"))

    @commands.command(name="rolecreated", brief="Show when a role was created")
    @commands.guild_only()
    async def rolecreated(self, ctx, *, role: discord.Role = None):
        if not role: return await ctx.message.edit(content=S.ui_err("usage: rolecreated <@role>"))
        await ctx.message.edit(content=S.ui_ok(f"{role.name} created: {role.created_at.strftime('%Y-%m-%d %H:%M')}"))

    @commands.command(name="roleposition", brief="Show role position in hierarchy")
    @commands.guild_only()
    async def roleposition(self, ctx, *, role: discord.Role = None):
        if not role: return await ctx.message.edit(content=S.ui_err("usage: roleposition <@role>"))
        await ctx.message.edit(content=S.ui_ok(f"{role.name} position: {role.position}"))

    @commands.command(name="rolehierarchy", brief="Show full role hierarchy")
    @commands.guild_only()
    async def rolehierarchy(self, ctx):
        roles = sorted(ctx.guild.roles, key=lambda r: r.position, reverse=True)
        rows = [f"  {S.GREY}{r.position:>3}{S.RESET} {r.name}" for r in roles]
        await ctx.message.edit(content=S._paginate("hierarchy", ctx.guild.name, rows))

async def setup(bot): await bot.add_cog(RoleMgmtCog(bot))

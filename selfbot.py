# selfbot.py | wilt v3.0.0 | discord.py-self
import os, sys, json, math, time, asyncio, signal
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
def _load_cfg():
    try:
        with open("config.json") as f: return json.load(f)
    except Exception: return {}

def _save_cfg(cfg):
    with open("config.json", "w") as f: json.dump(cfg, f, indent=2)

_cfg    = _load_cfg()
TOKEN   = os.environ.get("TOKEN") or _cfg.get("token", "")
VERSION = "3.0.0"

# ── ANSI colour constants (mirrors cogs/state.py) ─────────────────────────────
ESC    = "\x1b"
RESET  = f"{ESC}[0m"
GREY   = f"{ESC}[2;37m"
WHITE  = f"{ESC}[1;37m"
CYAN   = f"{ESC}[36m"
GREEN  = f"{ESC}[32m"
RED    = f"{ESC}[31m"
YELLOW = f"{ESC}[33m"
BLUE   = f"{ESC}[34m"
DIM    = f"{ESC}[2m"
DARK   = f"{ESC}[30m"
BOLD   = f"{ESC}[1m"
CYAN2  = f"{ESC}[0;36m"
WHITE2 = f"{ESC}[0;37m"
BLUE2  = f"{ESC}[0;34m"
BRAND  = f"{ESC}[0;35m{ESC}[1m{ESC}[4m"

# ── Prefix (reads live from state so setprefix works immediately) ─────────────
def _get_prefix(bot, message):
    from cogs import state as S
    gid = str(getattr(message.guild, "id", "")) if message.guild else ""
    if gid and gid in S._server_prefixes:
        return S._server_prefixes[gid]
    return S.PREFIX

# ── Bot ───────────────────────────────────────────────────────────────────────
class WiltBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix = _get_prefix,
            self_bot       = True,
            help_command   = None,
            chunk_guilds_at_startup = False,
        )

    async def setup_hook(self):
        """Load all cogs before connecting."""
        COGS = [
            "cogs.general",   "cogs.settings",  "cogs.information",
            "cogs.server",    "cogs.afk",        "cogs.auto",
            "cogs.autoresponder","cogs.automod",  "cogs.backup",
            "cogs.bumper",    "cogs.db",          "cogs.developer",
            "cogs.downloads", "cogs.filters",     "cogs.fun",
            "cogs.gc",        "cogs.guards",       "cogs.host",
            "cogs.interactions","cogs.lastfm",    "cogs.loggers",
            "cogs.mass",      "cogs.meta",         "cogs.monitor",
            "cogs.multispoof","cogs.nickname",    "cogs.nuke",
            "cogs.perms",     "cogs.pingtrack",   "cogs.profile",
            "cogs.profile_ext","cogs.protect",    "cogs.quests",
            "cogs.reminders", "cogs.resilience",  "cogs.rolemgmt",
            "cogs.rpc", "cogs.scheduler",
            "cogs.scrape",    "cogs.search",       "cogs.sniper",
            "cogs.social",    "cogs.spoofer",      "cogs.status",
            "cogs.tasks",     "cogs.tools",        "cogs.tracking",
            "cogs.triggers",  "cogs.utility",      "cogs.voice",
            "cogs.webhooks",  "cogs.ai",           "cogs.agc",
        ]
        ok = fail = 0
        for cog in COGS:
            try:
                await self.load_extension(cog)
                ok += 1
            except Exception as e:
                print(f"[boot] SKIP {cog}: {e}")
                fail += 1
        print(f"[boot] cogs: {ok} loaded, {fail} failed")

    async def on_ready(self):
        from cogs import state as S
        S.BOT    = self
        S.TOKEN  = self.http.token or TOKEN
        S.PREFIX = _cfg.get("prefix", ".")
        S._live_prefix[0] = S.PREFIX
        print(f"[wilt] v{VERSION} | {self.user} | {len(self.guilds)} guilds")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CommandOnCooldown):
            return await ctx.message.edit(
                content=f"```ansi\n  \x1b[31m✗\x1b[0m  cooldown: {error.retry_after:.1f}s\n```")
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.message.edit(
                content=f"```ansi\n  \x1b[31m✗\x1b[0m  missing argument: {error.param}\n```")
        print(f"[error] {ctx.command}: {error}")

    async def on_message(self, message):
        # selfbot: only route own messages through the command system
        if self.user and message.author.id == self.user.id:
            await self.process_commands(message)

    async def process_commands(self, message):
        if message.author.id != self.user.id:
            return
        await super().process_commands(message)

bot = WiltBot()

# ── Help command ──────────────────────────────────────────────────────────────
# ── Category metadata (order + descriptions matching modifyself) ──────────────
CATEGORY_ORDER = [
    "general",  "quests",   "sniper",       "afk",          "rpc",
    "spoofer",  "status",   "social",       "profile",      "profile_ext",
    "auto",     "autoresponder", "filters", "loggers",      "sniper",
    "tracking", "triggers", "reminders",    "pingtrack",    "guards",
    "voice",    "server",   "rolemgmt",     "information",  "settings",
    "meta",     "developer","tools",        "fun",          "utility",
    "mass",     "nuke",     "search",       "scrape",       "nickname",
    "scheduler","tasks",    "resilience",   "monitor",      "backup",
    "bumper",   "host",     "multispoof",   "agc",          "gc",
    "webhooks", "automod",  "interactions", "perms",        "db",
    "ai",       "downloads","lastfm",       "protect",
]

CATEGORY_DESC = {
    "general":       "utilities, purge, snipe, hypesquad",
    "quests":        "quest completer, auto-enroll, orb badge",
    "sniper":        "nitro sniper, giveaway, extended snipe",
    "afk":           "AFK replies — whitelist, blacklist, per-server",
    "rpc":           "rich presence — 6 slots · icon · appname · xbox/ps/spotify/roblox/vrchat",
    "spoofer":       "platform / device spoofing",
    "status":        "custom status, rotate, steal",
    "social":        "friends, block, pending requests",
    "profile":       "bio, avatar, banner, username",
    "profile_ext":   "avatardl, bannerdl, user notes, personal block",
    "auto":          "autoreact, superreact, mimic, vsniper, nitrosniper",
    "autoresponder": "keyword/regex rule engine + cooldown",
    "filters":       "spam, dupe, link, invite, nsfw, scam filters",
    "loggers":       "message/delete/edit/join/leave/dm loggers",
    "tracking":      "message & profile tracking",
    "triggers":      "message/reaction/voice triggers",
    "reminders":     "reminders, timers, notifications",
    "pingtrack":     "ping counters + mention log",
    "guards":        "blacklists, whitelists, server guard",
    "voice":         "VC controls, vckeep, self-mute/deafen",
    "server":        "ban, kick, mute, channels, server settings",
    "rolemgmt":      "role info, members, perms, color",
    "information":   "user & server lookup, whois",
    "settings":      "prefix, aliases, cooldowns, disable",
    "meta":          "config, debug, cog management, uptime",
    "developer":     "eval, plugins, proxy, sessions, access",
    "tools":         "tokeninfo, calculate, lyrics, robuxtax",
    "fun":           "neko, hug, meme, joke, roleplay",
    "utility":       "text transforms, translate, ghostping",
    "mass":          "massdm, massreact, massfriend, massjoin",
    "nuke":          "destructive ops + server backup",
    "search":        "channel search, bulk delete, msearch",
    "scrape":        "member/channel/role export",
    "nickname":      "auto-nickname + history",
    "scheduler":     "scheduled messages",
    "tasks":         "background task manager",
    "resilience":    "reconnect, session monitor, rate limits",
    "monitor":       "event monitoring & alerts",
    "backup":        "server backup & restore",
    "bumper":        "auto-bump (Disboard, MEE6)",
    "host":          "multi-account token hosting",
    "multispoof":    "concurrent sessions — 4+ device badges",
    "agc":           "anti group-chat trap",
    "gc":            "group DM management",
    "webhooks":      "webhooks, emoji tools",
    "automod":       "automod, raid mode, quarantine, tickets",
    "interactions":  "button & modal handling",
    "perms":         "permission checks",
    "db":            "notes, history, db info",
    "ai":            "Claude AI chat, model, history",
    "downloads":     "yt-dlp video/audio/tiktok/instagram",
    "lastfm":        "last.fm now playing",
    "protect":       "account protection, danger sweep",
}


@bot.command(name="help", aliases=["h"])
async def _help(ctx, *, query: str = ""):
    from cogs import state as S
    raw  = query.strip().lower()
    pfx  = S.PREFIX
    CPER = 15    # commands per category page
    KPER = 10    # categories per root page

    # ── Parse optional trailing page number ──────────────────────────────────
    parts = raw.split()
    page  = 1
    if parts and parts[-1].isdigit():
        page  = max(1, int(parts.pop()))
    q = " ".join(parts)

    # ── Build category map (loaded cogs only) ─────────────────────────────────
    cats: dict = {}
    for cog in bot.cogs.values():
        cname = cog.qualified_name.lower()
        cmds  = [c for c in cog.get_commands() if not c.hidden and c.enabled]
        if cmds:
            cats[cname] = sorted(cmds, key=lambda c: c.name)

    def _block(*lines):
        """Render lines as a single Discord ANSI code block."""
        return S._ansi_block(list(lines))

    def _blockquote(content: str) -> str:
        """Wrap content as a blockquote ANSI block (original style)."""
        inner = "\n".join(f"> {l}" for l in content.split("\n"))
        return f"> ```ansi\n{inner}\n> ```"

    # ════════════════════════════════════════════════════════════════════════
    # ROOT INDEX — .h  /  .h 2
    # ════════════════════════════════════════════════════════════════════════
    if not q:
        # Order by CATEGORY_ORDER, unknowns appended alphabetically at end
        seen = set()
        ordered = []
        for name in CATEGORY_ORDER:
            if name in cats and name not in seen:
                ordered.append(name); seen.add(name)
        for name in sorted(cats):
            if name not in seen:
                ordered.append(name); seen.add(name)

        total_cmds = sum(len(v) for v in cats.values())
        pages      = max(1, math.ceil(len(ordered) / KPER))
        page       = min(page, pages)
        chunk      = ordered[(page-1)*KPER : page*KPER]

        lines = [
            f"  {BRAND}wilt{RESET}  {DIM}v{VERSION}{RESET}"
            f"  {GREY}·  {total_cmds} cmds  ·  {len(ordered)} categories{RESET}",
            f"  {DIM}{'─' * 34}{RESET}", "",
        ]
        for cat in chunk:
            n   = len(cats[cat])
            pad = max(0, 14 - len(cat))
            lines.append(
                f"  {CYAN}{cat}{RESET}{' ' * pad}"
                f"  {DIM}{n:>3} cmd{'s' if n != 1 else ''}{RESET}"
            )
        lines += [
            "",
            f"  {DIM}{'─' * 34}{RESET}",
        ]
        nav = f"{pfx}h <category>  ·  {pfx}h <cmd>"
        if pages > 1:
            nxt = (page % pages) + 1
            nav = f"{pfx}h {nxt} → next  ·  " + nav
        lines.append(f"  {DIM}page {page}/{pages}  ·  {nav}{RESET}")
        return await ctx.message.edit(content=S._ansi_block(lines))

    # ════════════════════════════════════════════════════════════════════════
    # CATEGORY PAGE — .h rpc  /  .h rpc 2
    # Uses 3-block blockquote layout from original
    # ════════════════════════════════════════════════════════════════════════
    if q in cats:
        cmds  = cats[q]
        pages = max(1, math.ceil(len(cmds) / CPER))
        page  = min(page, pages)
        chunk = cmds[(page-1)*CPER : page*CPER]
        col   = max((len(c.name) for c in chunk), default=8)

        # Block 1 — header
        hdr = (f"{BRAND}wilt{RESET}"
               f"{DARK} :: {RESET}"
               f"{WHITE2}v{VERSION}{RESET}"
               f"{DARK} :: {RESET}"
               f"{BLUE2}{q}{RESET}")
        b1 = f"> ```ansi\n> {hdr}\n> ```"

        # Block 2 — command list
        cmd_lines = []
        for c in chunk:
            pad  = col - len(c.name)
            desc = c.brief or (c.help or "").split("\n")[0] or ""
            cmd_lines.append(
                f"> {CYAN2}{c.name}{' ' * pad}{RESET}"
                f"{DARK} :: {RESET}{WHITE2}{desc}{RESET}")
        b2 = "> ```ansi\n" + "\n".join(cmd_lines) + "\n> ```"

        # Block 3 — footer / navigation
        if pages > 1:
            nxt = (page % pages) + 1
            nav = f"{pfx}h {q} {nxt}"
        else:
            nav = f"{pfx}h <cmd>"
        b3 = (f"> ```ansi\n"
              f"> {DARK}page {page}/{pages}  ·  {nav}  ·  {pfx}h  back to index{RESET}\n"
              f"> ```")

        return await ctx.message.edit(content="\n".join([b1, b2, b3]))

    # ════════════════════════════════════════════════════════════════════════
    # SINGLE COMMAND — .h ping
    # ════════════════════════════════════════════════════════════════════════
    cmd = bot.get_command(q)
    if cmd:
        cog_name = cmd.cog.qualified_name.lower() if cmd.cog else "—"
        als      = "  ".join(f"{pfx}{a}" for a in cmd.aliases) if cmd.aliases else "—"
        sig      = cmd.signature or ""
        desc     = cmd.help or cmd.brief or "no description"

        lines = [
            f"  {WHITE}{pfx}{cmd.name}"
            + (f"  {GREY}{sig}{RESET}" if sig else f"{RESET}"),
            f"  {DIM}{'─' * 34}{RESET}", "",
            f"  {GREY}category{RESET}  {CYAN}{cog_name}{RESET}",
            f"  {GREY}aliases {RESET}  {DIM}{als}{RESET}",
            "",
            f"  {WHITE2}{desc}{RESET}",
        ]
        if hasattr(cmd, "commands"):
            subs = sorted(cmd.commands, key=lambda c: c.name)
            if subs:
                lines += ["", f"  {GREY}sub-commands{RESET}"]
                col2 = max(len(s.name) for s in subs)
                for sub in subs:
                    pad = col2 - len(sub.name)
                    lines.append(
                        f"  {GREY}├ {CYAN2}{sub.name}{RESET}{' ' * pad}"
                        f"  {DIM}{sub.brief or ''}{RESET}")
        lines += [
            "",
            f"  {DIM}{'─' * 34}{RESET}",
            f"  {DIM}{pfx}h {cog_name}  ·  back to category{RESET}",
        ]
        return await ctx.message.edit(content=S._ansi_block(lines))

    # ── Fuzzy fallback ────────────────────────────────────────────────────────
    all_cmds = [c for cog in bot.cogs.values() for c in cog.get_commands()]
    matches  = [c for c in all_cmds
                if q in c.name or c.name.startswith(q[:3])][:8]
    if matches:
        lines = [
            f"  {RED}✗{RESET}  unknown: {WHITE}{q}{RESET}",
            f"  {DIM}{'─' * 34}{RESET}", "",
            f"  {GREY}did you mean?{RESET}", "",
        ]
        for c in matches:
            cg  = c.cog.qualified_name.lower() if c.cog else "?"
            pad = max(0, 18 - len(c.name))
            lines.append(
                f"  {CYAN2}{pfx}{c.name}{RESET}{' ' * pad}"
                f"  {DIM}{c.brief or ''}  [{cg}]{RESET}")
        return await ctx.message.edit(content=S._ansi_block(lines))

    await ctx.message.edit(
        content=S.ui_err(f"unknown command or category: `{q}`"))


@bot.command(name="ping")
async def _ping(ctx):
    from cogs import state as S
    ms = round(bot.latency * 1000)
    await ctx.message.edit(content=S.ui_ok(f"pong — `{ms}ms`"))

# ── Run ───────────────────────────────────────────────────────────────────────
if not TOKEN:
    sys.exit("TOKEN not set — add to config.json or TOKEN env var")

bot.run(TOKEN, log_handler=None)

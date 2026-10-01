# cogs/state.py — shared state for all discord.py-self cogs
import json, os, time, re
from collections import defaultdict
import aiohttp
import time

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

# ── Runtime refs ──────────────────────────────────────────────────────────────
BOT     = None    # set in selfbot.py on_ready
TOKEN   = ""
PREFIX  = "."
VERSION = "3.0.0"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ── Config helpers ────────────────────────────────────────────────────────────
def load_config() -> dict:
    try:
        with open("config.json") as f: return json.load(f)
    except Exception: return {}

def save_config(cfg: dict):
    with open("config.json", "w") as f: json.dump(cfg, f, indent=2)

# ── Command state ─────────────────────────────────────────────────────────────
_aliases:       dict = {}
_cooldowns:     dict = {}
_cooldown_last: dict = {}
_cmd_disabled:  set  = set()
_global_cooldown: float = 0.0
_server_prefixes: dict = {}

# ── User lists ────────────────────────────────────────────────────────────────
_user_blacklist: set = set()
_user_whitelist: set = set()
_role_restrict:  dict = {}
_perm_allow:     dict = {}
_perm_block:     set  = set()
_perm_channel:   dict = {}
_perm_server:    dict = {}
_admins:         set  = set()
_devs:           set  = set()

# ── AFK ───────────────────────────────────────────────────────────────────────
afk = {
    "enabled": False, "message": "", "expires_at": 0,
    "emergency": False, "dm_only": False, "cooldown": 30,
    "blacklist": set(), "whitelist": set(),
    "custom_replies": {}, "per_server": {},
    "last_reply": {}, "ping_counter": {},
}

# ── Filters ───────────────────────────────────────────────────────────────────
filters = {
    "spam":        {"enabled": False, "threshold": 5, "window": 5, "history": {}},
    "duplicate":   {"enabled": False, "window": 30, "history": {}},
    "link":        {"enabled": False, "whitelist": set()},
    "invite":      {"enabled": False},
    "attachment":  {"enabled": False},
    "nsfw":        {"enabled": False, "keywords": set()},
    "mention_spam":{"enabled": False, "threshold": 5},
    "mass_ping":   {"enabled": False},
    "scam":        {"enabled": False},
    "bot":         {"enabled": False},
    "webhook":     {"enabled": False},
    "auto_purge":  {"enabled": False, "keep": 50},
    "log_channel": None, "actions_log": [],
}

# ── Loggers ───────────────────────────────────────────────────────────────────
loggers = {k: {"enabled": False, "channel": None}
           for k in ("message","deleted","edited","reaction",
                     "mention","dm","joins","leaves")}

# ── Sniper ────────────────────────────────────────────────────────────────────
SNIPER_ENABLED = True
_snipe_cache:     dict = {}
_editsnipe_cache: dict = {}
_vsniper_list:    list = []
_vsniper_task = None
_nitrosniper_enabled = True
_giveaway_enabled    = False

# ── RPC ───────────────────────────────────────────────────────────────────────
_current_platform = "desktop"

# ── Auto ──────────────────────────────────────────────────────────────────────
AUTO_RESPONSES:      dict = {}
_autoreact_users:    dict = {}
_superreact_users:   dict = {}
_multireact_users:   dict = {}
_mimic_dict:         dict = {}
_tracked_users:      set  = set()
_tracking:           dict = {}
_autoaddback:        bool = False

# ── AR ────────────────────────────────────────────────────────────────────────
ar_rules:     list = []
ar_variables: dict = {}

# ── Triggers ──────────────────────────────────────────────────────────────────
_triggers = {"message": [], "reaction": [], "voice": [], "member": []}
_trigger_fired_counts: dict = {}

# ── Nickname ──────────────────────────────────────────────────────────────────
nickname = {
    "enabled": False, "pattern": "{user}",
    "interval": 300, "history": {},
}

# ── Meta ──────────────────────────────────────────────────────────────────────
meta = {
    "debug": False, "dev_mode": False,
    "status_watch": {"enabled": False, "interval": 300, "last": 0},
    "webhook": None, "github_repo": None,
    "gh_notify_ch": None, "github_last": None,
}

# ── Scheduler / Tasks ─────────────────────────────────────────────────────────
_scheduler:     list = []
_managed_tasks: dict = {}
_TASK_STORE:    dict = {}
_TRIGGER_STORE: dict = {}

# ── DB ────────────────────────────────────────────────────────────────────────
_db      = None
_db_path = "database.db"

# ── Misc ──────────────────────────────────────────────────────────────────────
_pending_interactions: list = []
_buttons_enabled = False
_modals_enabled  = False
_spam_tasks:      dict = {}
_proxy           = None
_plugins:         dict = {}
_sessions:        list = []
_session_idx     = 0
_cache_auto      = False
_latency_history: list = []
_session_events:  list = []
_rate_limit_events: list = []
_auto_reconnect  = True
_auto_restart    = False
_reconnect_count = 0
_protect_enabled = False
_protect_log_ch  = 0
_serverguard_enabled  = False
_serverguard_keywords: set = {
    "child porn","cp server","csam","loli porn","shota porn",
    "gore server","snuff","animal abuse","zoophilia server",
    "drug market","hitman","terrorism","mass shooter",
    "ddos server","rat server","malware server",
}
_serverguard_log_ch: int = 0
LOGGER_ENABLED = False
LOG_FILE = "wilt.log"
LASTFM_BASE = "http://ws.audioscrobbler.com/2.0/"
HOUSE_IDS   = {}
HOUSE_NAMES = {}
_agc_state = {
    "enabled": False, "block": False, "leave_msg": "",
    "gc_name": "", "gc_icon_url": None, "webhook_url": None,
}
_agc_whitelist: set = set()
_automod = {"enabled": False, "words": [], "action": "delete", "log_ch": None}
_raidmode = {"enabled": False, "threshold": 10}
_quarantine = {"enabled": False, "role_id": None, "age_days": 7}
_ticket_cfg = {"category_id": None}
_verify_cfg = {"role_id": None}
_speak_lang = None
neko_gif = None
HOSTED_TOKENS: list = []
_host_sessions: list = []
_hosted_clients: list = []
_live_prefix: list = ["."]

# ── UI helpers ────────────────────────────────────────────────────────────────
def _ansi_block(lines) -> str:
    parts = []
    for line in lines:
        parts.append("" if not line.strip() else line)
    body = chr(10).join(parts).strip()
    return "```ansi\n" + body + "\n```"

def ui_box(title: str, rows, footer: str = "") -> str:
    lines = [f"  {WHITE}{title}{RESET}"] + list(rows)
    if footer: lines += ["", f"  {DIM}{footer}{RESET}"]
    return _ansi_block(lines)

def ui_ok(msg):   return _ansi_block([f"  {GREEN}✓{RESET}  {msg}"])
def ui_err(msg):  return _ansi_block([f"  {RED}✗{RESET}  {msg}"])
def ui_info(msg): return _ansi_block([f"  {CYAN}•{RESET}  {msg}"])
def ui_warn(msg): return _ansi_block([f"  {YELLOW}!{RESET}  {msg}"])

def ui_progress(label: str, pct: int) -> str:
    filled = int(max(0, min(pct, 100)) / 10)
    bar    = f"{GREEN}{'█' * filled}{GREY}{'░' * (10 - filled)}{RESET}"
    return f"  {bar} {WHITE}{pct}%{RESET}  {DIM}{label}{RESET}"

def _paginate(title: str, subtitle: str, rows: list, page: int = 1) -> str:
    PAGE  = 8
    total = max(1, math.ceil(len(rows) / PAGE))
    page  = max(1, min(page, total))
    chunk = rows[(page-1)*PAGE : page*PAGE]
    lines = [f"  {WHITE}> {title}{RESET}  {DIM}{subtitle}{RESET}", ""] + chunk + [
        "", f"  {DIM}page {page}/{total}{RESET}",
    ]
    return _ansi_block(lines)

def _get_session():
    return None  # aiohttp sessions now managed per-cog or via bot._session

def log_msg(msg: str):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception: pass

# ── Missing vars referenced by cogs ──────────────────────────────────────────
OWNER_ID: int           = 0
access_save: dict       = {}

_channel_blacklist: set  = set()
_server_blacklist:  set  = set()
_user_notes:        dict = {}
personal_blocklist: set  = set()
personal_ignore:    set  = set()
profile_history:    dict = {}

_ping_tracking: dict = {}
_ping_log:      list = []

_notify_watch: dict = {}

_dev_mode:     bool = False
_error_log:    list = []
_github_watch: dict = {}

_vsniper_enabled: bool = True
_autoreconnect:   bool = True   # alias for _auto_reconnect
_autorestart:     bool = False  # alias for _auto_restart
_rate_limit_events: list = []

_serverguard_user_whitelist: set = set()
_user_blacklist2: set = set()

# spoofer.py calls S.get() — patch as a module-level function alias
def get(key, default=None):
    import cogs.state as _s
    return getattr(_s, key, default)

# ── Config persistence ────────────────────────────────────────────────────────
def load_config() -> dict:
    import json, os
    try:
        if os.path.exists("config.json"):
            with open("config.json", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_config(cfg: dict) -> None:
    import json
    try:
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[state] save_config: {e}")

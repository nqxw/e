# cogs/antid.py | Anti-detection helpers
# Used by mass, nuke, scrape, quests, auto, typing, sniper cogs.
import asyncio
import random
import time

# ── tunables (change via .antid command) ────────────────────────────────────
CFG = {
    "batch_min":    1.2,   # min seconds between bulk actions
    "batch_max":    3.8,   # max seconds between bulk actions
    "burst_every":  5,     # after this many actions, take a longer break
    "burst_min":    4.0,   # longer break min
    "burst_max":    9.0,   # longer break max
    "jitter_pct":   0.25,  # ±25% timing jitter on fixed intervals
    "typo_chance":  0.0,   # future: occasional typo simulation
}


def jitter(base: float, pct: float | None = None) -> float:
    """Return base ± pct% random variation."""
    p = pct if pct is not None else CFG["jitter_pct"]
    return base * (1 + random.uniform(-p, p))


async def delay(min_s: float | None = None, max_s: float | None = None):
    """Sleep a random human-like duration between min and max seconds."""
    lo = min_s if min_s is not None else CFG["batch_min"]
    hi = max_s if max_s is not None else CFG["batch_max"]
    await asyncio.sleep(random.uniform(lo, hi))


async def batch_delay(n: int = 1):
    """
    Standard delay between bulk actions.
    Every CFG['burst_every'] actions takes a longer break.
    """
    if n > 0 and n % CFG["burst_every"] == 0:
        await asyncio.sleep(random.uniform(CFG["burst_min"], CFG["burst_max"]))
    else:
        await asyncio.sleep(random.uniform(CFG["batch_min"], CFG["batch_max"]))


def shuffled(seq):
    """Return a shuffled copy — randomize action order to avoid patterns."""
    lst = list(seq)
    random.shuffle(lst)
    return lst


async def on_rate_limit(retry_after: float):
    """Back off after a 429 with extra jitter so we don't immediately retry."""
    wait = retry_after + random.uniform(1.0, 3.0)
    print(f"[antid] rate limited — waiting {wait:.1f}s")
    await asyncio.sleep(wait)


def rand_interval(base_minutes: float) -> float:
    """
    Convert a fixed interval (minutes) to a jittered one.
    e.g. 30min loop → actually runs every 24–36 min.
    """
    base_s = base_minutes * 60
    return jitter(base_s, CFG["jitter_pct"])

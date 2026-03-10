# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# ## Bulk Sharing Automation
# Share AGOL items to groups and set access levels based on tag rules.
#
# **How to use:**
# 1. Edit the `RULES` list in the Configuration cell below.
# 2. Set `DRY_RUN = True` and run all cells to preview changes.
# 3. Review the summary. When satisfied, set `DRY_RUN = False` and re-run.
#
# **Requirements:**
# - The running account must be a member of every target group.
# - Items must be owned by the running account.
#
# ---
#
# #### Run this cell to connect to your GIS and get started:

# %%
from arcgis.gis import GIS
gis = GIS("home")
me = gis.users.me
print(f"Connected as: {me.username} ({me.fullName})\n")

# %% [markdown]
# ---
#
# ### Configuration
# Edit the `RULES` list and `DRY_RUN` flag, then run the remaining cells.

# %%
# ══════════════════════════════════════════════════════════════════════
#  CONFIGURATION — edit this section only
# ══════════════════════════════════════════════════════════════════════

DRY_RUN = False   # True = preview only, no changes made
VERBOSE = False   # True = also stream log to console

RULES = [
    {
        # ── Items to target ───────────────────────────────────────
        # Items must carry ALL of these tags (case-insensitive).
        "tags": [
            "gnb",
            "overture maps",
        ],
        # ── Sharing level (optional) ──────────────────────────────
        # ""        → keep the item's current access level
        # "group"   → group members only (default AGOL visibility)
        # "org"     → all organisation members
        # "public"  → everyone (including anonymous users)
        # "private" → owner only — WARNING: removes all group sharing
        "level": "org",
        # ── Groups to share with ──────────────────────────────────
        "groups": [
            "Geospatial Hub Editors",
        ],
    },
    # ── Copy the block above to add more rules ───────────────────
    # {
    #     "tags": ["syr", "overture maps"],
    #     "level": "",
    #     "groups": ["Syria Geospatial Data Hub Editors"],
    # },
]

# %% [markdown]
# ---
#
# ### Execution
# **Do not edit below this line.** Just run the remaining cells.

# %%
import warnings
import logging
from urllib3.exceptions import InsecureRequestWarning
from tqdm.notebook import tqdm

warnings.filterwarnings("ignore", category=InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# /arcgis/home is the only persistent path in AGOL Notebooks.
LOG_FILE = "/arcgis/home/agol_sharing.log"

log = logging.getLogger("agol_sharing")
log.setLevel(logging.DEBUG)
log.handlers.clear()
_fh = logging.FileHandler(LOG_FILE)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(_fh)
if VERBOSE:
    _ch = logging.StreamHandler()
    _ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    log.addHandler(_ch)

log.info(f"Connected as {me.username} | API version: {gis.version}")

VALID_LEVELS = {"group", "org", "public", "private"}
LEVEL_FLAGS = {
    "group":   {"everyone": "false", "org": "false"},
    "org":     {"everyone": "false", "org": "true"},
    "public":  {"everyone": "true",  "org": "false"},
    "private": {"everyone": "false", "org": "false"},
}
STATUS_ICONS = {"OK": "✓", "SKIP": "⊘", "DRY RUN": "○", "ERROR": "✗"}


def get_group(name):
    """Resolve a group by exact title match."""
    results = gis.groups.search(f'title:"{name}"', max_groups=5)
    for g in results:
        if g.title == name:
            return g
    log.warning(f"Group not found: '{name}'")
    return None


def item_has_all_tags(item, required_tags):
    """Check that an item carries every tag in the list (case-insensitive)."""
    item_tags = {t.lower() for t in (item.tags or [])}
    return all(t.lower() in item_tags for t in required_tags)


def search_by_tags(tags):
    """Return items owned by the service account that match all tags."""
    tag_query = " AND ".join(f'tags:"{t}"' for t in tags)
    return gis.content.search(
        f"owner:{me.username} AND ({tag_query})", max_items=1000
    )


def get_shared_group_ids(item):
    """Return the set of group IDs an item is currently shared with."""
    try:
        listed = item.sharing.groups.list()
        if listed is not None:
            return {g.id for g in listed}
    except Exception:
        pass
    return {g["id"] for g in (item.get("groups") or [])}


def set_sharing_level(item, level):
    """Set the item's access level via REST. Does NOT touch group membership."""
    flags = LEVEL_FLAGS[level]
    url = f"{gis.url}/sharing/rest/content/users/{me.username}/items/{item.id}/share"
    payload = {
        "f":        "json",
        "everyone": flags["everyone"],
        "org":      flags["org"],
        "groups":   "",
    }
    response = gis._con.post(url, payload)
    log.info(f"Level={level} | {item.title!r} | response={response}")
    return response


def share_to_group(item, group):
    """Share an item to a single group without changing its access level."""
    result = item.sharing.groups.add(group=group)
    if result is True:
        return "python-api"
    url = f"{gis.url}/sharing/rest/content/users/{me.username}/items/{item.id}/share"
    response = gis._con.post(url, {"f": "json", "groups": group.id})
    if group.id in response.get("notSharedWith", []):
        raise RuntimeError(f"REST rejected: {response}")
    return "rest-fallback"


def validate_rules(rules):
    """Pre-flight check: abort early on bad config rather than mid-run."""
    errors = []
    for i, rule in enumerate(rules, 1):
        if not rule.get("tags"):
            errors.append(f"Rule {i}: 'tags' list is empty or missing.")
        level = (rule.get("level") or "").strip()
        if level and level not in VALID_LEVELS:
            errors.append(
                f"Rule {i}: unknown level '{level}' "
                f"(choose from: {', '.join(sorted(VALID_LEVELS))})."
            )
        if level == "private" and rule.get("groups"):
            errors.append(
                f"Rule {i}: level='private' removes all group sharing — "
                "listing groups is contradictory."
            )
    return errors


config_errors = validate_rules(RULES)
if config_errors:
    print("Configuration errors — fix before running:\n")
    for e in config_errors:
        print(f"  ✗  {e}")
    raise SystemExit(1)

if DRY_RUN:
    print("── DRY RUN ── no changes will be made ──\n")

# %%
counts = {"ok": 0, "skip": 0, "dry_run": 0, "error": 0, "group_warn": 0}
results_log = []
level_log = []

for rule in RULES:
    required_tags = rule["tags"]
    target_group_names = rule["groups"]
    sharing_level = (rule.get("level") or "").strip() or None

    log.info(
        f"Rule | tags={required_tags} | level={sharing_level} "
        f"| groups={target_group_names}"
    )

    target_groups = [g for name in target_group_names if (g := get_group(name))]
    for name in set(target_group_names) - {g.title for g in target_groups}:
        print(f"  ⚠  Group not found: '{name}'")
        counts["group_warn"] += 1

    candidates = search_by_tags(required_tags)
    matched = [item for item in candidates if item_has_all_tags(item, required_tags)]
    log.info(f"Matched {len(matched)} item(s)")

    tag_label = ", ".join(required_tags)
    print(f"\n  Rule: tags=[{tag_label}]  level={sharing_level or '—'}"
          f"  →  {len(matched)} item(s), {len(target_groups)} group(s)")

    for item in tqdm(matched, desc=f"[{tag_label}]", unit="item"):
        if DRY_RUN:
            if sharing_level:
                level_log.append((item.title, sharing_level, "DRY RUN"))
            for group in target_groups:
                results_log.append((item.title, group.title, "DRY RUN", ""))
                counts["dry_run"] += 1
            continue

        if sharing_level:
            try:
                set_sharing_level(item, sharing_level)
                level_log.append((item.title, sharing_level, "OK"))
            except Exception as e:
                log.error(f"Level ERROR | {item.title!r}: {e}")
                level_log.append((item.title, sharing_level, "ERROR"))
                counts["error"] += 1
                continue

        shared_group_ids = get_shared_group_ids(item)
        for group in target_groups:
            if group.id in shared_group_ids:
                log.debug(f"SKIP | {item.title!r} → '{group.title}'")
                results_log.append((item.title, group.title, "SKIP", ""))
                counts["skip"] += 1
            else:
                try:
                    method = share_to_group(item, group)
                    log.info(f"OK ({method}) | {item.title!r} → '{group.title}'")
                    results_log.append((item.title, group.title, "OK", method))
                    counts["ok"] += 1
                except Exception as e:
                    log.error(f"ERROR | {item.title!r} → '{group.title}': {e}")
                    results_log.append((item.title, group.title, "ERROR", str(e)))
                    counts["error"] += 1

# %%
val_results = []

if not DRY_RUN:
    for rule in RULES:
        required_tags = rule["tags"]
        target_group_names = rule["groups"]
        sharing_level = (rule.get("level") or "").strip() or None

        if sharing_level == "private":
            continue

        candidates = search_by_tags(required_tags)
        matched = [i for i in candidates if item_has_all_tags(i, required_tags)]
        target_groups = [g for name in target_group_names if (g := get_group(name))]

        for item in tqdm(matched, desc="Validating", unit="item"):
            fresh = gis.content.get(item.id)
            shared_group_ids = get_shared_group_ids(fresh)
            for group in target_groups:
                passed = group.id in shared_group_ids
                val_results.append((fresh.title, group.title, passed))
                log.debug(
                    f"{'PASS' if passed else 'FAIL'} | "
                    f"{fresh.title!r} ∈ '{group.title}'"
                )

val_pass = sum(1 for *_, p in val_results if p)
val_fail = sum(1 for *_, p in val_results if not p)

# %%
mode_label = "DRY RUN" if DRY_RUN else "LIVE"

print(f"""
┌──────────────────────────────────┐
│  RUN SUMMARY  ({mode_label:^8})         │
├──────────────────────────────────┤
│  ✓  Shared      : {counts['ok']:<14}│
│  ⊘  Skipped     : {counts['skip']:<14}│
│  ✗  Errors      : {counts['error']:<14}│
│  ⚠  Bad groups  : {counts['group_warn']:<14}│""")

if not DRY_RUN and val_results:
    print(f"""\
├──────────────────────────────────┤
│  Validation                      │
│  ✓  Pass        : {val_pass:<14}│
│  ✗  Fail        : {val_fail:<14}│""")

if DRY_RUN:
    print(f"""\
├──────────────────────────────────┤
│  ○  Previewed   : {counts['dry_run']:<14}│""")

print("└──────────────────────────────────┘")

if level_log:
    print("\n── Access Level ──────────────────────────────────────────────────────")
    for item_title, level_str, status in level_log:
        icon = STATUS_ICONS.get(status, "?")
        print(f"  {icon}  {status:<8}  {item_title!r} → {level_str}")

if results_log:
    print("\n── Group Sharing ─────────────────────────────────────────────────────")
    for item_title, group_title, status, detail in results_log:
        icon = STATUS_ICONS.get(status, "?")
        detail_str = (
            f"  ({detail})" if detail and status == "OK"
            else f"  ← {detail}" if detail
            else ""
        )
        print(f"  {icon}  {status:<8}  {item_title!r} → '{group_title}'{detail_str}")

if not DRY_RUN and val_results:
    print("\n── Validation ────────────────────────────────────────────────────────")
    for item_title, group_title, passed in val_results:
        icon = "✓" if passed else "✗"
        print(f"  {icon}  {item_title!r} → '{group_title}'")

print(f"\n  Log → {LOG_FILE}")
if counts["error"] or val_fail:
    print(f"  ⚠  Issues detected — review log: cat {LOG_FILE}")

for handler in log.handlers[:]:
    handler.close()
    log.removeHandler(handler)

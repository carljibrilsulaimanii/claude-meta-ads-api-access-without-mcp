# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-adset-optimization-settings.py — run from the repo root (README "More example analyses")
# What: for the ad sets in campaigns whose name contains a keyword, prints how each is
#       really optimized: optimization_goal, destination_type, promoted_object (the
#       conversion event or sequence), optimization_sub_event and attribution_spec
#       (the click and view windows Meta credits conversions on).
# Why:  optimization_goal alone is ambiguous. OFFSITE_CONVERSIONS covers a single-event
#       setup and a LEAD -> PURCHASE sequence alike; only promoted_object tells them
#       apart. attribution_spec shows each ad set's window (e.g. 7-day click), which is
#       why Ads Manager's conversion count is wider than a CRM's last-click count.
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-adset-optimization-settings.py KEYWORD [LIMIT] [--all]
#         python examples/meta-adset-optimization-settings.py "Retargeting" 5
#         KEYWORD matches campaign names, case-insensitive. Active ad sets only, unless --all.

import os, sys, json, urllib.parse, urllib.request, urllib.error

ACT = "act_REPLACE_WITH_AD_ACCOUNT_ID"   # keep the act_ prefix (README Step 5g)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)

args = [a for a in sys.argv[1:] if a != "--all"]
ALL = "--all" in sys.argv[1:]
if not args:
    sys.exit("usage: python examples/meta-adset-optimization-settings.py KEYWORD [LIMIT] [--all]")
KEYWORD = args[0].lower()
LIMIT = int(args[1]) if len(args) > 1 else 10

if "REPLACE_WITH" in ACT:
    sys.exit("set ACT at the top of this file to your ad account id")

tp = os.path.join(os.path.expanduser("~"), ".meta-ads", "token")
if not os.path.exists(tp):
    sys.exit("token file not found: %s" % tp)
TOKEN = open(tp, encoding="utf-8-sig").read().strip().strip('"').strip("'")
if not TOKEN:
    sys.exit("token file is empty")
print("token loaded (%d chars) — not printed, not stored\n" % len(TOKEN))

FIELDS = ("name,effective_status,optimization_goal,billing_event,bid_strategy,"
          "promoted_object,attribution_spec,destination_type,optimization_sub_event,"
          "campaign{name,objective}")

rows, url = [], "%s/%s/adsets?%s" % (API, ACT, urllib.parse.urlencode(
    {"fields": FIELDS, "limit": 300, "access_token": TOKEN}))
while url:
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            j = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(e.read().decode("utf-8", "replace")[:300])
    rows.extend(j.get("data", []))
    url = j.get("paging", {}).get("next")


def show(r):
    c = r.get("campaign") or {}
    po = r.get("promoted_object") or {}
    print("  %-46s %s" % (r.get("name", "")[:46], r.get("effective_status")))
    print("      campaign      : %s  (%s)" % (c.get("name", "")[:60], c.get("objective")))
    print("      optimization  : %s" % r.get("optimization_goal"))
    print("      destination   : %s" % r.get("destination_type"))
    if po:
        print("      promoted_obj  : %s" % json.dumps(po))
    if r.get("optimization_sub_event"):
        print("      sub_event     : %s" % r.get("optimization_sub_event"))
    if r.get("attribution_spec"):
        print("      attribution   : %s" % json.dumps(r.get("attribution_spec")))
    print()


hits = [r for r in rows
        if KEYWORD in ((r.get("campaign") or {}).get("name") or "").lower()
        and (ALL or r.get("effective_status") == "ACTIVE")]

print("=" * 84)
print("AD SETS in campaigns matching '%s'  (%s, showing %d of %d)"
      % (KEYWORD, "any status" if ALL else "active only", min(LIMIT, len(hits)), len(hits)))
print("=" * 84)
for r in hits[:LIMIT]:
    show(r)

# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-period-compare.py — run from the repo root (README "More example analyses")
# What: one aggregate row per date window you pass in: spend, impressions, reach, CPM
#       (as Meta reports it and as spend / impressions), leads, impression-to-lead rate
#       and CPL. Use it for this season vs last season, this week vs last week, or any
#       "same window, different year" comparison.
# Why:  adding up daily rows by hand gets reach wrong (people are counted once per day,
#       not once per window) and invites arithmetic slips. Asking the API for each window
#       as one aggregate gives one authoritative row per window to quote from.
#       Leads use the 'lead' action type ONLY, never summed with
#       offsite_conversion.fb_pixel_lead or onsite_web_lead, which can return the same count.
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-period-compare.py SINCE:UNTIL [SINCE:UNTIL ...]
#         python examples/meta-period-compare.py 2026-03-01:2026-03-31 2025-03-01:2025-03-31

import os, sys, json, urllib.parse, urllib.request, urllib.error

ACT = "act_REPLACE_WITH_AD_ACCOUNT_ID"   # keep the act_ prefix (README Step 5g)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)

if len(sys.argv) < 2 or any(":" not in a for a in sys.argv[1:]):
    sys.exit("usage: python examples/meta-period-compare.py SINCE:UNTIL [SINCE:UNTIL ...]   (dates as YYYY-MM-DD)")
WINDOWS = [(a, a.split(":")[0], a.split(":")[1]) for a in sys.argv[1:]]

if "REPLACE_WITH" in ACT:
    sys.exit("set ACT at the top of this file to your ad account id")

tp = os.path.join(os.path.expanduser("~"), ".meta-ads", "token")
if not os.path.exists(tp):
    sys.exit("token file not found: %s" % tp)
TOKEN = open(tp, encoding="utf-8-sig").read().strip().strip('"').strip("'")
if not TOKEN:
    sys.exit("token file is empty")
print("token loaded (%d chars) — not printed, not stored\n" % len(TOKEN))


def pull(since, until):
    p = {
        "time_range": json.dumps({"since": since, "until": until}),
        "fields": "spend,impressions,reach,cpm,actions",
        "level": "account",
        "access_token": TOKEN,
    }
    try:
        with urllib.request.urlopen(
                API + "/" + ACT + "/insights?" + urllib.parse.urlencode(p),
                timeout=120) as r:
            j = json.load(r)
    except urllib.error.HTTPError as e:
        return {"__error": e.read().decode("utf-8", "replace")[:200]}
    d = j.get("data", [])
    return d[0] if d else {}


for label, since, until in WINDOWS:
    print("=" * 66)
    print(label + "   (" + since + " to " + until + ")")
    print("=" * 66)
    row = pull(since, until)

    if "__error" in row:
        print("  API error: " + row["__error"])
        print("")
        continue
    if not row:
        print("  no data returned")
        print("")
        continue

    spend = float(row.get("spend", 0))
    impr = int(row.get("impressions", 0))
    leads = 0
    for a in row.get("actions", []):
        if a.get("action_type") == "lead":
            leads = int(float(a.get("value", 0)))

    print("  spend                 : $" + format(spend, ",.2f"))
    print("  impressions           : " + format(impr, ","))
    print("  reach                 : " + format(int(row.get("reach", 0)), ","))
    print("  CPM (API)             : $" + format(float(row.get("cpm", 0) or 0), ",.2f"))
    if impr:
        print("  CPM (derived)         : $" + format(spend / impr * 1000, ",.2f"))
    print("  leads (action=lead)   : " + format(leads, ","))
    if impr and leads:
        rate = leads / impr * 100
        print("  impression-to-lead    : " + format(rate, ",.4f") + "%")
        print("  leads per 1k impr     : " + format(leads / impr * 1000, ",.3f"))
        print("  CPL                   : $" + format(spend / leads, ",.2f"))
    print("")

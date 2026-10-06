# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-action-type-audit.py — run from the repo root (README "More example analyses")
# What: prints every action_type Meta returns for a date range on your ad account, with
#       its count, largest first.
# Why:  Insights reports one conversion under several action_type names. A script that
#       adds 'lead', 'offsite_conversion.fb_pixel_lead' and 'onsite_conversion.lead_grouped'
#       together counts the same leads two or three times and halves your CPL on paper.
#       Run this once per account, see which names carry identical counts, pick ONE per
#       event, and write it down.
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-action-type-audit.py SINCE UNTIL
#         python examples/meta-action-type-audit.py 2026-03-01 2026-03-31

import os, sys, json, urllib.parse, urllib.request, urllib.error

ACT = "act_REPLACE_WITH_AD_ACCOUNT_ID"   # keep the act_ prefix (README Step 5g)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)

if len(sys.argv) < 3:
    sys.exit("usage: python examples/meta-action-type-audit.py SINCE UNTIL   (dates as YYYY-MM-DD)")
SINCE, UNTIL = sys.argv[1], sys.argv[2]

if "REPLACE_WITH" in ACT:
    sys.exit("set ACT at the top of this file to your ad account id")

tp = os.path.join(os.path.expanduser("~"), ".meta-ads", "token")
if not os.path.exists(tp):
    sys.exit("token file not found: %s" % tp)
TOKEN = open(tp, encoding="utf-8-sig").read().strip().strip('"').strip("'")
if not TOKEN:
    sys.exit("token file is empty")
print("token loaded (%d chars) — not printed, not stored\n" % len(TOKEN))

p = {"fields": "spend,actions", "time_range": json.dumps({"since": SINCE, "until": UNTIL}),
     "level": "account", "limit": 100, "access_token": TOKEN}
u = "%s/%s/insights?%s" % (API, ACT, urllib.parse.urlencode(p))
try:
    with urllib.request.urlopen(u, timeout=120) as r:
        data = json.load(r).get("data", [])
except urllib.error.HTTPError as e:
    sys.exit(e.read().decode("utf-8", "replace")[:400])
if not data:
    sys.exit("no data returned for %s to %s" % (SINCE, UNTIL))
d = data[0]
print("spend $%s\n" % format(float(d["spend"]), ",.0f"))
for a in sorted(d.get("actions", []), key=lambda x: -float(x.get("value") or 0)):
    print("  %-56s %12s" % (a["action_type"], format(int(float(a["value"])), ",")))

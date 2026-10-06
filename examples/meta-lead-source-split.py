# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-lead-source-split.py — run from the repo root (README "More example analyses")
# What: month by month, splits Meta's "leads" into website pixel leads and on-Meta
#       Instant Form leads, with the share that came from Instant Forms.
# Why:  'lead' counts both kinds; 'offsite_conversion.fb_pixel_lead' counts only leads
#       that reached your website. When a month's CPL looks unusually cheap, check here
#       first: Instant Forms are frictionless, so they produce cheap leads that often
#       don't show up or buy. A CPL target set from Instant Form months can't be met
#       by website leads. (In months with no Instant Forms the two counts are equal,
#       which is why summing them double counts.)
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-lead-source-split.py SINCE UNTIL
#         python examples/meta-lead-source-split.py 2026-01-01 2026-06-30

import os, sys, json, urllib.parse, urllib.request, urllib.error

ACT = "act_REPLACE_WITH_AD_ACCOUNT_ID"   # keep the act_ prefix (README Step 5g)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)

if len(sys.argv) < 3:
    sys.exit("usage: python examples/meta-lead-source-split.py SINCE UNTIL   (dates as YYYY-MM-DD)")
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
     "time_increment": "monthly", "level": "account", "limit": 500, "access_token": TOKEN}
try:
    with urllib.request.urlopen("%s/%s/insights?%s" % (API, ACT, urllib.parse.urlencode(p)), timeout=120) as r:
        rows = json.load(r)["data"]
except urllib.error.HTTPError as e:
    sys.exit(e.read().decode("utf-8", "replace")[:400])


def act(row, t):
    for a in (row.get("actions") or []):
        if a.get("action_type") == t: return int(float(a.get("value") or 0))
    return 0


print("%-9s %11s %10s %10s %10s %9s %9s" % ("month","spend","all leads","pixel","instant","% instant","CPL"))
print("-"*74)
for row in rows:
    s = float(row["spend"]); tot = act(row,"lead"); px = act(row,"offsite_conversion.fb_pixel_lead")
    inst = tot - px
    print("%-9s %11s %10s %10s %10s %9s %9s" % (
        row["date_start"][:7], "$%s"%format(s,",.0f"), format(tot,","), format(px,","),
        format(inst,","), "%.0f%%"%(100.0*inst/tot) if tot else "-", "$%.2f"%(s/tot) if tot else "-"))

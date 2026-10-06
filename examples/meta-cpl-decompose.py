# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-cpl-decompose.py — run from the repo root (README "More example analyses")
# What: splits monthly cost per lead into its two drivers, CPM (what the auction charges
#       for 1,000 impressions) and lead-per-impression rate (how well the ads and funnel
#       turn impressions into leads), then says how much each moved between two months.
# Why:  "CPL went up" has two very different fixes. If CPM moved, it's the auction
#       (audience, season, competition). If lead-per-impression moved, it's the creative,
#       the landing page or the tracking. CPL = CPM / (1000 x lead-per-impression), so
#       the two ratios multiply out to the CPL change exactly.
#       Leads use the 'lead' action type only (see examples/meta-action-type-audit.py).
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-cpl-decompose.py SINCE UNTIL [MONTH_A MONTH_B]
#         python examples/meta-cpl-decompose.py 2026-01-01 2026-06-30 2026-01 2026-06
#         (no months = compare the first month in the range with the last)

import os, sys, json, urllib.parse, urllib.request, urllib.error

ACT = "act_REPLACE_WITH_AD_ACCOUNT_ID"   # keep the act_ prefix (README Step 5g)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)

if len(sys.argv) < 3:
    sys.exit("usage: python examples/meta-cpl-decompose.py SINCE UNTIL [MONTH_A MONTH_B]")
SINCE, UNTIL = sys.argv[1], sys.argv[2]
MONTH_A = sys.argv[3] if len(sys.argv) > 3 else None
MONTH_B = sys.argv[4] if len(sys.argv) > 4 else None

if "REPLACE_WITH" in ACT:
    sys.exit("set ACT at the top of this file to your ad account id")

tp = os.path.join(os.path.expanduser("~"), ".meta-ads", "token")
if not os.path.exists(tp):
    sys.exit("token file not found: %s" % tp)
TOKEN = open(tp, encoding="utf-8-sig").read().strip().strip('"').strip("'")
if not TOKEN:
    sys.exit("token file is empty")
print("token loaded (%d chars) — not printed, not stored\n" % len(TOKEN))

p = {"fields": "spend,impressions,cpm,clicks,actions",
     "time_range": json.dumps({"since": SINCE, "until": UNTIL}),
     "time_increment": "monthly", "level": "account", "limit": 500, "access_token": TOKEN}
u = "%s/%s/insights?%s" % (API, ACT, urllib.parse.urlencode(p))
try:
    with urllib.request.urlopen(u, timeout=120) as r:
        rows = json.load(r).get("data", [])
except urllib.error.HTTPError as e:
    sys.exit(e.read().decode("utf-8", "replace")[:400])
if not rows:
    sys.exit("no data returned for %s to %s" % (SINCE, UNTIL))


def act(row, t):
    for a in (row.get("actions") or []):
        if a.get("action_type") == t:
            return int(float(a.get("value") or 0))
    return 0


print("%-9s %11s %12s %8s %10s %9s %8s %8s" %
      ("month", "spend", "impressions", "CPM", "LPV", "leads", "lead/imp", "CPL"))
print("-" * 82)
for row in rows:
    s = float(row["spend"]); imp = int(row["impressions"])
    l = act(row, "lead"); lpv = act(row, "landing_page_view")
    rate = l / imp if imp else 0
    print("%-9s %11s %12s %8s %10s %9s %8s %8s" % (
        row["date_start"][:7], "$%s" % format(s, ",.0f"), format(imp, ","),
        "$%.0f" % float(row["cpm"]), format(lpv, ","), format(l, ","),
        "%.3f%%" % (rate * 100), "$%.2f" % (s / l) if l else "-"))
print("-" * 82)

ma = MONTH_A or rows[0]["date_start"][:7]
mb = MONTH_B or rows[-1]["date_start"][:7]
a_rows = [r for r in rows if r["date_start"][:7] == ma]
b_rows = [r for r in rows if r["date_start"][:7] == mb]
if not a_rows or not b_rows:
    sys.exit("month %s or %s is not in the range" % (ma, mb))
a_, b_ = a_rows[0], b_rows[0]
if not act(a_, "lead") or not act(b_, "lead"):
    sys.exit("one of the two months has no leads; nothing to decompose")
ar = act(a_, "lead") / int(a_["impressions"]); br = act(b_, "lead") / int(b_["impressions"])
ac, bc = float(a_["cpm"]), float(b_["cpm"])
print("%s -> %s:  CPM x%.2f   lead-per-impression x%.2f   => CPL x%.2f"
      % (ma, mb, bc / ac, br / ar, (bc / ac) / (br / ar)))

# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-purchase-split-by-custom-conversion.py — run from the repo root (README "More example analyses")
# What: per campaign per day, splits Meta-attributed purchases into two custom
#       conversions (e.g. your main product vs a low-price add-on), alongside generic
#       'purchase'. Answers: what is purchase spend actually buying?
# Why:  one Purchase event usually covers every product you sell. A campaign optimized
#       to generic Purchase is told a cheap add-on and your main product are the same
#       win, and Meta will find more of whichever is cheapest. Custom conversions that
#       filter Purchase by product (e.g. content_name contains "<product>") appear in
#       Insights as offsite_conversion.custom.<id>, so the split is readable per campaign.
#       Get the ids from examples/meta-list-custom-conversions.py.
#       Custom conversions only count from the day they were created; earlier days read 0.
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-purchase-split-by-custom-conversion.py DAY [DAY ...]
#         python examples/meta-purchase-split-by-custom-conversion.py 2026-03-10 2026-03-11

import os, sys, json, datetime, urllib.parse, urllib.request, urllib.error

ACT = "act_REPLACE_WITH_AD_ACCOUNT_ID"   # keep the act_ prefix (README Step 5g)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)

# The two custom conversions to split by, and the column label for each.
CC_A = "offsite_conversion.custom.REPLACE_WITH_CUSTOM_CONVERSION_ID_A"
CC_A_LABEL = "main"
CC_B = "offsite_conversion.custom.REPLACE_WITH_CUSTOM_CONVERSION_ID_B"
CC_B_LABEL = "add-on"

if len(sys.argv) < 2:
    sys.exit("usage: python examples/meta-purchase-split-by-custom-conversion.py DAY [DAY ...]   (YYYY-MM-DD)")
DAYS = sys.argv[1:]
TODAY = datetime.date.today().isoformat()   # your computer's date; Insights uses the account time zone

if "REPLACE_WITH" in ACT:
    sys.exit("set ACT at the top of this file to your ad account id")
if "REPLACE_WITH" in CC_A or "REPLACE_WITH" in CC_B:
    sys.exit("set CC_A and CC_B at the top of this file to your custom conversion ids")

tp = os.path.join(os.path.expanduser("~"), ".meta-ads", "token")
if not os.path.exists(tp):
    sys.exit("token file not found: %s" % tp)
TOKEN = open(tp, encoding="utf-8-sig").read().strip().strip('"').strip("'")
if not TOKEN:
    sys.exit("token file is empty")
print("token loaded (%d chars) — not printed, not stored\n" % len(TOKEN))


def pull(day):
    p = {
        "time_range": json.dumps({"since": day, "until": day}),
        "fields": "campaign_name,spend,actions",
        "level": "campaign",
        "limit": 300,
        "access_token": TOKEN,
    }
    url = API + "/" + ACT + "/insights?" + urllib.parse.urlencode(p)
    out = []
    while url:
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                j = json.load(r)
        except urllib.error.HTTPError as e:
            sys.exit(e.read().decode("utf-8", "replace")[:400])
        out.extend(j.get("data", []))
        url = j.get("paging", {}).get("next")
    return out


def val(row, at):
    for a in row.get("actions", []):
        if a.get("action_type") == at:
            return int(float(a.get("value", 0)))
    return 0


for day in DAYS:
    print("=" * 78)
    print(day + ("  (running)" if day == TODAY else "  (closed)"))
    print("=" * 78)
    rows = pull(day)
    ta = tb = tp_ = 0
    for r in sorted(rows, key=lambda x: -float(x.get("spend", 0))):
        spend = float(r.get("spend", 0))
        if spend == 0:
            continue
        pur = val(r, "purchase")
        a = val(r, CC_A)
        b = val(r, CC_B)
        ta += a
        tb += b
        tp_ += pur
        print("  %-58s $%9.2f  purch %3d  %s %3d  %s %3d"
              % (r["campaign_name"][:58], spend, pur, CC_A_LABEL, a, CC_B_LABEL, b))
    print("  %-58s %11s  purch %3d  %s %3d  %s %3d"
          % ("TOTAL", "", tp_, CC_A_LABEL, ta, CC_B_LABEL, tb))
    print()

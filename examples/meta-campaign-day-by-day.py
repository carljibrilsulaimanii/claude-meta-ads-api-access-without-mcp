# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-campaign-day-by-day.py — run from the repo root (README "More example analyses")
# What: for the days you list, the account total per day, then every campaign's spend,
#       impressions, CPM, leads, CPL and purchases day by day, biggest spender (on the
#       last day listed) first.
# Why:  after a restructure (budgets moved to the campaign, ad sets switched on or off,
#       a campaign relaunched), the question is whether any of it worked. Putting the
#       days before and after side by side per campaign answers that without opening
#       Ads Manager one campaign at a time.
#       Leads use 'lead' only, purchases 'purchase' only. The other lead and purchase
#       action types can return identical counts; summing them doubles the figure.
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-campaign-day-by-day.py DAY [DAY ...]
#         python examples/meta-campaign-day-by-day.py 2026-03-10 2026-03-11 2026-03-12

import os, sys, json, urllib.parse, urllib.request, urllib.error

ACT = "act_REPLACE_WITH_AD_ACCOUNT_ID"   # keep the act_ prefix (README Step 5g)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)

if len(sys.argv) < 2:
    sys.exit("usage: python examples/meta-campaign-day-by-day.py DAY [DAY ...]   (dates as YYYY-MM-DD)")
DAYS = sys.argv[1:]

if "REPLACE_WITH" in ACT:
    sys.exit("set ACT at the top of this file to your ad account id")

tp = os.path.join(os.path.expanduser("~"), ".meta-ads", "token")
if not os.path.exists(tp):
    sys.exit("token file not found: %s" % tp)
TOKEN = open(tp, encoding="utf-8-sig").read().strip().strip('"').strip("'")
if not TOKEN:
    sys.exit("token file is empty")
print("token loaded (%d chars) — not printed, not stored\n" % len(TOKEN))


def pull(day, level):
    p = {
        "time_range": json.dumps({"since": day, "until": day}),
        "fields": ("campaign_name," if level == "campaign" else "") + "spend,impressions,cpm,ctr,actions",
        "level": level,
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
            print("  API error: " + e.read().decode("utf-8", "replace")[:200], file=sys.stderr)
            return []
        out.extend(j.get("data", []))
        url = j.get("paging", {}).get("next")
    return out


def counts(row):
    ld = pu = 0
    for a in row.get("actions", []):
        if a.get("action_type") == "lead":
            ld = int(float(a.get("value", 0)))
        elif a.get("action_type") == "purchase":
            pu = int(float(a.get("value", 0)))
    return ld, pu


print("=" * 78)
print("ACCOUNT TOTAL")
print("=" * 78)
print("")
print("  day             spend      impr      CPM   leads      CPL   purch")
print("  " + "-" * 64)
for d in DAYS:
    rows = pull(d, "account")
    if not rows:
        print("  " + d.ljust(14) + "  no data")
        continue
    r = rows[0]
    s = float(r.get("spend", 0))
    im = int(r.get("impressions", 0))
    ld, pu = counts(r)
    cpl = ("$" + format(s / ld, ",.2f")) if ld else "-"
    print("  " + d.ljust(14)
          + ("$" + format(s, ",.2f")).rjust(11)
          + format(im, ",").rjust(10)
          + ("$" + format(float(r.get("cpm", 0) or 0), ",.2f")).rjust(9)
          + format(ld, ",").rjust(8)
          + cpl.rjust(9)
          + format(pu, ",").rjust(8))

print("")
print("=" * 78)
print("BY CAMPAIGN - " + ", ".join(DAYS))
print("=" * 78)

snap = {}
for d in DAYS:
    for c in pull(d, "campaign"):
        s = float(c.get("spend", 0))
        if s <= 0:
            continue
        ld, pu = counts(c)
        snap.setdefault(c.get("campaign_name", ""), {})[d] = (
            s, int(c.get("impressions", 0)), float(c.get("cpm", 0) or 0), ld, pu)

last = DAYS[-1]
for name in sorted(snap, key=lambda n: -snap[n].get(last, (0,))[0]):
    print("")
    print("  " + name[:70])
    print("      day            spend      impr      CPM   leads      CPL   purch")
    for d in DAYS:
        if d not in snap[name]:
            continue
        s, im, cpm, ld, pu = snap[name][d]
        cpl = ("$" + format(s / ld, ",.2f")) if ld else "-"
        print("      " + d.ljust(12)
              + ("$" + format(s, ",.2f")).rjust(10)
              + format(im, ",").rjust(10)
              + ("$" + format(cpm, ",.2f")).rjust(9)
              + format(ld, ",").rjust(8)
              + cpl.rjust(9)
              + format(pu, ",").rjust(8))
print("")

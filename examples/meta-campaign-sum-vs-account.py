# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-campaign-sum-vs-account.py — run from the repo root (README "More example analyses")
# What: one date window as a SINGLE aggregate, per campaign (spend, CPM, leads, CPL,
#       purchases), then the account total pulled independently, and whether the
#       campaign rows add up to it.
# Why:  campaign figures going into a message or an invoice are often made by adding
#       daily rows by hand. This asks the API for the window directly, so the arithmetic
#       is Meta's, and the reconcile line proves no campaign is missing. Use closed days
#       only: a day that is still running moves between pulls.
#       Leads use 'lead' only, purchases 'purchase' only.
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-campaign-sum-vs-account.py SINCE UNTIL
#         python examples/meta-campaign-sum-vs-account.py 2026-03-01 2026-03-31

import os, sys, json, urllib.parse, urllib.request, urllib.error

ACT = "act_REPLACE_WITH_AD_ACCOUNT_ID"   # keep the act_ prefix (README Step 5g)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)

if len(sys.argv) < 3:
    sys.exit("usage: python examples/meta-campaign-sum-vs-account.py SINCE UNTIL   (dates as YYYY-MM-DD)")
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


def pull(level):
    p = {
        "time_range": json.dumps({"since": SINCE, "until": UNTIL}),
        "fields": ("campaign_name," if level == "campaign" else "") + "spend,impressions,cpm,actions",
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
            sys.exit(e.read().decode("utf-8", "replace")[:300])
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


print("=" * 76)
print("META AGGREGATE  " + SINCE + "  to  " + UNTIL)
print("=" * 76)
print("")

rows = []
for c in pull("campaign"):
    s = float(c.get("spend", 0))
    if s <= 0:
        continue
    ld, pu = counts(c)
    rows.append((s, c.get("campaign_name", ""), int(c.get("impressions", 0)),
                 float(c.get("cpm", 0) or 0), ld, pu))
rows.sort(reverse=True)

print("  " + "campaign".ljust(50) + "spend".rjust(12) + "CPM".rjust(9)
      + "leads".rjust(8) + "CPL".rjust(9) + "purch".rjust(7))
print("  " + "-" * 95)
tot = 0.0
for s, name, im, cpm, ld, pu in rows:
    tot += s
    cpl = ("$" + format(s / ld, ",.2f")) if ld else "-"
    print("  " + name[:50].ljust(50)
          + ("$" + format(s, ",.2f")).rjust(12)
          + ("$" + format(cpm, ",.2f")).rjust(9)
          + format(ld, ",").rjust(8) + cpl.rjust(9) + format(pu, ",").rjust(7))
print("  " + "-" * 95)
print("  " + "SUM OF CAMPAIGNS".ljust(50) + ("$" + format(tot, ",.2f")).rjust(12))

acct = pull("account")
if not acct:
    sys.exit("no account-level row returned for this window")
a = acct[0]
asp = float(a.get("spend", 0))
ald, apu = counts(a)
print("  " + "ACCOUNT TOTAL (independent)".ljust(50) + ("$" + format(asp, ",.2f")).rjust(12)
      + ("$" + format(float(a.get("cpm", 0) or 0), ",.2f")).rjust(9)
      + format(ald, ",").rjust(8)
      + ("$" + format(asp / ald, ",.2f") if ald else "-").rjust(9)
      + format(apu, ",").rjust(7))
print("")
print("  reconciles : " + ("YES" if abs(tot - asp) < 1 else "NO - diff $" + format(tot - asp, ",.2f")))
print("")

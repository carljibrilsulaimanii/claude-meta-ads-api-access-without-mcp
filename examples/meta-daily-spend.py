# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-daily-spend.py — run from the repo root (README "More example analyses")
# What: daily spend, impressions, CPM, leads and CPL for a date range at account level,
#       with a running total that keeps CLOSED days apart from today, which is still
#       spending and therefore provisional.
# Why:  a month-to-date total built from a pull taken before a day closed carries a
#       too-small figure for that day, and every number built on it inherits the error.
#       Re-pull the whole range and never let a running day into a "closed" total.
#       Leads use the 'lead' action type ONLY. 'lead', 'offsite_conversion.fb_pixel_lead',
#       'onsite_web_lead' and 'offsite_lead_add_20_s_calls' can all return the same count
#       (one event reported several ways); summing them doubles the figure.
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-daily-spend.py [SINCE] [UNTIL]
#         python examples/meta-daily-spend.py 2026-03-01 2026-03-15
#         (no dates = first of this month to today)

import os, sys, json, datetime, urllib.parse, urllib.request, urllib.error

ACT = "act_REPLACE_WITH_AD_ACCOUNT_ID"   # keep the act_ prefix (README Step 5g)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)

# "today" is your computer's date. Insights days are in the AD ACCOUNT's time zone, so
# if the two differ, the row flagged as running may be off by one around midnight.
TODAY = datetime.date.today().isoformat()
SINCE = sys.argv[1] if len(sys.argv) > 1 else TODAY[:8] + "01"
UNTIL = sys.argv[2] if len(sys.argv) > 2 else TODAY

if "REPLACE_WITH" in ACT:
    sys.exit("set ACT at the top of this file to your ad account id")

tp = os.path.join(os.path.expanduser("~"), ".meta-ads", "token")
if not os.path.exists(tp):
    sys.exit("token file not found: %s" % tp)
TOKEN = open(tp, encoding="utf-8-sig").read().strip().strip('"').strip("'")
if not TOKEN:
    sys.exit("token file is empty")
print("token loaded (%d chars) — not printed, not stored\n" % len(TOKEN))

params = {
    "time_range": json.dumps({"since": SINCE, "until": UNTIL}),
    "fields": "spend,impressions,cpm,actions",
    "level": "account",
    "time_increment": 1,
    "limit": 100,
    "access_token": TOKEN,
}

url = API + "/" + ACT + "/insights?" + urllib.parse.urlencode(params)
rows = []
while url:
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            j = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(e.read().decode("utf-8", "replace")[:400])
    rows.extend(j.get("data", []))
    url = j.get("paging", {}).get("next")

rows.sort(key=lambda r: r.get("date_start", ""))

print("=" * 72)
print("META DAILY  " + SINCE + " to " + UNTIL + ", pulled " + TODAY)
print("=" * 72)
print("")
print("  date          spend      impr      CPM    leads       CPL")
print("  " + "-" * 60)

closed_spend = 0.0
closed_leads = 0
today_spend = 0.0
today_leads = 0

for r in rows:
    d = r.get("date_start", "")
    s = float(r.get("spend", 0))
    im = int(r.get("impressions", 0))
    cpm = float(r.get("cpm", 0) or 0)
    ld = 0
    for a in r.get("actions", []):
        if a.get("action_type") == "lead":
            ld = int(float(a.get("value", 0)))

    if d == TODAY:
        today_spend, today_leads = s, ld
        tag = "  <- running"
    else:
        closed_spend += s
        closed_leads += ld
        tag = ""

    cpl = ("$" + format(s / ld, ",.2f")) if ld else "-"
    print("  " + d + ("$" + format(s, ",.2f")).rjust(12)
          + format(im, ",").rjust(10)
          + ("$" + format(cpm, ",.2f")).rjust(9)
          + format(ld, ",").rjust(8)
          + cpl.rjust(10) + tag)

print("  " + "-" * 60)
print("")
print("CLOSED DAYS")
print("  spend        : $" + format(closed_spend, ",.2f"))
print("  leads        : " + format(closed_leads, ","))
if closed_leads:
    print("  CPL          : $" + format(closed_spend / closed_leads, ",.2f"))
print("")
print("TODAY (" + TODAY + ", still running)")
print("  spend        : $" + format(today_spend, ",.2f"))
print("  leads        : " + format(today_leads, ","))
print("")
print("RANGE TOTAL   : $" + format(closed_spend + today_spend, ",.2f"))
print("")

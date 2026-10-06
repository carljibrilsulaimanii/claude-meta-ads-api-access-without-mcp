# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-pixel-event-hourly.py — run from the repo root (README "More example analyses")
# What: prints the pixel's hourly arrival buckets for ONE event over the last N days,
#       as the /stats edge returns them, with a total.
# Why:  shows exactly which hour an event stopped (or started) arriving, which separates
#       a real outage (e.g. a server-side sender failing mid-evening) from a reporting lag.
#       Don't use the pixel's last_fired_time for this: it can read hours stale while
#       events are still arriving.
#       /stats counts raw event arrivals. Ads Manager counts conversions it attributes to
#       ads (click and view windows), so the two numbers differ; compare shapes over
#       time, not absolute values.
#       Needs ads_management + business_management on the token (README Step 9a).
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-pixel-event-hourly.py [EVENT] [DAYS]
#         python examples/meta-pixel-event-hourly.py Lead 3

import os, sys, json, time, urllib.parse, urllib.request, urllib.error

PIXEL = "REPLACE_WITH_PIXEL_ID"   # the dataset / pixel id (README Step 9b)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)
EVENT = sys.argv[1] if len(sys.argv) > 1 else "Lead"
DAYS = int(sys.argv[2]) if len(sys.argv) > 2 else 3

if "REPLACE_WITH" in PIXEL:
    sys.exit("set PIXEL at the top of this file to your pixel / dataset id")

tp = os.path.join(os.path.expanduser("~"), ".meta-ads", "token")
if not os.path.exists(tp):
    sys.exit("token file not found: %s" % tp)
TOKEN = open(tp, encoding="utf-8-sig").read().strip().strip('"').strip("'")
if not TOKEN:
    sys.exit("token file is empty")
print("token loaded (%d chars) — not printed, not stored\n" % len(TOKEN))

end = int(time.time())
start = end - DAYS * 86400
p = {
    "aggregation": "event",
    "event": EVENT,
    "start_time": start,
    "end_time": end,
    "access_token": TOKEN,
}
url = API + "/" + PIXEL + "/stats?" + urllib.parse.urlencode(p)
rows = []
while url:
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            j = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(e.read().decode("utf-8", "replace")[:400])
    rows.extend(j.get("data", []))
    url = j.get("paging", {}).get("next")

# stats rows come back as {start_time, data:[{value,count}]} hourly buckets.
# start_time carries its own UTC offset; convert before grouping by day.
print("%s buckets, event=%s, last %d days (times as Meta returns them)" % (len(rows), EVENT, DAYS))
total = 0
for row in rows:
    ts = row.get("start_time")
    cnt = sum(int(d.get("count", 0)) for d in row.get("data", []))
    total += cnt
    print("  %s  %6d" % (ts, cnt))
print("  TOTAL %d" % total)

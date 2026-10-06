# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman · 2026-09-22
# Location: scripts/meta-pixel-trace.py — run from the repo root (README Step 9)
# What: traces the source of Meta pixel events for one dataset, so a stray sender
#       (browser vs Conversions API vs Event Setup Tool rule) can be identified by page.
# Why:  when the Ads MCP isn't enabled on the account, pixel diagnostics have to come
#       from the Graph API directly. The token is read from ~/.meta-ads/token, held in
#       memory, and never printed or written anywhere. Needs ads_management +
#       business_management on the token and a Manage role on the dataset.
#
# Usage:  python scripts/meta-pixel-trace.py [EVENT] [DAYS]
#         python scripts/meta-pixel-trace.py Purchase 7

import os, sys, json, time, urllib.parse, urllib.request, urllib.error

PIXEL = "REPLACE_WITH_PIXEL_ID"   # the dataset / pixel id (README Step 9)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)
EVENT = sys.argv[1] if len(sys.argv) > 1 else "Purchase"
DAYS = int(sys.argv[2]) if len(sys.argv) > 2 else 7

if "REPLACE_WITH" in PIXEL:
    sys.exit("set PIXEL at the top of this file to your pixel / dataset id")

tp = os.path.join(os.path.expanduser("~"), ".meta-ads", "token")
if not os.path.exists(tp):
    sys.exit("token file not found: %s" % tp)
TOKEN = open(tp, encoding="utf-8-sig").read().strip().strip('"').strip("'")
if not TOKEN:
    sys.exit("token file is empty")
print("token loaded (%d chars) \u2014 not printed, not stored\n" % len(TOKEN))


def get(path, **params):
    params["access_token"] = TOKEN
    url = "%s/%s?%s" % (API, path, urllib.parse.urlencode(params))
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode("utf-8", "replace"))["error"]
            return {"__error__": "%s (code %s subcode %s)" % (
                err.get("message"), err.get("code"), err.get("error_subcode"))}
        except Exception:
            return {"__error__": "HTTP %s" % e.code}
    except Exception as e:
        return {"__error__": str(e)}


now = int(time.time())
start = now - DAYS * 86400

print("=" * 78)
print("PIXEL %s   event=%s   last %d days" % (PIXEL, EVENT, DAYS))
print("=" * 78)

info = get(PIXEL, fields="name,last_fired_time,owner_business{name}")
print(json.dumps(info, indent=1)[:500] + "\n")

# event_detection_method is the one that exposes Event Setup Tool rules
AGGS = ["event", "event_source", "event_detection_method", "host", "url",
        "pixel_fire", "device_type"]

for agg in AGGS:
    print("-" * 78)
    print("aggregation = %s" % agg)
    r = get("%s/stats" % PIXEL, aggregation=agg, start_time=start, end_time=now, event=EVENT)
    if "__error__" in r:
        # some aggregations reject the event filter; retry unfiltered
        r = get("%s/stats" % PIXEL, aggregation=agg, start_time=start, end_time=now)
        if "__error__" in r:
            print("  ERROR: " + r["__error__"])
            continue
        print("  (unfiltered \u2014 this aggregation rejects an event filter)")
    rows = {}
    for bucket in r.get("data", []):
        for v in bucket.get("data", []):
            k = str(v.get("value"))
            rows[k] = rows.get(k, 0) + (v.get("count") or 0)
    if not rows:
        print("  (no rows)")
        continue
    total = sum(rows.values()) or 1
    for k, c in sorted(rows.items(), key=lambda kv: -kv[1])[:25]:
        print("  %9d  %5.1f%%  %s" % (c, 100.0 * c / total, k[:80]))
print("-" * 78)

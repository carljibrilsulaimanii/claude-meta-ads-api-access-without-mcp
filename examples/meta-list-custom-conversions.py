# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-list-custom-conversions.py — run from the repo root (README "More example analyses")
# What: lists every custom conversion on the ad account: id, name, event type, the rule
#       it fires on, creation and last-fired time, default value, and whether it is
#       archived.
# Why:  before a plan or a message says "assign the <name> conversion to the new ad sets",
#       confirm it exists, is the right rule, and is still live. Two traps this catches:
#       an ARCHIVED conversion with a similar name (the one people find first), and a
#       custom conversion that never fires, which can't be used as an optimization event
#       whatever the list says. You also need the id: in Insights a custom conversion
#       shows up as action_type offsite_conversion.custom.<id>
#       (see examples/meta-purchase-split-by-custom-conversion.py).
#       Custom conversions hang off the ad account, so the Ads MCP can't list them on an
#       account it doesn't serve. Custom conversions can't be created over the API;
#       make them by hand in Events Manager.
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-list-custom-conversions.py

import os, sys, json, urllib.parse, urllib.request, urllib.error

ACT = "act_REPLACE_WITH_AD_ACCOUNT_ID"   # keep the act_ prefix (README Step 5g)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)

if "REPLACE_WITH" in ACT:
    sys.exit("set ACT at the top of this file to your ad account id")

tp = os.path.join(os.path.expanduser("~"), ".meta-ads", "token")
if not os.path.exists(tp):
    sys.exit("token file not found: %s" % tp)
TOKEN = open(tp, encoding="utf-8-sig").read().strip().strip('"').strip("'")
if not TOKEN:
    sys.exit("token file is empty")
print("token loaded (%d chars) — not printed, not stored\n" % len(TOKEN))

FIELDS = ("id,name,description,custom_event_type,rule,is_archived,"
          "creation_time,last_fired_time,default_conversion_value,"
          "data_sources,aggregation_rule,event_source_type")


def pull(path):
    p = {"fields": FIELDS, "limit": 200, "access_token": TOKEN}
    url = API + "/" + path + "/customconversions?" + urllib.parse.urlencode(p)
    out = []
    while url:
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                j = json.load(r)
        except urllib.error.HTTPError as e:
            return {"__error": e.read().decode("utf-8", "replace")[:300]}
        out.extend(j.get("data", []))
        url = j.get("paging", {}).get("next")
    return out


# The ad account is the edge that works. (A /{pixel_id}/customconversions edge was
# tried in the original build and does not exist.)
for label, path in [("AD ACCOUNT " + ACT, ACT)]:
    print("=" * 78)
    print(label)
    print("=" * 78)
    rows = pull(path)

    if isinstance(rows, dict):
        print("  API error: " + rows["__error"])
        print("")
        continue
    if not rows:
        print("  none returned")
        print("")
        continue

    for c in rows:
        arch = "  [ARCHIVED]" if c.get("is_archived") else ""
        print("")
        print("  " + str(c.get("name")) + arch)
        print("      id           : " + str(c.get("id")))
        print("      event type   : " + str(c.get("custom_event_type")))
        print("      created      : " + str(c.get("creation_time")))
        print("      last fired   : " + str(c.get("last_fired_time")))
        if c.get("default_conversion_value") is not None:
            print("      default value: " + str(c.get("default_conversion_value")))
        rule = c.get("rule")
        if rule:
            r = rule if isinstance(rule, str) else json.dumps(rule)
            print("      rule         : " + r[:400])
    print("")

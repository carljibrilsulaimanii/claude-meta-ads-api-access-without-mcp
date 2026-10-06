# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-live-structure.py — run from the repo root (README "More example analyses")
# What: every ACTIVE campaign and its active ad sets right now: objective, campaign
#       budget (CBO) or ad set budgets (ABO), bid strategy, and for each ad set the
#       conversion event it optimizes to, read from promoted_object: a single event, a
#       LEAD -> PURCHASE sequence, or a custom conversion. Ends with a count of
#       sequenced vs single-event ad sets.
# Why:  budgets and structure change daily, and a plan or report written from memory
#       repeats yesterday's numbers. It is also the way to check a "done, the ad sets now
#       optimize to <custom conversion>" claim at field level:
#       - optimization_goal reads OFFSITE_CONVERSIONS whether or not a sequence exists,
#         so it can't tell you; promoted_object can (multi_event_product).
#       - a custom conversion carries custom_conversion_id ALONGSIDE the underlying
#         custom_event_type (e.g. PURCHASE). Reading the event type first hides the custom
#         conversion and gives a false "still on generic Purchase". The id wins.
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-live-structure.py

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


def get(path, fields, extra=None):
    p = {"fields": fields, "limit": 300, "access_token": TOKEN}
    if extra:
        p.update(extra)
    url = API + "/" + path + "?" + urllib.parse.urlencode(p)
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


def money(v):
    # budgets come back in the account currency's minor unit (cents)
    try:
        return "$" + format(int(v) / 100.0, ",.0f")
    except Exception:
        return "-"


camps = get(ACT + "/campaigns",
            "name,effective_status,objective,daily_budget,lifetime_budget,bid_strategy")
adsets = get(ACT + "/adsets",
             "name,effective_status,daily_budget,optimization_goal,promoted_object,"
             "campaign_id,end_time")

live_c = {c["id"]: c for c in camps if c.get("effective_status") == "ACTIVE"}

print("=" * 80)
print("LIVE CAMPAIGNS AND AD SETS")
print("=" * 80)

for cid, c in sorted(live_c.items(), key=lambda kv: kv[1].get("name", "")):
    cb = c.get("daily_budget")
    print("")
    print("  " + c.get("name", "")[:74])
    print("      objective   : " + str(c.get("objective")))
    print("      budget      : " + (money(cb) + "/day  CAMPAIGN (CBO)" if cb else "ad set budgets (ABO)"))
    print("      bid strategy: " + str(c.get("bid_strategy")))

    mine = [a for a in adsets if a.get("campaign_id") == cid]
    on = [a for a in mine if a.get("effective_status") == "ACTIVE"]
    print("      ad sets     : %d active of %d" % (len(on), len(mine)))

    for a in sorted(on, key=lambda x: -(int(x.get("daily_budget") or 0))):
        po = a.get("promoted_object") or {}
        seq = "SEQUENCE" if po.get("multi_event_product") else "single"
        # The custom conversion id wins over custom_event_type (see the header).
        if po.get("custom_conversion_id"):
            ev = "CUSTOM CONV " + po["custom_conversion_id"]
        else:
            ev = po.get("custom_event_type") or "?"
        if po.get("lead_ads_custom_event_type"):
            ev += " -> " + po["lead_ads_custom_event_type"]
        print("        - %-44s %8s  %-9s %s" % (
            a.get("name", "")[:44],
            money(a.get("daily_budget")) if a.get("daily_budget") else "campaign",
            seq, ev))

print("")
print("=" * 80)
print("ACTIVE AD SETS BY EVENT SETUP")
print("=" * 80)
seq_n = single_n = 0
for a in adsets:
    if a.get("effective_status") != "ACTIVE":
        continue
    po = a.get("promoted_object") or {}
    if po.get("multi_event_product"):
        seq_n += 1
    else:
        single_n += 1
print("  sequenced (LEAD -> PURCHASE) : %d" % seq_n)
print("  single event                 : %d" % single_n)
print("")

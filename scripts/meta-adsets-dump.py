# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman · 2026-09-22
# Location: scripts/meta-adsets-dump.py — run from the repo root (README Step 8)
# What: dumps every ad set on your ad account with budget, campaign, objective,
#       budget level (ABO vs CBO), optimization goal, targeting and schedule, to adsets-live.json.
# Why:  when the Meta Ads MCP connector isn't enabled on an account, ad set names, budgets
#       and audiences have to come from the Graph API rather than be guessed from screenshots.
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python scripts/meta-adsets-dump.py

import os, sys, json, urllib.parse, urllib.request, urllib.error

ACT = "act_REPLACE_WITH_AD_ACCOUNT_ID"   # keep the act_ prefix (README Step 5g)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)
OUT = os.path.join(os.getcwd(), "adsets-live.json")   # git-ignored: it holds your targeting

if "REPLACE_WITH" in ACT:
    sys.exit("set ACT at the top of this file to your ad account id")

tp = os.path.join(os.path.expanduser("~"), ".meta-ads", "token")
if not os.path.exists(tp):
    sys.exit("token file not found: %s" % tp)
TOKEN = open(tp, encoding="utf-8-sig").read().strip().strip('"').strip("'")
if not TOKEN:
    sys.exit("token file is empty")
print("token loaded (%d chars) \u2014 not printed, not stored" % len(TOKEN))

FIELDS = ("name,daily_budget,lifetime_budget,effective_status,status,optimization_goal,"
          "billing_event,bid_strategy,start_time,end_time,targeting,"
          "campaign{id,name,objective,buying_type,daily_budget,lifetime_budget,bid_strategy,"
          "special_ad_categories,effective_status}")

rows, url = [], "%s/%s/adsets?%s" % (API, ACT, urllib.parse.urlencode(
    {"fields": FIELDS, "limit": 200, "access_token": TOKEN}))

while url:
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            j = json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            err = json.loads(body)["error"]
            sys.exit("Graph API error: %s (code %s subcode %s)" % (
                err.get("message"), err.get("code"), err.get("error_subcode")))
        except SystemExit:
            raise
        except Exception:
            sys.exit("HTTP %s: %s" % (e.code, body[:300]))
    rows.extend(j.get("data", []))
    url = j.get("paging", {}).get("next")

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)

live = [r for r in rows if r.get("effective_status") == "ACTIVE"]
print("fetched %d ad sets (%d ACTIVE) -> %s" % (len(rows), len(live), os.path.basename(OUT)))

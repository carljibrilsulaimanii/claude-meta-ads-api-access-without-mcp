# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-campaign-mix-by-week.py — run from the repo root (README "More example analyses")
# What: a past (or current) season week by week: spend and purchases per campaign in a
#       grid, then each campaign's totals and the ad names grouped by the landing page
#       they send people to.
# Why:  before rebuilding a campaign for this season, look at how last season was
#       actually wired: which campaigns carried the money in which week, how the mix
#       shifted as the event approached, and whether a sales campaign was pointing at a
#       purchase page or at a free sign-up page. Taken from the account, not from memory.
#       Only the CLICK URL is used as the destination (link / website_url). The display
#       URL (link_caption, display_url) is text printed under the ad and changes nothing
#       about where the tap lands.
#       Leads use 'lead' only, purchases 'purchase' only.
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-campaign-mix-by-week.py SINCE UNTIL
#         python examples/meta-campaign-mix-by-week.py 2025-03-01 2025-05-31

import os, sys, json, urllib.parse, urllib.request, urllib.error
from collections import defaultdict

ACT = "act_REPLACE_WITH_AD_ACCOUNT_ID"   # keep the act_ prefix (README Step 5g)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)
MIN_SPEND = 500   # campaigns that spent less than this over the window are left out

if len(sys.argv) < 3:
    sys.exit("usage: python examples/meta-campaign-mix-by-week.py SINCE UNTIL   (dates as YYYY-MM-DD)")
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


def get(path, params):
    p = dict(params)
    p["access_token"] = TOKEN
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


def acts(r):
    ld = pu = 0
    for a in r.get("actions", []):
        if a.get("action_type") == "lead":
            ld = int(float(a.get("value", 0)))
        elif a.get("action_type") == "purchase":
            pu = int(float(a.get("value", 0)))
    return ld, pu


rows = get(ACT + "/insights", {
    "time_range": json.dumps({"since": SINCE, "until": UNTIL}),
    "fields": "campaign_id,campaign_name,spend,actions",
    "level": "campaign", "time_increment": 7, "limit": 400,
})

weeks = sorted({r["date_start"] for r in rows})
names = {}
grid = defaultdict(lambda: defaultdict(lambda: [0.0, 0, 0]))
for r in rows:
    cid = r["campaign_id"]
    names[cid] = r.get("campaign_name", "")
    ld, pu = acts(r)
    cell = grid[cid][r["date_start"]]
    cell[0] += float(r.get("spend", 0))
    cell[1] += ld
    cell[2] += pu

totals = {cid: sum(v[0] for v in wk.values()) for cid, wk in grid.items()}
order = [c for c in sorted(totals, key=lambda c: -totals[c]) if totals[c] >= MIN_SPEND]

print("=" * 100)
print("SEASON BY WEEK  (" + SINCE + " to " + UNTIL + ")   spend / purchases")
print("=" * 100)
print("")
hdr = "  " + "campaign".ljust(40) + "".join(w[5:].rjust(13) for w in weeks)
print(hdr)
print("  " + "-" * (40 + 13 * len(weeks)))
for cid in order:
    line = "  " + names[cid][:40].ljust(40)
    for w in weeks:
        sp, ld, pu = grid[cid].get(w, [0.0, 0, 0])
        line += ("-" if sp < 1 else "$%s/%s" % (format(int(sp / 1000), ","), pu)).rjust(13)
    print(line)
print("")
print("  cells are $thousands spend / purchases; column = the week's first day")

print("")
print("=" * 100)
print("FULL CAMPAIGN NAMES, TOTALS, AND AD DESTINATIONS")
print("=" * 100)

CRE = "creative{object_story_spec,asset_feed_spec,call_to_action_type,template_url}"


def urls_from(cr):
    """Click URLs only: link and call_to_action.value.link, asset feed website_url, template_url."""
    f = []
    oss = cr.get("object_story_spec") or {}
    for k in ("video_data", "link_data", "photo_data"):
        d = oss.get(k) or {}
        cta = d.get("call_to_action") or {}
        v = cta.get("value") or {}
        if d.get("link"):
            f.append((d["link"], cta.get("type")))
        if v.get("link"):
            f.append((v["link"], cta.get("type")))
    afs = cr.get("asset_feed_spec") or {}
    for lu in (afs.get("link_urls") or []):
        f.append((lu.get("website_url"),
                  (afs.get("call_to_action_types") or [None])[0]))
    if cr.get("template_url"):
        f.append((cr["template_url"], cr.get("call_to_action_type")))
    return [(u, c) for u, c in f if u]


for cid in order:
    tot = totals[cid]
    tl = sum(v[1] for v in grid[cid].values())
    tp_ = sum(v[2] for v in grid[cid].values())
    print("")
    print("  " + names[cid])
    print("      $%s   %s leads   %s purchases" % (
        format(int(tot), ","), format(tl, ","), format(tp_, ",")))
    try:
        ads = get(cid + "/ads", {"fields": "name," + CRE, "limit": 60})
    except SystemExit:
        print("      (ads unreadable)")
        continue
    byurl = defaultdict(list)
    for ad in ads:
        us = urls_from(ad.get("creative") or {})
        key = (us[0][0].split("?")[0], us[0][1]) if us else ("(none)", "")
        byurl[key].append(ad.get("name", "?"))
    for (u, cta), adnames in sorted(byurl.items(), key=lambda x: -len(x[1])):
        print("      %s   [%s]   %d ads" % (u[:62], cta or "", len(adnames)))
        for n in sorted(adnames)[:10]:
            print("           - " + n[:70])
        if len(adnames) > 10:
            print("           ... +%d more" % (len(adnames) - 10))
print("")

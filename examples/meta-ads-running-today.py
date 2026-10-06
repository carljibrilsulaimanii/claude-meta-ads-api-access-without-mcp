# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-ads-running-today.py — run from the repo root (README "More example analyses")
# What: every ACTIVE ad (ad, ad set and campaign all on) whose creative mentions a URL
#       keyword, split into its CLICK URL (the real landing page) and DISPLAY URL (text
#       only), with its campaign, ad set, and spend / impressions for today and yesterday.
# Why:  "Active" only means the ad is switched on. This shows whether ads pointing at a
#       given page are actually delivering, so a stale destination left over from an
#       old funnel is caught before it spends.
#       The display URL (link_caption, caption, display_url) is printed under the ad and
#       changes nothing about where the tap lands. An audit that treats it as a
#       destination reports ads "sending traffic" to a page they only mention. This
#       script prints click: and display: separately; only click: is a destination.
#       A mismatched display URL is still worth fixing, as a cosmetic issue.
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-ads-running-today.py [URL_KEYWORD]
#         python examples/meta-ads-running-today.py old-funnel.example.com
#         (no keyword = every active ad with a URL; one insights call per ad, so it's slower)

import os, sys, json, urllib.parse, urllib.request, urllib.error

ACT = "act_REPLACE_WITH_AD_ACCOUNT_ID"   # keep the act_ prefix (README Step 5g)
API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)
MATCH = sys.argv[1] if len(sys.argv) > 1 else ""   # matched against click AND display URLs

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


def urls_from(cr):
    """(url, role) pairs. role 'click' = where the tap goes; 'display' = the
    caption / display URL printed under the ad, which does not change the landing page."""
    found = []
    oss = cr.get("object_story_spec") or {}
    for key in ("video_data", "link_data", "photo_data"):
        d = oss.get(key) or {}
        val = (d.get("call_to_action") or {}).get("value") or {}
        for src in (d, val):
            if src.get("link"):
                found.append((src["link"], "click"))
            if src.get("link_caption"):
                found.append((src["link_caption"], "display"))
            if src.get("caption"):
                found.append((src["caption"], "display"))
    afs = cr.get("asset_feed_spec") or {}
    for lu in (afs.get("link_urls") or []):
        if lu.get("website_url"):
            found.append((lu["website_url"], "click"))
        if lu.get("display_url"):
            found.append((lu["display_url"], "display"))
    if cr.get("template_url"):
        found.append((cr["template_url"], "click"))
    return [(u, r) for u, r in found if u]


camps = {c["id"]: c for c in get(ACT + "/campaigns", "name,effective_status")}
adsets = {a["id"]: a for a in get(ACT + "/adsets", "name,campaign_id,effective_status")}

# Account-wide /ads with the creative expanded can exceed Meta's response size limit,
# so walk the active ad sets one at a time with a trimmed creative field set.
CRE = "creative{object_story_spec,asset_feed_spec,template_url}"
hits = []
for sid, s in adsets.items():
    if s.get("effective_status") != "ACTIVE":
        continue
    c = camps.get(s.get("campaign_id")) or {}
    if c.get("effective_status") != "ACTIVE":
        continue
    for ad in get(sid + "/ads", "name,effective_status," + CRE, {"limit": 50}):
        if ad.get("effective_status") != "ACTIVE":
            continue
        urls = urls_from(ad.get("creative") or {})
        if any(MATCH in u for u, _ in urls):
            hits.append((c.get("name", "?"), s.get("name", "?"), ad, urls))


def insight(ad_id, preset):
    r = get(ad_id + "/insights", "spend,impressions", {"date_preset": preset})
    if not r:
        return 0.0, 0
    return float(r[0].get("spend", 0)), int(r[0].get("impressions", 0))


print("ACTIVE ADS WITH A URL MATCHING '%s': %d" % (MATCH, len(hits)))
tot_t = tot_y = 0.0
for cname, sname, ad, urls in sorted(hits, key=lambda h: (h[0], h[1])):
    st, it = insight(ad["id"], "today")
    sy, iy = insight(ad["id"], "yesterday")
    tot_t += st
    tot_y += sy
    print("-" * 80)
    print("campaign: " + cname)
    print("ad set:   " + sname)
    print("ad:       %s (%s)" % (ad.get("name", "?"), ad["id"]))
    print("click:    " + " | ".join(sorted({u for u, r in urls if r == "click"})))
    print("display:  " + " | ".join(sorted({u for u, r in urls if r == "display"})))
    print("today:     $%10.2f  %8d impr" % (st, it))
    print("yesterday: $%10.2f  %8d impr" % (sy, iy))
print("=" * 80)
print("TOTAL today $%.2f   yesterday $%.2f" % (tot_t, tot_y))

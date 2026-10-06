# -*- coding: utf-8 -*-
# Author: Jibril Sulaiman
# Location: examples/meta-ad-creative-dump.py — run from the repo root (README "More example analyses")
# What: for one ad set (or the ad set an ad belongs to), lists every ad in it, any status,
#       and writes each creative's raw object_story_spec / asset_feed_spec / url_tags
#       to ad-creative-dump.json.
# Why:  multi-link ads (asset feeds, i.e. dynamic creative with several videos, texts and
#       links) don't say which link each variant uses in a destinations summary. The raw
#       spec shows which videos, texts and rules carry which URL, and url_tags shows the
#       UTM template appended to every link.
#       Token is read from ~/.meta-ads/token (README Step 7), held in memory, never printed.
#
# Usage:  python examples/meta-ad-creative-dump.py <adset_id | ad_id>
#         Get the id from Ads Manager, or from examples/meta-ads-running-today.py output.

import os, sys, json, urllib.parse, urllib.request, urllib.error

API = "https://graph.facebook.com/v26.0"   # pin the version you tested (README Security)
OUT = os.path.join(os.getcwd(), "ad-creative-dump.json")   # git-ignored (*.json)

if len(sys.argv) < 2:
    sys.exit("usage: python examples/meta-ad-creative-dump.py <adset_id | ad_id>")

tp = os.path.join(os.path.expanduser("~"), ".meta-ads", "token")
if not os.path.exists(tp):
    sys.exit("token file not found: %s" % tp)
TOKEN = open(tp, encoding="utf-8-sig").read().strip().strip('"').strip("'")
if not TOKEN:
    sys.exit("token file is empty")
print("token loaded (%d chars) — not printed, not stored\n" % len(TOKEN))


def call(path, fields, extra=None):
    p = {"fields": fields, "access_token": TOKEN}
    if extra:
        p.update(extra)
    url = API + "/" + path + "?" + urllib.parse.urlencode(p)
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(e.read().decode("utf-8", "replace")[:400])


target = sys.argv[1]
CRE = "creative{id,name,object_story_spec,asset_feed_spec,template_url,url_tags}"
node = call(target, "id,name,adset_id")   # an ad id returns its adset_id; an ad set id doesn't
if "adset_id" in node:
    target = node["adset_id"]
aset = call(target, "id,name,effective_status")
ads = call(target + "/ads", "id,name,effective_status,created_time," + CRE,
           {"limit": 100}).get("data", [])
out = {"adset": aset, "ads": ads}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("ad set:", aset.get("name"), aset.get("effective_status"))
for a in ads:
    print(a["id"], a.get("effective_status"), a.get("name"))
print("-> " + os.path.basename(OUT))

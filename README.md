<!--
  README.md -- Claude + Meta Ads API access without the MCP connector
  Author:  Jibril Sulaiman
  Date:    2026-10-06
  What:    Click-by-click guide for giving Claude read access to a Meta ad account (spend,
           creative, targeting, conversions, pixel diagnostics) through the Graph API with a
           long-lived user token stored in a file, plus two scripts that use it.
  Why:     The Meta Ads MCP connector is enabled account by account, a blocked account has
           no route forward, and the system user token the docs point to is gated behind
           business portfolio admin rights most operators don't have.
-->

# Claude + Meta Ads: API access without the MCP connector

Give Claude read access to a Meta ad account that the Meta Ads MCP connector won't
serve. For many ad accounts, MCP access isn't enabled yet, so the connector can't read
them at all. You create a small Meta app under your own profile, generate a user token with the
Graph API Explorer, extend it to 60 days, and save it to a file on your computer. Claude
(or any script) reads the file at query time and calls the Graph API directly. The token
never enters a chat.

You get spend, creative, targeting and conversion data at account, campaign, ad set and
ad level, plus the pixel diagnostics that catch broken or double-counted conversion
tracking. It takes about 30 minutes, most of it in Meta's screens. You don't need
business portfolio admin rights, App Review or a system user.

## Why it exists

The Meta Ads MCP connector is the intended way to let Claude read an ad account. It is
being enabled **account by account**, and **many ad accounts don't have MCP access
yet.** The connector can list them, but every read on one returns *"This ad account is
not enabled for the Ads MCP."*, and its account details show:

```json
{
  "is_ads_mcp_enabled": false,
  "is_ads_mcp_disabled_reason": "Ads MCP is gradually being rolled out. Please check back at a later date to use Ads MCP with this Ad Account."
}
```

No permission, role or app setting changes that flag, and a Meta rep can't add an
account to the rollout. The connector offers no fallback. Being queryable doesn't help:
an account can show `is_queryable: true` and still be shut out of the MCP. If you manage
several accounts, expect some to be enabled and others not, so check each one
(Step 1).

The obvious fallback is a **system user token**, which never expires and is what Meta's
docs point to. It is blocked for anyone who doesn't administer the business portfolio:

1. In **Business Settings → System users**, **Generate token** is greyed out: *"In order
   to generate a system user access token, an app must be part of this business
   portfolio. Please add an app."*
2. You can't add an app to the portfolio without admin rights.
3. So you create the app under your own profile and try to add a portfolio admin to it.
   That fails with **Form can't be saved**: *"You are trying to add users that haven't
   registered their developer accounts."* Meta won't add anyone to an app until they've
   registered at https://developers.facebook.com/.

A **long-lived user token** has none of those gates. It needs only your own access to
the ad account, and it lasts about 60 days.

### Why read access is worth the setup

Ads Manager already reports spend. The reason to wire Claude in is a class of failure
that is **invisible inside Ads Manager** and shows up only when you compare Meta's data
against your own CRM:

- **A conversion snippet goes missing.** A page is cloned without it, or a new funnel
  ships incomplete. Impressions, clicks, landing page views, CPM and reach all look
  normal, because they're measured independently. Only the conversion event stops. In
  Ads Manager that looks like a performance collapse, which invites the wrong fix
  (pause campaigns, rewrite creative), and bidding degrades for as long as the signal
  is missing. In production this ran undetected for six days and then happened again
  the same month.
- **A conversion is counted twice.** A CRM's native conversion sync is switched on while
  a hand-placed page snippet still fires. Without a shared `event_id`, Meta can't
  deduplicate them. Cost per result then reads at about half its true value, which
  looks like success, so nobody questions it. In production it ran for ten days at
  1.3x to 2x the real count.

| Question | Ads Manager alone | With this access |
|---|---|---|
| Is spend efficient? | Yes | Yes |
| Are conversions actually being recorded? | **No**: an outage and a collapse look the same | Yes: compare against CRM counts |
| Is a conversion being counted twice? | **No** | Yes: the CRM ratio exposes it |
| Did one funnel page stop reporting? | **No** | Yes: event volume by host and by day (Step 9) |
| Which sender is firing (browser, server, a setup-tool rule)? | **No** | Yes: [`scripts/meta-pixel-trace.py`](scripts/meta-pixel-trace.py) |

## How it works

```text
 You (once, ~30 min)                      Claude (every query)
 Meta app ─► Graph API Explorer token      reads ~/.meta-ads/token
          ─► Access Token Debugger: extend ─► GET graph.facebook.com/v26.0/...
          ─► save to ~/.meta-ads/token      ─► answers in plain language
```

Every call is a read (`GET`). Nothing in this guide changes a campaign.

## What's in this repo

| Path | What it is | Where it runs |
|---|---|---|
| [`README.md`](README.md) | This guide | — |
| [`scripts/`](scripts/) | Two Python scripts that read the token file and call the Graph API: an ad set dump (Step 8) and a pixel source trace (Step 9) | Your computer, Python 3.8+, no packages to install |

## Table of contents

- [1. Requirements](#1-requirements)
- [2. Setup, step by step](#2-setup-step-by-step)
  - [Step 1: Confirm the MCP route really is closed](#step-1-confirm-the-mcp-route-really-is-closed)
  - [Step 2: Choose the token type](#step-2-choose-the-token-type)
  - [Step 3: Create the Meta app](#step-3-create-the-meta-app)
  - [Step 4: Check the app's permissions](#step-4-check-the-apps-permissions)
  - [Step 5: Generate a token and find your ad account](#step-5-generate-a-token-and-find-your-ad-account)
  - [Step 6: Extend the token to 60 days](#step-6-extend-the-token-to-60-days)
  - [Step 7: Save the token to a file](#step-7-save-the-token-to-a-file)
  - [Step 8: Verify, then dump your ad sets](#step-8-verify-then-dump-your-ad-sets)
  - [Step 9: Pixel diagnostics](#step-9-pixel-diagnostics)
  - [Step 10: Let Claude use it](#step-10-let-claude-use-it)
- [Limits](#limits)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)
- [Security](#security)

## 1. Requirements

| Need | Why |
|---|---|
| Your own Facebook profile has access to the ad account (*View performance* is enough) | A user token can only see what your profile can see |
| A Facebook profile that can create Meta apps | New profiles may first be asked to confirm a phone number or card (see Troubleshooting) |
| Python 3.8 or later | Only for the two scripts; uses the standard library |
| Claude Code, or any Claude client that can run a script | To query on your behalf |

You do **not** need business portfolio admin, App Review, Standard Access or a system
user.

## 2. Setup, step by step

### Step 1: Confirm the MCP route really is closed

About 2 minutes.

**1a.** Don't assume. In Claude, with the Meta Ads connector enabled, ask:

> *Use the Meta Ads connector to list my ad accounts.*

**1b.** Read three fields on your account:

| Field | Meaning |
|---|---|
| `is_ads_mcp_enabled` | `false` means the connector won't serve this account. Continue with this guide. |
| `is_queryable` | A different flag. An account can be queryable and still not MCP-enabled. |
| `account_status` | Matters more than either. A `DISABLED` account is a dead end whatever token you use. Resolve that with Meta first. |

✅ **Check:** your account shows `is_ads_mcp_enabled: false` and is not `DISABLED`. If it
shows `true`, use the connector instead and stop here.

### Step 2: Choose the token type

About 1 minute. This fork wastes more time than the rest of the setup combined.

| | System user token | Long-lived user token |
|---|---|---|
| Expires | Never | About 60 days |
| Needs an app owned by the business portfolio | Yes | No |
| Needs portfolio admin rights | Yes | No |
| Needs your own ad account access | No | Yes |

**Take the user token unless you personally hold business portfolio admin.** The rest of
this guide is the user-token route.

✅ **Check:** you know whether you're a portfolio admin. If you're not, carry on.

### Step 3: Create the Meta app

About 5 minutes.

**3a.** Go to https://developers.facebook.com/apps/ and click **Create App**. The wizard
has five tabs: **App details · Use cases · Business · Requirements · Overview**.

**3b. App details.** Enter an **App Name** (for example `Claude Ads Reader`) and an
**App Email**. Click **Next**.

**3c. Use cases.** Under **Add use cases**, filter **Featured**. Tick **only**
**Create & manage ads with Marketing API**. Click **Next**.

> ⚠️ **Tick one use case.** Every extra use case adds review requirements you don't need
> for reading your own accounts.

**3d. Business.** The heading is *"Which business portfolio do you want to connect to
this app?"* If you're not a portfolio admin, your portfolio usually isn't listed. Choose
the last option, **I don't want to connect a business portfolio yet.** This blocks
nothing on the user-token route. Click **Next**.

> ⚠️ **Scroll inside the list before deciding a portfolio is missing.** The list scrolls
> on its own, and the top entry can sit above the fold.

**3e. Requirements.** It should say *"No requirements for the use cases on this app."*
Click **Next**.

**3f. Overview.** Check **App Name**, **App Email**, and Business *"No business
selected."* Click **Create app**. Meta may ask for your password (wording may differ).

**3g.** On the app dashboard, copy the **App ID**. You'll pick the app by name in Step 5,
but keep the id for reference.

✅ **Check:** the app dashboard opens with your app name at the top.

### Step 4: Check the app's permissions

About 2 minutes.

**4a.** In the app's left menu, open **Use cases**, then **Customize** on *Create &
manage ads with Marketing API*. The page heading is **Customize use case**.

**4b.** In the left nav, open **Permissions and features**. Find these three and confirm
each shows **Ready for testing**:

| Permission | Needed for |
|---|---|
| `ads_read` | Spend, creative, targeting, insights (Steps 5 to 8) |
| `ads_management` | Pixel diagnostics (`/stats`, Step 9) |
| `business_management` | Pixel diagnostics (`/stats`, Step 9) |

**4c.** **Marketing API Access Tier** reads **Limited access**. That's the development
tier and it's enough here. Insights queries return data on it. Only apply for Standard
Access if you actually hit a rate limit or an error that asks for it.

✅ **Check:** all three permissions show **Ready for testing**. You don't need to submit
anything for App Review.

### Step 5: Generate a token and find your ad account

About 5 minutes.

**5a.** Open the **Graph API Explorer** at https://developers.facebook.com/tools/explorer/.

**5b.** In the right-hand panel:
1. **Meta App** → your app from Step 3.
2. **User or Page** → **User Token**.
3. **Permissions** tab → **Add a Permission** → add `ads_read`, `ads_management` and
   `business_management`. Add all three now: a token with only `ads_read` works for
   spend but returns `(#100) Permission Denied` on pixel diagnostics, and you'd have to
   generate and extend a second token.
4. Leave the version dropdown on its default (**v26.0** when this was built).

**5c.** Click **Generate Access Token**. Approve the Facebook dialog. If it lists
businesses or ad accounts, make sure yours is ticked (wording may differ).

**5d.** Click **Submit** on the default query `me?fields=id,name`. Your name and id come
back.

**5e.** Confirm every permission was granted. Replace the query with:

```text
me/permissions
```

Every permission you added should read `granted`. A `declined` means the dialog didn't
include it. Generate again and approve it.

**5f.** Find your ad account. Replace the query with:

```text
me/adaccounts?fields=name,account_id,account_status
```

> ⚠️ **The list pages at 25.** On a profile with access to many accounts (an agency
> profile, say), yours may not be on the first page. In production it was on page 2.
> Click the `next` link under `paging` in the response (or add `&limit=200`) **before**
> concluding you lack access.

**5g.** Copy your `account_id`. API calls use it with an `act_` prefix:
`act_1234567890`.

**5h.** Optional double check: on Facebook, open **Settings → Business Integrations**,
click your app, and confirm **Access your Facebook ads and related stats** is switched
on. **Cancel** out without changing anything.

✅ **Check:** your ad account appears in `me/adaccounts`, and `me/permissions` shows all
three permissions `granted`.

### Step 6: Extend the token to 60 days

About 3 minutes. An Explorer token lasts about an hour. Extending it gives you about 60
days.

**6a.** Open the **Access Token Debugger** at
https://developers.facebook.com/tools/debug/accesstoken/. Paste the token from the
Explorer's **Access Token** box and click **Debug**.

**6b.** Read the table: **Valid** should be *True*, **Origin** *Web*, and **Scopes** should
list your three permissions.

**6c.** Scroll to the bottom and click **Extend Access Token**. You may be asked for your
password.

**6d.** Below the button, a line reads *"This new long-lived access token will expire on
<date>:"* with the new token under it.

> ⚠️ **Copy the token below the button, not the one you pasted.** They're different
> strings, and the original is still on screen above.

> ⚠️ **Don't screenshot this page.** It shows the full token, and a screenshot is a copy
> of the credential. If you opened the debugger from a link, the token may also be in
> the URL, and so in your browser history. Close the tab when you're done.

**6e.** Paste the new token back into the debugger and click **Debug** again.

✅ **Check:** **Expires** reads about 60 days out.

### Step 7: Save the token to a file

About 2 minutes. **Never paste a token into a chat.** Write it to disk yourself, outside
any folder that gets shared, synced, previewed or committed.

**7a.** In **PowerShell**, replace `<PASTE_TOKEN_HERE>` with the extended token and run:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.meta-ads" | Out-Null
Set-Content "$env:USERPROFILE\.meta-ads\token" -Value '<PASTE_TOKEN_HERE>' -NoNewline -Encoding ascii
"saved: $((Get-Content "$env:USERPROFILE\.meta-ads\token" -Raw).Length) chars"
```

Expect `saved: 200 chars` or more.

> ⚠️ **Run each line in PowerShell, not a bash one-liner.** Windows PowerShell 5.1 rejects
> `&&` (*"The token '&&' is not a valid statement separator in this version."*) and `<`
> (*"The '<' operator is reserved for future use."*).

> ⚠️ **Keep `-NoNewline`.** Without it, PowerShell adds a line break to the file. The
> scripts here strip it, but other tools may send it as part of the token.

**7b.** On macOS or Linux:

```bash
mkdir -p ~/.meta-ads && printf '%s' '<PASTE_TOKEN_HERE>' > ~/.meta-ads/token && chmod 600 ~/.meta-ads/token
```

**7c.** Clear the command from your shell history if your shell keeps one (PowerShell:
`Clear-History`, and delete the line from the PSReadLine history file).

✅ **Check:** the file exists and the length is 200 or more characters.

### Step 8: Verify, then dump your ad sets

About 5 minutes.

**8a.** In the Graph API Explorer (with your extended token pasted into **Access Token**),
run these in order. Each one isolates a different failure:

| Query | Proves |
|---|---|
| `me/adaccounts?fields=name,account_id` | The token sees the account |
| `act_<AD_ACCOUNT_ID>?fields=name,account_status,currency` | The account is reachable |
| `act_<AD_ACCOUNT_ID>/insights?level=campaign&time_increment=1&fields=campaign_name,spend,impressions,reach,frequency,actions&date_preset=last_7d&limit=5` | Insights work on the development tier: the real query shape |

Once the third returns a `spend` figure, the access is live.

**8b.** Open [`scripts/meta-adsets-dump.py`](scripts/meta-adsets-dump.py) and set `ACT` at
the top to your account, keeping the `act_` prefix:

```python
ACT = "act_1234567890"
```

**8c.** From the repo folder, run it:

```powershell
python scripts/meta-adsets-dump.py
```

Runs [`scripts/meta-adsets-dump.py`](scripts/meta-adsets-dump.py).

Success looks like:

```text
token loaded (200 chars) — not printed, not stored
fetched 48 ad sets (6 ACTIVE) -> adsets-live.json
```

`adsets-live.json` holds every ad set with its campaign, objective, budgets (so you can
tell ABO from CBO), optimization goal, bid strategy, schedule and full targeting,
including included and excluded audiences. It's git-ignored because it holds your
targeting.

✅ **Check:** `adsets-live.json` exists and the ACTIVE count matches Ads Manager.

### Step 9: Pixel diagnostics

About 5 minutes. Reading ad performance and reading pixel event data need different
permissions.

**9a.** Confirm your token has `ads_management` and `business_management` (Step 5e). With
`ads_read` only, every `/stats` call returns `(#100) Permission Denied`, which looks like
a token problem and isn't. In production, adding those two scopes and re-extending the
token was the whole fix.

**9b.** Find your pixel (dataset) id in **Events Manager → Data sources**.

**9c.** In the Explorer, try one call (Unix timestamps for the window):

```text
<PIXEL_ID>/stats?aggregation=event&start_time=<UNIX>&end_time=<UNIX>
```

If it still returns `(#100)` with the right scopes, ask a business admin for a **Manage**
role on the dataset at https://business.facebook.com/settings/datasets (this wasn't
needed in production, so treat it as the next thing to try, not a first step).

**9d.** Open [`scripts/meta-pixel-trace.py`](scripts/meta-pixel-trace.py), set `PIXEL` at
the top, and run it with an event name and a number of days:

```powershell
python scripts/meta-pixel-trace.py Purchase 7
```

Runs [`scripts/meta-pixel-trace.py`](scripts/meta-pixel-trace.py).

It prints the pixel's name and last fire time, then the event's volume split seven ways:

| Aggregation | What it tells you |
|---|---|
| `event` | Volume per event. Your conversion event falling while `PageView` holds steady is the missing-snippet signature. |
| `event_source` | `BROWSER` vs `SERVER`. Tells you whether a page snippet or a server-side sender is the one that changed. |
| `event_detection_method` | The only one that exposes **Event Setup Tool** rules, a hidden sender that's easy to forget. |
| `host` / `url` | Volume per domain or page. When a funnel is swapped, the host mix shifts the same day the conversion dies. |
| `pixel_fire`, `device_type` | Sanity checks. |

> ⚠️ **Pass the event.** Without `&event=<name>`, the `host` and `url` buckets count all
> traffic and look like a PageView map. The script passes it, and retries unfiltered for
> any aggregation that rejects the filter (it says so in the output).

> ⚠️ **`/stats` buckets are hourly. Sum them.** Assigning instead of summing reports the
> last hour of each day as the daily total: plausible-looking and wrong by an order of
> magnitude. The script sums.

> ⚠️ **`last_fired_time` is not a health check.** It can lag, and a stale value isn't
> evidence the pixel stopped. Use the `event` aggregation by day.

✅ **Check:** the script prints counts for at least `event` and `event_source` with no
`ERROR:` lines.

### Step 10: Let Claude use it

About 2 minutes.

**10a.** Tell Claude once, in the project you'll work in:

> *The Meta token is at `~/.meta-ads/token`. The ad account is `act_<AD_ACCOUNT_ID>` and the
> pixel is `<PIXEL_ID>`. Read the token file at query time, never print it, and use
> Graph API v26.0.*

**10b. In Claude Code**, a script that reads a token file can be stopped by the
permission check as credential access, and asking Claude to add the permission for
itself is stopped too. Add the rule yourself, once. In your project's
`.claude/settings.json` (or through `/permissions` in a terminal session):

```json
{
  "permissions": {
    "allow": [
      "Bash(python scripts/meta-adsets-dump.py:*)",
      "Bash(python scripts/meta-pixel-trace.py:*)"
    ]
  }
}
```

Keep the scripts at stable paths in the project. A rule for a temporary folder breaks
the next session.

**10c.** If you'd rather not add a rule, Claude can hand you a PowerShell command to run
yourself. The token stays in your shell and only the JSON lands in the project:

```powershell
$t = (Get-Content "$env:USERPROFILE\.meta-ads\token" -Raw).Trim()
Invoke-RestMethod "https://graph.facebook.com/v26.0/<path>?<params>&access_token=$t" |
  ConvertTo-Json -Depth 8 | Set-Content ".\out.json"
```

**10d.** Ask for outcomes, not endpoints. Claude builds the queries:

- *"Pull daily spend and conversions by campaign for the last 30 days."*
- *"Compare the pixel's Lead events against our CRM registrations by week and flag any
  week under 80%."*
- *"For the top ads by spend, list the headline, body, description and destination URL."*
- *"Which ad sets are true broad, and which use lookalikes or exclusions?"*
- *"Show Purchase volume by host for the last two weeks."* ← the funnel-swap detector
- *"Split Purchase into browser versus server."* ← finds which sender changed

✅ **Check:** Claude answers one of those without asking you for the token.

## Limits

- **37-month history ceiling, rolling.** Older ranges return `(#3018) The start date of
  the time range cannot be beyond 37 months from the current date`. The floor moves
  daily. Export older history before it ages out; it can't be recovered later.
- **Meta restates about the last 28 days.** Spend and attribution are revised after the
  fact. A scheduled sync must re-pull a trailing window and update, not append one day.
- **Conversions attribute to click date; your CRM records submission date.** Day-level
  ratios between the two are noisy. Compare weekly or period totals.
- **Several `action_type` values can report the same event.** On one lead account,
  `lead`, `onsite_web_lead`, `offsite_conversion.fb_pixel_lead` and
  `offsite_lead_add_20_s_calls` matched every day. Pick one, write it down and move on.
- **Read only.** Nothing here writes to Meta. Changing campaigns needs `ads_management`
  used for writes and is out of scope.

## Troubleshooting

| You got | Cause | Fix |
|---|---|---|
| `is_ads_mcp_enabled: false` | Meta's rollout flag | Not configurable. Follow this guide (Step 1). |
| **Generate token** greyed out (system user) | No app owned by the portfolio | Use a user token (Step 2) |
| *"Your account must be confirmed before you can create a new app. Please confirm your account by adding your mobile phone number or credit card."* and the confirm link loops | That profile isn't confirmed for development | Create the app from a profile that's already confirmed and has access to the ad account (Step 3) |
| **Form can't be saved** / *"users that haven't registered their developer accounts"* | Adding a non-developer to the app | They register at developers.facebook.com first, or skip it: the user-token route doesn't need them (Step 2) |
| *"There was an unexpected technical issue. Please try again."* when adding the app in Business Settings | Not resolved | Not needed for this route. Skip it. |
| Your account is missing from `me/adaccounts` | Paging at 25, or no assignment | Follow `paging.next` or add `&limit=200` (Step 5f), then check **Assign people** on the account in Business Settings |
| `(#100) Permission Denied` on `/stats` | Token lacks `ads_management` / `business_management` | Add both, generate, extend, re-save (Steps 5 to 7, Step 9a) |
| `(#100) Missing perms`, then `(#200) Ad account owner has NOT grant ads_management or ads_read permission` while `me` still works | Someone removed your profile from the ad account | Get the assignment restored. **Test the existing token first**: in production the same token worked again once access came back. Regenerating forces you to update every place it's stored. |
| `(#3018) ...beyond 37 months` | History ceiling | Nothing to fix (see Limits) |
| `Error validating access token` | Expired (about 60 days) | Extend again (Step 6) and re-save (Step 7) |
| `set ACT at the top of this file...` / `set PIXEL...` | Placeholder still in the script | Steps 8b and 9d |
| `token file not found` | File not at `~/.meta-ads/token` | Step 7 |
| Daily totals wildly too small | Hourly `/stats` buckets assigned, not summed | Sum per day (Step 9) |

## Maintenance

| When | Do |
|---|---|
| Day 55 of each token | Extend again in the debugger (Step 6) and overwrite the file (Step 7). Nothing else changes. Token expiry fails silently in anything scheduled, so put it on a calendar. |
| After any funnel launch | Run the Step 9 `event` and `host` check. This is when snippets go missing. |
| After any permission change in Business Settings | Confirm `me/adaccounts` still lists the account |
| Monthly | Re-check `is_ads_mcp_enabled` (Step 1). If it flips to `true`, switch to the connector, delete the token file, and remove the app. |

## Security

- The token reads everything your profile can see in that account. Treat it like a
  password.
- **Never paste it into a chat, a screenshot, a ticket or a commit.** In the original
  build it leaked into a debugger screenshot, a pasted terminal command and the browser
  history. Each of those is a working copy until the token expires.
- If a token leaks, revoke it: on Facebook, **Settings → Business Integrations**, remove
  the app (wording may differ), then repeat Steps 5 to 7.
- The scripts read the file into memory, print only its length, and never write it
  anywhere. `.gitignore` excludes `token` files and the JSON output.
- Pin the API version you tested (`v26.0` here). Meta retires old versions on a
  schedule.

---

Built by [Jibril Sulaiman](https://github.com/carljibrilsulaimanii).

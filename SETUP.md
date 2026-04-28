# War Room — Setup & Deployment Guide

## Overview
This project generates a daily intelligence dashboard and publishes it to
**www.newsofpast.com** via GitHub Pages. You run it manually whenever you want;
it updates the site automatically after each run.

---

## Step 1 — Add your Anthropic API key (if not done yet)

```bash
cp /Users/mohammadmobin/Documents/Claude/war-room/.env.example \
   /Users/mohammadmobin/Documents/Claude/war-room/.env
```
Edit `.env` and replace `sk-ant-your-key-here` with your real key from
https://console.anthropic.com/settings/keys

---

## Step 2 — Create the GitHub repository

1. Go to **https://github.com/new**
2. Repository name: **`newsofpast`**
3. Set visibility to **Public**
4. **Do not** add a README, .gitignore, or license (leave it empty)
5. Click **Create repository**

---

## Step 3 — Run the one-time GitHub setup script

```bash
/Users/mohammadmobin/Documents/Claude/war-room/setup_github.sh
```

This script will:
- Initialize git in the `war-room/` folder
- Add `https://github.com/msmobin/newsofpast.git` as the remote
- Commit all existing files (reports included)
- Push everything to GitHub
- Print the next steps

> **Authentication:** macOS will open a browser window to log in to GitHub
> the first time. After that it's stored in the macOS Keychain.

---

## Step 4 — Enable GitHub Pages

1. Open: **https://github.com/msmobin/newsofpast/settings/pages**
2. Under **Source** → choose `Deploy from a branch`
3. Branch → **main** / **(root)** → click **Save**
4. Under **Custom domain** → type `www.newsofpast.com` → click **Save**
5. Wait ~2 minutes, then check **Enforce HTTPS** when it becomes available

---

## Step 5 — Add DNS records in Squarespace

Log in to Squarespace → **Domains** → `newsofpast.com` → **DNS Settings**

### Remove conflicting preset first
If you have a **Squarespace Website** DNS Preset applied, you need to remove
the `www` CNAME entry it created (it points to Squarespace servers — you are
replacing it with GitHub Pages).

### Add these records

| Type  | Host | Data / Points to       | TTL  |
|-------|------|------------------------|------|
| CNAME | www  | `msmobin.github.io`    | 3600 |
| A     | @    | `185.199.108.153`      | 3600 |
| A     | @    | `185.199.109.153`      | 3600 |
| A     | @    | `185.199.110.153`      | 3600 |
| A     | @    | `185.199.111.153`      | 3600 |

- The **CNAME** makes `www.newsofpast.com` point to your GitHub Pages site.
- The four **A records** make the bare domain `newsofpast.com` redirect to `www`.
- DNS changes take **5 minutes to 48 hours** to propagate worldwide.

---

## Daily usage — run whenever you want

```bash
/Users/mohammadmobin/Documents/Claude/war-room/run_now.sh
```

This single command:
1. Generates today's report (overwrites if already run today)
2. Commits the new files to git
3. Pushes to GitHub → site updates within ~2 minutes
4. Opens the local calendar in your browser

---

## File structure

```
war-room/
├── index.html              ← Calendar landing page
├── CNAME                   ← Tells GitHub Pages your custom domain
├── .nojekyll               ← Disables Jekyll processing on GitHub Pages
├── news/
│   └── YYYY-MM-DD.html     ← Daily reports (preserved permanently)
├── data/
│   └── reports.json        ← Metadata index for the calendar
├── generate_report.py      ← Report generator (Anthropic API)
├── run_now.sh              ← Run this to generate + publish
├── setup_github.sh         ← Run this ONCE to connect to GitHub
├── requirements.txt
├── .env                    ← Your API key — NEVER committed
├── .gitignore
└── warroom.log             ← Run log (not committed)
```

---

## Troubleshooting

**Site not loading at www.newsofpast.com after DNS changes?**
DNS can take up to 48 hours. Check propagation at https://dnschecker.org

**`git push` fails with authentication error?**
Run: `gh auth login` (requires GitHub CLI) or generate a Personal Access
Token at https://github.com/settings/tokens and use it as your password.

**Generation failed / JSON error?**
Check the log: `tail -50 /Users/mohammadmobin/Documents/Claude/war-room/warroom.log`

**Unload the old 7AM scheduler (if you loaded it previously):**
```bash
launchctl unload ~/Library/LaunchAgents/com.warroom.daily.plist 2>/dev/null
rm ~/Library/LaunchAgents/com.warroom.daily.plist 2>/dev/null
```

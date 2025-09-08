# LinkedIn Auto Blogger (Free)

Automated short cybersecurity & AI posts to your **LinkedIn personal profile** every **2 days** between **08:00–17:00 America/Toronto**, with **ntfy** push notifications **10 minutes before** and **immediately after** posting.
No paid services: GitHub Actions + LinkedIn Posts API + ntfy.

## Features

* **Every 2 days** cadence (no duplicates).
* Randomized posting time **inside 8AM–5PM**.
* **Pre-notification (10 min ahead)** and **post-notification** via [ntfy](https://ntfy.sh).
* Content from **`topics.csv`** using a concise template (no paid AI).
* Uses LinkedIn **Posts API** (`w_member_social` scope).

## Repository structure

```
/ (repo root)
  topics.csv
  scripts/
    run.py
  .github/
    workflows/
      linkedin.yml
  README.md
```

## Quick start

1. **Create a LinkedIn Developer App** and authorize your account to get:

   * `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`
   * `LINKEDIN_REFRESH_TOKEN` (authorization code flow)
   * `LINKEDIN_MEMBER_URN` (format: `urn:li:person:XXXXXXXX`)
2. **Add GitHub Actions secrets**
   Repo → **Settings → Secrets and variables → Actions** → *New repository secret*:

   * `LINKEDIN_CLIENT_ID`
   * `LINKEDIN_CLIENT_SECRET`
   * `LINKEDIN_REFRESH_TOKEN`
   * `LINKEDIN_MEMBER_URN`
   * `NTFY_TOPIC` (pick a hard-to-guess topic, e.g., `chat-sec-ai-7k2p9`)
3. **Subscribe to notifications**
   Open `https://ntfy.sh/<your-topic>` in a browser or the ntfy mobile app and **Subscribe**.
4. **Confirm files are in place**

   * `topics.csv` at the **repo root**.
   * `scripts/run.py` exists.
   * `.github/workflows/linkedin.yml` exists.
5. **Run once (optional)**
   Go to **Actions → linkedin-auto-blogger → Run workflow** to test.
   (Posting still respects the *every-2-days* gate and random time window.)

## Scheduling behavior

* Workflow triggers at **12:00 UTC** and **17:00 UTC** daily.
* The Python script:

  * Posts **only on alternate days** (every 2 days) relative to `ANCHOR_DATE`.
  * Chooses **morning** or **afternoon** window on that day (alternates).
  * Waits a **random offset** within the window, sends a **10-minute heads-up**, then posts.

**Change timezone or cadence**

* Timezone: set `TIMEZONE` (default `America/Toronto`) in the workflow env.
* First posting day: edit `ANCHOR_DATE` in `scripts/run.py` (ISO date).
* CSV path: change `TOPICS_CSV` in the workflow env if you move the file.

## Configuration (env vars)

Defined in `.github/workflows/linkedin.yml`:

| Variable           | Purpose                          | Example           |
| ------------------ | -------------------------------- | ----------------- |
| `TIMEZONE`         | Local time zone for messaging    | `America/Toronto` |
| `TOPICS_CSV`       | Path to your topics CSV          | `topics.csv`      |
| `LINKEDIN_VERSION` | REST API version header (YYYYMM) | `202507`          |
| `NTFY_URL`         | ntfy endpoint                    | `https://ntfy.sh` |
| `CRON_SCHEDULE`    | Populated by GitHub on schedule  | *(auto)*          |

**Secrets (Actions → Secrets):**
`LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_REFRESH_TOKEN`, `LINKEDIN_MEMBER_URN`, `NTFY_TOPIC`.

## Content: `topics.csv`

**Required header:**

```
id,title,outline,cta,hashtags
```

* `outline` uses `|` to separate bullet points.
* The composer creates a short, practical post + CTA + hashtags and trims to stay under LinkedIn’s limit.

**Example row**

```csv
1,Zero Trust for small teams,"Map critical assets|Segment access by role|Continuous verification|Kill legacy implicit trust|Pilot one app","What’s one app you’d move to Zero Trust this quarter?",#ZeroTrust #Cybersecurity #Identity
```

## Manual run & quick tests

* **Manual run:** Actions → *linkedin-auto-blogger* → **Run workflow**.
* **Force a same-day test:** temporarily set `ANCHOR_DATE` in `scripts/run.py` to today, commit, run once, then revert.
* **Reduce waiting during tests:** change `random.randint(...)` to `0` in `run.py` to skip the random delay, then revert.

## Troubleshooting

**`python: can't open file '.../scripts/run.py'`**

* Cause: `scripts/run.py` missing or wrong path/case.
* Fix: Ensure `scripts/run.py` exists exactly at that path; commit it.

**“Not a posting day” / “This slot is not chosen window today.”**

* The cadence guard is working. See “Manual run & quick tests.”

**`LinkedIn post failed: 401/403`**

* Wrong/expired tokens, missing scope, or URN mismatch. Re-authorize for `w_member_social`, refresh tokens, and confirm `LINKEDIN_MEMBER_URN`.

**Missing CSV**

* If you moved it, update `TOPICS_CSV` in the workflow env.
* Optional sanity step before the run:

```yaml
- name: Sanity check
  run: |
    echo "TOPICS_CSV=$TOPICS_CSV"
    ls -la
    test -f "$TOPICS_CSV" || (echo "❌ Missing $TOPICS_CSV"; exit 1)
```

## Security

* Keep tokens in **GitHub Secrets** (never commit them).
* Rotate your refresh token periodically or if you suspect exposure.

## License

MIT

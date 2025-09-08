#!/usr/bin/env python3
import os, csv, random, time, requests, sys, json, datetime, textwrap, urllib.parse
from zoneinfo import ZoneInfo

TIMEZONE = os.getenv("TIMEZONE", "America/Toronto")
CRON_SCHEDULE = os.getenv("CRON_SCHEDULE", "")
TOPICS_CSV = os.getenv("TOPICS_CSV", "topics.csv")
ANCHOR_DATE = os.getenv("ANCHOR_DATE", "2025-09-08")  # first Monday after setup; adjust as desired

# LinkedIn credentials (set as GitHub Secrets)
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("LINKEDIN_REFRESH_TOKEN")
AUTHOR_URN = os.getenv("LINKEDIN_MEMBER_URN")  # e.g., urn:li:person:XXXXXXXX

# ntfy notifications
NTFY_URL = os.getenv("NTFY_URL", "https://ntfy.sh")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")

LI_VERSION = os.getenv("LINKEDIN_VERSION", "202507")  # YYYYMM; keep recent
MAX_LEN = 2900  # stay under official 3000 char cap

def is_posting_day(today: datetime.date) -> bool:
    # Every 2 days vs anchor date, in local time
    anchor = datetime.date.fromisoformat(ANCHOR_DATE)
    delta = (today - anchor).days
    return delta >= 0 and delta % 2 == 0

def choose_window_index(today: datetime.date) -> int:
    """Return 0 for MORNING (12:00 UTC trigger), 1 for AFTERNOON (17:00 UTC trigger).
    Alternate each posting day deterministically: even index -> morning, odd -> afternoon.
    """
    anchor = datetime.date.fromisoformat(ANCHOR_DATE)
    n = ((today - anchor).days) // 2
    return 0 if n % 2 == 0 else 1

def this_run_slot() -> int:
    if CRON_SCHEDULE.strip() == "0 12 * * *":
        return 0
    if CRON_SCHEDULE.strip() == "0 17 * * *":
        return 1
    # Fallback by time-of-day if run manually
    now_utc = datetime.datetime.now(datetime.timezone.utc).time()
    return 0 if now_utc < datetime.time(15,0) else 1

def read_topics(path=TOPICS_CSV):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows

def pick_topic_index(today: datetime.date, count: int) -> int:
    anchor = datetime.date.fromisoformat(ANCHOR_DATE)
    delta = (today - anchor).days
    n = delta // 2
    return n % count

def ntfy_send(title, message, tags=None, priority=3):
    if not NTFY_TOPIC:
        print("[warn] NTFY_TOPIC not set; skipping notification.")
        return
    headers = {"Title": title, "Priority": str(priority)}
    if tags:
        headers["Tags"] = ",".join(tags)
    url = f"{NTFY_URL.rstrip('/')}/{NTFY_TOPIC}"
    resp = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=20)
    print(f"[ntfy] {resp.status_code}")

def refresh_access_token():
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        raise RuntimeError("Missing LinkedIn OAuth secrets (client id/secret or refresh token)")
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    resp = requests.post("https://www.linkedin.com/oauth/v2/accessToken", data=data, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to refresh token: {resp.status_code} {resp.text}")
    tok = resp.json()
    return tok["access_token"]

def compose_post(row):
    title = row["title"].strip()
    outline = [b.strip() for b in row["outline"].split("|")]
    cta = row["cta"].strip()
    hashtags = row["hashtags"].strip()

    opening = f"{title}: a practical playbook.\n"
    points = ""
    for b in outline:
        points += f"\n• {b}"
    body = (
        f"{opening}"
        f"Here’s a crisp checklist from the trenches to move you forward:{points}\n\n"
        f"Pro tip: Start small, measure impact, and iterate.\n\n"
        f"Question: {cta}"
    )
    # Trim if needed
    post = body.strip()[:MAX_LEN- len("\n\n") - len(hashtags)]
    post = f"{post}\n\n{hashtags}"
    return post

def post_to_linkedin(text):
    if not AUTHOR_URN:
        raise RuntimeError("LINKEDIN_MEMBER_URN is not set (e.g., urn:li:person:XXXX)")
    access_token = refresh_access_token()
    payload = {
        "author": AUTHOR_URN,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": []
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": LI_VERSION,
        "Content-Type": "application/json"
    }
    resp = requests.post("https://api.linkedin.com/rest/posts", headers=headers, json=payload, timeout=60)
    if resp.status_code not in (201, 202):
        raise RuntimeError(f"LinkedIn post failed: {resp.status_code} {resp.text}")
    post_urn = resp.headers.get("x-restli-id", "").strip()  # e.g., urn:li:share:...
    view_url = None
    if post_urn:
        view_url = "https://www.linkedin.com/feed/update/" + urllib.parse.quote(post_urn)
    return post_urn, view_url

def main():
    now_local = datetime.datetime.now(ZoneInfo(TIMEZONE))
    today = now_local.date()

    # Gate days (every 2 days)
    if not is_posting_day(today):
        print("[info] Not a posting day. Exiting.")
        return

    # Gate window (morning vs afternoon alternation)
    chosen_window = choose_window_index(today)
    if this_run_slot() != chosen_window:
        print("[info] This slot is not chosen window today. Exiting.")
        return

    # Determine random offset inside window and pre-notify 10 minutes earlier
    # Morning window runs at 12:00 UTC; allow up to 5 hours -> 0..300 min
    # Afternoon window runs at 17:00 UTC; allow up to 4 hours -> 0..240 min
    max_offset = 300 if chosen_window == 0 else 240
    offset = random.randint(0, max_offset)
    pre_offset = max(0, offset - 10)

    # Sleep until 10 minutes before post
    if pre_offset > 0:
        print(f"[sleep] Waiting {pre_offset} minutes until pre-notify...")
        time.sleep(pre_offset * 60)

    # Load topics and select today's
    rows = read_topics(TOPICS_CSV)
    idx = pick_topic_index(today, len(rows))
    row = rows[idx]
    planned_text = compose_post(row)

    # Pre-notify
    sched_time = now_local + datetime.timedelta(minutes=10 + (offset - pre_offset))
    ntfy_send(
        title="LinkedIn Auto-Post (10 min heads-up)",
        message=(f"Next post in ~10 minutes at {sched_time.strftime('%Y-%m-%d %H:%M %Z')} "
                 f"\nTitle: {row['title']}\nPreview:\n\n{planned_text[:400]}…"),
        tags=["spiral_calendar","memo"],
        priority=4
    )

    # Sleep last 10 minutes
    print("[sleep] Final 10-minute wait before posting...")
    time.sleep(10 * 60)

    # Post
    try:
        urn, url = post_to_linkedin(planned_text)
        ntfy_send(
            title="LinkedIn Auto-Post (Success)",
            message=f"Published: {row['title']}\n{url or urn}",
            tags=["white_check_mark","link"],
            priority=3
        )
        print("[done]", urn, url)
    except Exception as e:
        ntfy_send(
            title="LinkedIn Auto-Post (Failed)",
            message=f"Error: {e}",
            tags=["x","warning"],
            priority=5
        )
        raise

if __name__ == "__main__":
    main()

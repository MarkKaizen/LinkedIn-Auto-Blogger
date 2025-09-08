# Write a ready-to-use README.md to the sandbox so the user can download or paste it.
readme = """# LinkedIn Auto Blogger (Free)

Automated short cybersecurity & AI posts to your **LinkedIn personal profile** every **2 days** between **08:00–17:00 America/Toronto**, with **ntfy** push notifications **10 minutes before** and **immediately after** posting.  
No paid services: GitHub Actions + LinkedIn Posts API + ntfy.

---

## Features

- **Every 2 days** cadence (no duplicates).
- Randomized posting time **inside 8AM–5PM**.
- **Pre-notification (10 min ahead)** and **post-notification** via [ntfy](https://ntfy.sh).
- Content from **`topics.csv`** using a concise template (no paid AI).
- Uses LinkedIn **Posts API** (`w_member_social` scope).

---

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

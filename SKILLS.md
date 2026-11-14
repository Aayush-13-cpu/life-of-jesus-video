# Skills for this project

Claude Code skills that make this channel faster to run and more professional. Type the command in Claude Code,
inside this repository. They are grouped by the stage of the work they help with.

## 1. Writing new videos

| Skill | Use it for | Example |
|---|---|---|
| `/yt-script` | New Short stories and long-video chapters: scored hook options for the first 15 seconds, then the full narration with retention beats marked | `/yt-script a Short on the widow's oil, 4 beats, KJV quotes` |
| `/yt-viral` | Finding which Bible stories and prayer formats are working in the faith niche right now, before you write the next batch | `/yt-viral christian prayer and bible story channels` |
| `/yt-plan` | A posting calendar for the 40 Shorts and the long videos, sized to how often you can really publish | `/yt-plan 3 Shorts a week and 1 long video a month` |

When a script is ready, stage it in `shorts/stories.json` or `longform/videos.json`, then run the self-check
(`python shorts/test_shorts.py` or `python longform/test_long.py`) before pushing.

## 2. Packaging each upload

The long videos already come with a description, chapter timestamps and a thumbnail (`<id>.txt`, `<id>.jpg` in
the Release). These skills check and sharpen them.

| Skill | Use it for | Example |
|---|---|---|
| `/yt-package` | Title and thumbnail text as one pairing, checked for truncation, duplication and vagueness | `/yt-package The Prayers of Jesus, 10 min, Gethsemane and the Lord's Prayer` |
| `/yt-seo` | The description and tags, written for what people actually search ("prayer before sleep", "lord's prayer explained") | paste the generated `<id>.txt` |
| `/yt-chapters` | Checking the chapter timestamps against YouTube's rules so they render (first at 0:00, at least 3, each 10 s or longer) | paste the `Chapters` block |

## 3. After publishing

| Skill | Use it for | Example |
|---|---|---|
| `/yt-retention` | Reading a YouTube Studio retention export and finding where viewers leave, then fixing it in the script or pacing (`LEAD`/`TAIL` in the builders) | paste the retention CSV |
| `/yt-audit` | A whole-channel review: packaging, consistency, the first 15 seconds, and what to fix first | your channel URL |
| `/yt-comment` | Replies to comments in your voice, triaged by which ones are worth answering | paste a comment thread |

## 4. Keeping the code healthy

| Skill | Use it for |
|---|---|
| `/code-review` | Review your changes for bugs before you push (renders cost a cloud run, so catch mistakes first) |
| `/ecc:python-review` | Python-specific review of `build_short.py`, `build_long.py`, `kit.py`, `lineart.py` |
| `/ponytail` | Keep changes small: the simplest fix that works, no new dependencies (already installed) |
| `/ecc:verification-loop` | A full check (tests, lint, diff review) before a release |
| `/ecc:github-ops` | Workflow runs, failed jobs, releases and artifacts on GitHub |
| `/ecc:security-review` | Check the workflows before making changes to permissions or secrets |

## 5. Automating the routine

| Skill | Use it for | Example |
|---|---|---|
| `/schedule` | A cloud routine that runs on a timetable, for example a weekly check that the newest Release rendered, or drafting next week's scripts | `/schedule every Monday, list the newest shorts-N and long-N releases and flag failed runs` |

## Workflow in one line each

- **New Short:** `/yt-script` → add to `shorts/stories.json` → `python shorts/test_shorts.py` → id in `shorts/render.txt` → push → download from the `shorts-N` Release → `/yt-package`.
- **New long video:** `/yt-script` per chapter → add to `longform/videos.json` with a new template → `python longform/test_long.py` → id in `longform/render.txt` → push → download from the `long-N` Release → `/yt-chapters`, `/yt-seo`.
- **Monthly:** `/yt-retention` on the last uploads, `/yt-audit` on the channel, `/yt-plan` for the next month.

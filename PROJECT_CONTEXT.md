# coimbatore360-autopost - project context

Automatic Coimbatore-district news reels for the Instagram page **கோயம்புத்தூர் 360** (`@coimbatore360.official`, placeholder; hashtag `#Coimbatore360`;
`post_to` value in the Sheet: `Coimbatore 360`). A separate, fully independent copy of the Namakkal project `news360-autopost`:
own GitHub repository, own Google account / Sheet / Apps Script, own Instagram token, own Cloudinary account and own free API keys.
Namakkal 360 / Rasipuram 360 are never touched. Same file structure and function names as Namakkal, so Namakkal fixes can be
ported by diff. Everything runs on GitHub Actions; the Google Sheet (through the Apps Script bridge) is the working store.

**Status: not live** (no `LIVE` file, no `research_free/ENABLED`). See the owner setup checklist in `README.md`.

## How it works (end to end)

```
every 2 h    research_free.yml  collect news (newspaper sites incl. Dinamalar Coimbatore page, Google/Bing News, Coimbatore searches)
                                 -> open + check each article -> only Coimbatore-district news of today/yesterday
                                 -> queue by priority (research_free/archive/queue.json)
every 20 min write_stories.yml  write each queued news by priority (free LLM chain only) -> ONE AI image of the main scene
                                 (Cloudflare FLUX schnell -> NVIDIA FLUX -> paid FAL only if both fail) -> story saved in the Sheet
                                 -> starts posting at once
every 5 min  post.yml           checks (Coimbatore only, not stale, no duplicate, daily cap 50; posts at once) -> reel (reel/reel4.py,
                                 Valluvar voice) -> Instagram (one page, no collab)
daily        insights.yml       Instagram insights -> learned topic weights (writer priority)
```

## Rules the owner decided (keep them)

| Area | Rule |
|---|---|
| News scope | Only Coimbatore-district news, published today or yesterday (Coimbatore city, Pollachi, Mettupalayam, Sulur, Annur, Valparai, Kinathukadavu, Madukkarai, Perur, Thondamuthur, Anaimalai, Karamadai ...). Tiruppur, Nilgiris, Erode, Palakkad and every other district are not ours, even when close. "Avinashi Road" is a Coimbatore city road: a headline that also names a Coimbatore place is ours |
| One page | Only கோயம்புத்தூர் 360. No second page, no collaborator, no Rasipuram routing |
| Priority | owner 27 Nov: by this page's Instagram views per topic (research_free/learned.json); urgent = an upcoming power cut (first) or a topic whose reels often pass 10,000 views (1 in 5) |
| Never miss news | Everything eligible is queued and written; duplicates and other-district news are skipped; nothing eligible is dropped |
| Daily cap | owner 27 Nov: 30 news a day per page on Instagram, Facebook and YouTube each (IST day; rasipalan / gold rate extra); after 30 only urgent news |
| YouTube hashtags | owner 28 Nov: 40 hashtags on every YouTube Short (YouTube allows 60) - 25 for the video (from its own keyword line; sensitive news gets general tags only), 5 for the page, 5 for the district, 5 for the area of the news (poster/yt_hashtags.py). The first line stays `#<Page> #TamilNews #Shorts`; title, hidden Tags, Instagram and Facebook are not changed. Switch off: config.json `"youtube_hashtags": false` |
| Add news (backend) | owner 28 Nov: a news typed in the News360 Backend ("Add news": content, extra details, follow-up of an earlier post, link, picture, note with extra instructions) is taken within 5-10 minutes (research_free/backend_news.py, backend_news.yml), written by the usual writer chain, and posted on Instagram, Facebook and YouTube through every usual check. Only the logins in the store setting DASH_POSTERS may add news. A follow-up is never held as a duplicate of the news it continues; the owner's own words are not fact-checked against a link |
| Posting time | owner 27 Nov: 06:00-22:00 IST every reel posts as soon as it is ready; 22:00-06:00 only urgent news. News is collected every 2 hours |
| Errors and blocks | owner 27 Nov: after an error 5 tries 10 minutes apart, then 1 try 1 hour later, then Hold - never retried at once; a temporary block waits the time the platform states, else 2 hours (owner 28 Nov: a Facebook block with no stated time waits 24 hours - retrying every 2 hours kept five pages blocked). No manual work for the owner (config.json owner_emails false) |
| Format | Reel only (no carousel) |
| Voice | **Valluvar only** (free edge-tts `ta-IN-ValluvarNeural`). Google voices are never used, even if a Google key exists |
| Follow line | Spoken: மேலும் செய்திகளுக்கு கோயம்புத்தூர் த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள். Caption: கோயம்புத்தூர் செய்திகளைத் தவறவிடாமல் இருக்க Save செய்து Follow செய்யுங்கள் 📌 |
| Images | ONE new photo-realistic AI image per reel (main scene of THIS news, no text/logos); the reel uses different camera moves / crops of it. Free first: Cloudflare FLUX schnell -> NVIDIA FLUX; paid FAL `flux/schnell` -> `flux/dev` only as the last fallback. Picture check (free Gemini) as in Namakkal |
| Writing | Free LLM chain only; Claude backup OFF (`CLAUDE_MAX_CALLS=0`, no `ANTHROPIC_API_KEY`) |
| Reel language | Formal news Tamil, no slang; everyday Tamil Nadu words in voice, subtitles and cards (பஸ், டூவீலர், போலீசார், கலெக்டர் ...); dates always with the month |
| Website | Off for now (later). `poster/website.py` does nothing without `WEBSITE_INGEST_KEY`; workflows do not pass it |
| Separation | Own accounts and keys, so Namakkal's free API limits are never used; bridge e-mails tagged `COIMBATORE360` |
| Privacy | Personal project; bot commits as `news360-bot`; no office account, office email or Claude lines in commits |

## Main files

| Path | What |
|---|---|
| `research_free/collect.py`, `allnews.py`, `sources.py` | collection, Coimbatore district checks, queue, writer, image |
| `research_free/rules.md`, `examples.json`, `names.py` | writing rules and spoken-word fixes |
| `poster/post.py` | posting checks, prime time, daily cap, Instagram publishing |
| `poster/freshness.py` | stale / duplicate / power-cut timing rules |
| `poster/config.json` | voice (Valluvar), prime time, design switches |
| `reel/reel4.py` | reel renderer (one image, camera moves, voice, opening, dates) |
| `apps_script/Code.gs` | Google Sheet bridge for the Coimbatore 360 account (set the `..._HERE` values; redeploy after changes) |
| `tests/test_regressions.py` | regression tests (run before every push) |

## Sheet bridge (apps_script/Code.gs)

- Page key `coimbatore`, label `கோயம்புத்தூர் 360`, `post_to` `Coimbatore 360`, token property `IG_TOKEN_COIMBATORE` (refreshed weekly).
- Columns: same 31 as Namakkal; column 25 `spare_link` (unused), column 26 `coimbatore_link` (carousel link, unused while reel only),
  27 `reel_link`.
- GET actions: `queue`, `posted_rows`, `token`, `voice`, `recent`, `ping`, `autoPending`.
  POST actions: `posted`, `error`, `addStories`, `archiveNews`, `reoffer`, `setImages`, `repost`.
- E-mail subjects: `COIMBATORE360 STORY`, `COIMBATORE360 REEL`, `[COIMBATORE360 IMAGES NEEDED]` ...

## Secrets (GitHub -> Settings -> Secrets -> Actions; values never in the repo)

BRIDGE_URL, BRIDGE_KEY, GEMINI_API_KEY, GROQ_API_KEY, NVIDIA_API_KEY, CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID,
CLOUDINARY_CLOUD, CLOUDINARY_PRESET; optional MISTRAL_API_KEY, OPENROUTER_API_KEY, GH_MODELS_TOKEN, FAL_KEY (paid image fallback).
Not used: ANTHROPIC_API_KEY, GOOGLE_TTS_API_KEY, WEBSITE_INGEST_KEY. Local copies live only in `.env` (git-ignored).

## Run and check

```
python3 -m unittest discover -s tests        # regression tests (also run by tests.yml on every code push)
python3 tools/repost.py RN-158               # (Actions: repost) post a reel again after it was removed from Instagram
```

## Recent changes
<!-- recent-changes:start (updated automatically by .github/workflows/context.yml - do not edit by hand) -->
| Date | Commit | Change |
|---|---|---|
| 2026-11-28 | `2d2af53` | Facebook: a block with no stated time waits 24 hours again (owner 28 Nov) - with 2 hours five pages retried every 2 hours, were refused each time (368) and stayed blocked |
| 2026-11-28 | `74ab590` | stories shared / Instagram pause |
| 2026-11-28 | `955f085` | stories shared / Instagram pause |
| 2026-11-28 | `c9af96d` | stories shared / Instagram pause |
| 2026-11-28 | `f144bd9` | stories shared / Instagram pause |
| 2026-11-28 | `81c1684` | stories shared / Instagram pause |
| 2026-11-28 | `265df9e` | stories shared / Instagram pause |
| 2026-11-28 | `97298f0` | stories shared / Instagram pause |
| 2026-11-28 | `f06116e` | stories shared / Instagram pause |
| 2026-11-28 | `7a38fc1` | stories shared / Instagram pause |
| 2026-11-28 | `392266e` | stories shared / Instagram pause |
| 2026-11-28 | `43c61a7` | stories shared / Instagram pause |
| 2026-11-28 | `2fe1124` | stories shared / Instagram pause |
| 2026-11-28 | `d974633` | pick: written and posted |
| 2026-11-28 | `a40294e` | stories shared / Instagram pause |
| 2026-11-28 | `f6ca26b` | facebook RN-793 |
| 2026-11-28 | `b935bd2` | posted RN-793 |
| 2026-11-28 | `db2bd72` | stories shared / Instagram pause |
| 2026-11-28 | `f1bc9c7` | stories shared / Instagram pause |
| 2026-11-28 | `3a8a5a9` | facebook RN-794 |
| 2026-11-28 | `829cc1d` | posted RN-794 |
| 2026-11-28 | `fdf7180` | stories shared / Instagram pause |
| 2026-11-28 | `4e7e567` | pick: picked news saved |
| 2026-11-28 | `845bbba` | stories shared / Instagram pause |
| 2026-11-28 | `33adb32` | pick: picked news saved |
| 2026-11-28 | `79a6d41` | pick: list sent |
| 2026-11-28 | `36bfcc7` | stories shared / Instagram pause |
| 2026-11-28 | `88b8365` | stories shared / Instagram pause |
| 2026-11-28 | `85171c3` | stories shared / Instagram pause |
| 2026-11-28 | `2133fe9` | stories shared / Instagram pause |
<!-- recent-changes:end -->

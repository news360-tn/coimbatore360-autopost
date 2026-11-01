# coimbatore360-autopost - project context

Automatic Coimbatore-district news reels for the Instagram page **கோயம்புத்தூர் 360** (`@coimbatore360_official`, placeholder; hashtag `#Coimbatore360`;
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
| Priority | power cut (TNEB) > crime > accident > civic > the rest |
| Never miss news | Everything eligible is queued and written; duplicates and other-district news are skipped; nothing eligible is dropped |
| Daily cap | 50 reels a day (Instagram's limit) (`DAILY_CAP` in post.yml, also in the collector / writer); urgent news first |
| Posting time | No fixed times (owner 29 Oct): every reel posts the moment it is made (`poster/config.json` `prime_time.enabled: false`) |
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
| 2026-11-01 | `f51c1b8` | the fact-check / location hold also applies to owner ready reels (they skipped every news check before); RN-272 repost path |
| 2026-11-01 | `f26a4d8` | writer must name the town or village from the article in location (a district alone is not allowed); a story whose location is only the district is held from posting (RN-272) |
| 2026-11-01 | `1fa9d2b` | hold a story from posting when its fact-check found any problem or its location is unknown (RN-272); the verification label now shows the real check result instead of a fixed 'not checked by Claude yet' |
| 2026-11-01 | `7d4ef29` | pick: written and posted |
| 2026-11-01 | `32025f6` | pick: the evening round is the latest round (text sort put 'evening' before 'morning' - the 4 PM ticks were ignored); resume input to decide the latest round again |
| 2026-11-01 | `d54f494` | pick: written and posted |
| 2026-11-01 | `1bc2bec` | pick: list sent |
| 2026-11-01 | `f981a49` | rasipalan: திதி / நட்சத்திரம் / யோகம் as Maalaimalar's daily panchangam (Vakya) prints them; own calculation only when not found |
| 2026-11-01 | `40389cf` | stories shared |
| 2026-11-01 | `26b3a7e` | story catch-up: a post shared once is remembered (poster/story_shared.json) - the rasipalan got a 2nd story |
| 2026-11-01 | `b744fc1` | story catch-up: video re-hosted on Cloudinary first (Instagram refused its own CDN link: container ERROR); tries capped per run |
| 2026-11-01 | `918b22b` | story catch-up: a post's owner id is the account's app id - every post was taken for the other page's collab |
| 2026-11-01 | `f9384a2` | story catch-up: log quota / posts / stories seen |
| 2026-11-01 | `a7a2ed2` | stories: every post (news reel, carousel, rasipalan, any job) also goes to the story - fixed 25-post cut removed, missing stories caught up every run, last 5 of the 50/day kept for news |
| 2026-11-01 | `4802cdf` | powercut: log the title of a power cut skipped as another district |
| 2026-11-01 | `7244f7a` | powercut: search results kept only when the headline is a power cut (first run took 20+ min resolving every result); self-contained module |
| 2026-11-01 | `125329d` | powercut: Coimbatore power-shutdown notices posted at once without a tick - hourly, Dinamani + Dinamalar (+ Covai Mail backup), never twice, never late, fails loudly if not posted |
| 2026-11-01 | `099c2fc` | pick: start the posting job for REAL (dry_run=false) - a manual post.yml start defaults to test |
| 2026-11-01 | `c22dbac` | pick: end-to-end guard - every ticked news must be POSTED: posting starts at once, verify every 5 min for 1 h, then fail loudly; end-to-end test |
| 2026-11-01 | `b52de74` | post: news the owner ticked in the pick form is always posted - no 'stale' hold (7 of 12 were held on 1 Nov) |
| 2026-11-01 | `dd53944` | pick: written and posted |
| 2026-11-01 | `8295eba` | pick: a leftover from another district (Puducherry story) is dropped, not listed again |
| 2026-11-01 | `719440c` | rasipalan posted |
| 2026-11-01 | `3a2a758` | rasipalan writer: 5 tries, best draft kept, only the lines still wrong are replaced (1 Nov Coimbatore repost failed over 1 line) |
| 2026-11-01 | `e93a9f5` | rasipalan: repost input - post today again once the old post is deleted |
| 2026-11-01 | `ce26223` | rasipalan: நல்ல நேரம், சூலம் (+பரிகாரம்), சுபமுகூர்த்த நாள் on the panchangam slide and caption; ஞாயிற்றுக்கிழமை spelling; overlap check |
| 2026-11-01 | `86e7929` | voice: no dash ever reaches the voice - 'சேலம் - நாமக்கல்' was read as minus (RN-256); routes read முதல் ... வரை |
| 2026-11-01 | `ff7d052` | rasipalan posted |
| 2026-11-01 | `490d2d3` | rasipalan: never miss a day - 1 source enough after 9:30, keep trying until 12:30, backups 9:45 and 11:45 |
| 2026-11-01 | `ac85e79` | rasipalan: find today's article when the day is written 01 or the link has no date (1 Nov nothing posted) |
<!-- recent-changes:end -->

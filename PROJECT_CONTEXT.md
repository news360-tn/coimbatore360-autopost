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
| 2026-10-29 | `dbb6967` | Coimbatore: news collected only from Tamil-language websites of Tamil Nadu newspapers and channels (English and foreign outlets removed and filtered out) |
| 2026-10-29 | `baea4a0` | Coimbatore workflows: newest Haiku (claude-haiku-5-5) |
| 2026-10-29 | `84aab54` | Newest Haiku (claude-haiku-5-5) for Claude calls, older Haiku only if the name is ever refused; news only from Tamil-language articles |
| 2026-10-29 | `1a53394` | Letters of another script inside Tamil words are repaired (voice and cards), flagged for rewrite, and cleaned in captions (Coimbatore RN-5, 7, 20, 22) |
| 2026-10-29 | `cc7d734` | No made-up or empty stories (from Namakkal d24107f + b4f47be): skip headline-only pages, never file a draft mostly not grounded in its Tamil article, never file/post a story that only says the article has no details (RN-12 K.N. Nehru raid) |
| 2026-10-29 | `ab700c1` | Coimbatore: refuse Tamil text with letters of another script (RN-20 headline had Chinese/Korean/Bengali letters) |
| 2026-10-29 | `d788969` | Coimbatore: city rule checked again right after writing with the writer's location (RN-2 Valparai was written, then blocked at posting); proofread never turns a verb into another word (RN-1 நிர்வாகிக்க -> நிர்வாகம்) |
| 2026-10-29 | `28c447a` | Coimbatore: a script that talks about 'the article' / 'no information' instead of the news is refused (Namakkal RN-189 case, deleted by the owner) |
| 2026-10-29 | `96505b2` | Coimbatore writing (owner): ALL free models first on every call (Gemini, GitHub Models, Groq, Cloudflare); paid Claude Haiku 4.5 only when every free one failed or is out of quota; fixed Claude model id (claude-haiku-5-5 does not exist) |
| 2026-10-29 | `e4228e5` | Coimbatore 360 LIVE (owner): LIVE + collect switch on, news from today 00:00 IST, dry-run queue/state cleared |
| 2026-10-29 | `7150e45` | Coimbatore image prompt (owner): detailed city scene of THIS news first (subject+action, place, people, vehicles/objects, light, camera; 3+ article facts, 100-150 words), Coimbatore city look and category guide; a generic or short scene is sent back once |
| 2026-10-29 | `b4c10d3` | Coimbatore (owner): collect every 2 hours, post at once, do not miss city news - cap 50 (Instagram's limit), news from the last 3 h still taken after midnight, watchdog restarts a collect late by 2 h 15 min |
| 2026-10-29 | `437918c` | Coimbatore: no fixed posting times - every reel posts the moment it is made (prime time off) |
| 2026-10-29 | `5d9697a` | Coimbatore priority (owner): power cut > crime > accident > civic > the rest; collect only news published TODAY |
| 2026-10-29 | `9eef430` | Coimbatore CITY only for now (owner): towns outside the city skipped at collecting, writing and posting unless a city area is named; town searches not run; CITY_ONLY=0 covers the whole district later |
| 2026-10-29 | `2a0cc5b` | free-model test output |
| 2026-10-29 | `42ba0ef` | research-free-test: same free writing chain as the writer (GitHub Models, Cloudflare) |
| 2026-10-29 | `e2d6460` | Coimbatore pictures (owner, final): free first (Cloudflare, NVIDIA), FAL schnell/dev only when no free source made one, plain branded background only if FAL fails too; Gemini image off (free tier quota 0) |
| 2026-10-29 | `426b4c2` | free-model test output |
| 2026-10-29 | `0f2cb04` | image test output |
| 2026-10-29 | `d2f4ec8` | free-model test output |
| 2026-10-29 | `eac502a` | Coimbatore: free pictures only (Cloudflare, Gemini, NVIDIA) - never FAL; no free picture after 30 min -> plain background with the page logo; FAL key no longer passed to any workflow |
| 2026-10-29 | `358c0e1` | image test output |
| 2026-10-29 | `c067fed` | Images free first: Cloudflare -> Gemini image (free tier) -> NVIDIA schnell/dev -> only then FAL schnell/dev; every prompt asks for no text/logos; Cloudflare daily-limit not retried per picture; NVIDIA models that answer 404 removed |
| 2026-10-29 | `b979441` | image test output |
| 2026-10-29 | `4a75089` | free-model test output |
| 2026-10-29 | `05feb55` | Bridge: Coimbatore Cloudinary cloud (own account, unsigned preset coimbatore360) |
| 2026-10-28 | `7bbcf3a` | Instagram handle is coimbatore360_official (underscore, as Instagram reports it) |
| 2026-10-28 | `7d5006f` | ig probe output |
| 2026-10-28 | `e12dfef` | ig-probe: never write the Instagram token or bridge key into the public repo (error messages can carry the request URL) |
<!-- recent-changes:end -->

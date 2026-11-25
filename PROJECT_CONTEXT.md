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
| 2026-11-25 | `6777ba3` | YouTube: upload only when the login's channel is this page's (verify_channel on Erode, Karur, Salem, Tiruppur, Trichy - their Shorts went to the Namakkal channel) |
| 2026-11-25 | `edcdf2d` | stories shared / Instagram pause |
| 2026-11-25 | `2b4b6c7` | stories shared / Instagram pause |
| 2026-11-25 | `e213dfa` | stories shared / Instagram pause |
| 2026-11-25 | `3bb3bb9` | stories shared / Instagram pause |
| 2026-11-25 | `16859cc` | stories shared / Instagram pause |
| 2026-11-25 | `0634411` | stories shared / Instagram pause |
| 2026-11-25 | `07f1d35` | stories shared / Instagram pause |
| 2026-11-25 | `997f63f` | pick: written and posted |
| 2026-11-25 | `ca56684` | facebook RN-696 |
| 2026-11-25 | `c2bfc68` | posted RN-696 |
| 2026-11-25 | `b3f56e9` | stories shared / Instagram pause |
| 2026-11-25 | `5368199` | pick: picked news saved |
| 2026-11-25 | `45198da` | stories shared / Instagram pause |
| 2026-11-25 | `2f0bc59` | pick: picked news saved |
| 2026-11-25 | `1203959` | pick: list sent |
| 2026-11-25 | `e5982f4` | pick: written and posted |
| 2026-11-25 | `7bbe5a4` | facebook RN-694 |
| 2026-11-25 | `31bb332` | posted RN-694 |
| 2026-11-25 | `5998a90` | stories shared / Instagram pause |
| 2026-11-25 | `2a5f9c8` | stories shared / Instagram pause |
| 2026-11-25 | `1687aca` | facebook RN-693 |
| 2026-11-25 | `9389a24` | posted RN-693 |
| 2026-11-25 | `a5a0bfa` | YouTube: first comment (the Instagram source comment) and topic playlists after each upload - start once the channel login has the youtube.force-ssl permission; skipped quietly until then |
| 2026-11-25 | `aae8dc4` | Platform text: Facebook news caption short (headline + 3 lines + source) with the Tamil district tag; YouTube title ~70 chars with an English search word, 3 hashtags first, Subscribe line, Tamil language |
| 2026-11-25 | `7ca0287` | YouTube: the Instagram source comment (source + link) at the top of each Short's description |
| 2026-11-25 | `9926c29` | stories shared / Instagram pause |
| 2026-11-25 | `9fd5c75` | goldrate posted |
| 2026-11-25 | `f1365af` | After a posting error wait 10 minutes before the next try (Instagram, Facebook, YouTube); YouTube and Facebook 20 a day; rasipalan and gold rate on YouTube too, first, outside the 20 |
| 2026-11-25 | `72cfe20` | pick: picked news saved |
<!-- recent-changes:end -->

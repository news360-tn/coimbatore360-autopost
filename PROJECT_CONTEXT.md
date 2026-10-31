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
| 2026-10-31 | `ecbb9d2` | test: today-only freshness check no longer fails every night 00:00-02:00 IST (matches the owner's FRESH_HOURS 0 rule) |
| 2026-10-31 | `d480193` | rasipalan: proofreader may only fix sandhi/spacing (never a changed letter); TV9 'மேஷ ராசி' headings read |
| 2026-10-31 | `cf77638` | rasipalan: test runs keep the slides and log on a preview branch |
| 2026-10-31 | `9034b5d` | Daily rasipalan carousel for Coimbatore 360 (7:31 AM, Tamil daily-calendar design, festival themes) |
| 2026-10-31 | `299d7eb` | Heartbeat |
| 2026-10-31 | `bfe422a` | Real photos: one Gemini 'too many requests' (429) stops the photo check for 30 min - the free quota stays for the writer (owner 31 Oct) |
| 2026-10-31 | `bb85c5f` | Headline-only pages are never written; one prison escape is one event; 'details not yet known' scripts are not news (owner 31 Oct) |
| 2026-10-31 | `47f461e` | Coimbatore: a wall / building collapse is an incident (the same event from two outlets is not posted twice) (owner 31 Oct) |
| 2026-10-31 | `27811da` | Real news photos: only our page's branding - source watermarks / channel logos removed, no source credit (owner 31 Oct) |
| 2026-10-31 | `0429960` | Real news photos: the source article's own photo is used when it shows this news, enhanced to a presentable picture; else AI pictures (owner 31 Oct) |
| 2026-10-31 | `a5ec073` | Coimbatore: each round's top 3 only from power cut / rain / crime / accident, Coimbatore-district news only; repeats never posted (owner 31 Oct) |
| 2026-10-31 | `1b1521e` | Coimbatore: no daily limit - every 2-hour round posts its top 3 (only Instagram's 50 a day applies); a round keeps trying until 3 are written |
| 2026-10-31 | `466a2bb` | The same event is never posted twice: incidents matched by name / distinctive number; round-mates checked (owner 31 Oct) |
| 2026-10-31 | `e6a1029` | Location tags: only ids Instagram accepts are used; ig-probe checks them (owner 31 Oct) |
| 2026-10-31 | `ea88c0c` | 10 rounds a day, top 3 of the whole district each; fix the posting watchdog (owner 31 Oct) |
| 2026-10-31 | `d25783f` | Only news Instagram users watch is written; collection every 4 hours (owner 31 Oct) |
| 2026-10-30 | `f40cfc4` | Heartbeat |
| 2026-10-30 | `9578ca7` | Refused stories are not written again and again (owner 30 Oct) |
| 2026-10-30 | `3a52ae7` | Power cuts never missed, never reposted (owner 30 Oct) |
| 2026-10-30 | `fb188b1` | Same event from two outlets in one writer round is caught (stories filed this round join the check), and short reports of one event count as the same (RN-214 = RN-209) |
| 2026-10-30 | `b17f80e` | Writer/collector: the Sheet bridge is tried 3 times when Apps Script does not answer (writer crashed once at 09:00 UTC 30 Oct on a 120 s timeout) |
| 2026-10-30 | `ee7ce70` | Sarvam out of the live writer order until writer-compare proves it |
| 2026-10-30 | `bea20ac` | Sarvam: reasoning low (API accepts low/medium/high only) |
| 2026-10-30 | `325ffed` | Sarvam: thinking off, bigger answer budget; empty answers logged with the reason |
| 2026-10-30 | `799fd5e` | Remove Cerebras writer: it now needs a card (paid after $5 trial) |
| 2026-10-30 | `fc91049` | Free writers: Gemini 3.6/3.5 first, Sarvam + Cerebras (skipped until keys), Gemma ready (off), Groq short retry on 413; remove GitHub Models, Mistral, OpenRouter, NVIDIA text; writer-compare test workflow |
| 2026-10-30 | `acfe77d` | SiliconFlow removed (owner): not free for this account ('balance insufficient'); picture order Cloudflare -> Pollinations -> NVIDIA -> FAL |
| 2026-10-30 | `c28740a` | image test output |
| 2026-10-30 | `8540ebc` | imagegen-test: each free picture service tested on its own (Cloudflare, SiliconFlow, Pollinations, NVIDIA) - nothing posted |
| 2026-10-30 | `3729cb8` | Free pictures first (owner 30 Oct): Cloudflare kept for pictures (not writing, 4 steps = ~230 free pictures/day) -> SiliconFlow free FLUX -> Together free FLUX -> Pollinations -> NVIDIA -> FAL only when all fail (each new service skipped until its key is set); 2 news-specific pictures per reel on every page (cover = main event, 2nd = detail); the cover is kept if the 2nd picture fails; switches in config.json free_images |
<!-- recent-changes:end -->

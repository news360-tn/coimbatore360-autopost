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
| 2026-10-30 | `ee7ce70` | Sarvam out of the live writer order until writer-compare proves it |
| 2026-10-30 | `bea20ac` | Sarvam: reasoning low (API accepts low/medium/high only) |
| 2026-10-30 | `325ffed` | Sarvam: thinking off, bigger answer budget; empty answers logged with the reason |
| 2026-10-30 | `799fd5e` | Remove Cerebras writer: it now needs a card (paid after $5 trial) |
| 2026-10-30 | `fc91049` | Free writers: Gemini 3.6/3.5 first, Sarvam + Cerebras (skipped until keys), Gemma ready (off), Groq short retry on 413; remove GitHub Models, Mistral, OpenRouter, NVIDIA text; writer-compare test workflow |
| 2026-10-30 | `acfe77d` | SiliconFlow removed (owner): not free for this account ('balance insufficient'); picture order Cloudflare -> Pollinations -> NVIDIA -> FAL |
| 2026-10-30 | `c28740a` | image test output |
| 2026-10-30 | `8540ebc` | imagegen-test: each free picture service tested on its own (Cloudflare, SiliconFlow, Pollinations, NVIDIA) - nothing posted |
| 2026-10-30 | `3729cb8` | Free pictures first (owner 30 Oct): Cloudflare kept for pictures (not writing, 4 steps = ~230 free pictures/day) -> SiliconFlow free FLUX -> Together free FLUX -> Pollinations -> NVIDIA -> FAL only when all fail (each new service skipped until its key is set); 2 news-specific pictures per reel on every page (cover = main event, 2nd = detail); the cover is kept if the 2nd picture fails; switches in config.json free_images |
| 2026-10-30 | `9943e0e` | Code bugs never repeat (owner): tests fail on any undefined name in poster/research_free/reel (pyflakes on GitHub - would have stopped the 29 Oct 'verify' posting crash) and run the caption + posting-check steps end to end on a sample story |
| 2026-10-30 | `b2a800d` | Known issues are repaired, not lost (owner): a card cut mid-phrase, a sentence or word said twice, a sentence about 'the article' are fixed before posting; only what cannot be fixed is held (RN-199, RN-203 held for a cut card); repeated-sentence check no longer splits at 'ரூ.2.50' / 'ஹெச்.பி.' (RN-200 false alarm) |
| 2026-10-29 | `74ab3ce` | Heartbeat |
| 2026-10-29 | `0807636` | Coimbatore (owner): power-cut news from the WHOLE district (every town searched for its shutdown notice, never blocked by the city filter); all other news stays city only; power cut stays first priority |
| 2026-10-29 | `5d59cf1` | Caption holds ALL the news (owner): every number, date, age, amount and place in the article sentences about this story must be in the caption, else the writer adds it (RN-175, 178, 181, 185, 186 missed one); other headlines on the page and datelines ignored; never drops a story; switch reach.caption_all_facts |
| 2026-10-29 | `3f6b7de` | English search line never cut in the middle of a word |
| 2026-10-29 | `c546c12` | Coimbatore reach plan (owner): reels at most 60 s (70-105 words, key facts once; every detail stays in the caption's full-details block, checked at writing), English search line added at posting, 5 focused hashtags (page + district + area + topic + broad, junk tags dropped), no brand names/logos in pictures, location tags on; all behind poster/config.json reach switches |
| 2026-10-29 | `da1b5f9` | Known issues never repeat (owner): one list (research_free/known_issues.py) checked when a story is written AND right before posting - script about the article, letters of another script (repaired first), English words the voice skips, card cut mid-phrase, words said twice; every entry has a real bad and good example run by the tests |
| 2026-10-29 | `849f93c` | Coimbatore quality check (owner): card lines never cut mid-phrase (RN-34), English words in the voice script sent back - the voice drops them (RN-34), state-wide stories not written or posted (RN-8 TNEB, RN-20 prisons) |
| 2026-10-29 | `7201ad8` | Fix: every post job crashed with NameError (verify not imported in clean_caption) since 13:00 UTC 29 Oct |
| 2026-10-29 | `51b8910` | Topic / tag / author / page-N listing pages are never written or posted as a news story (RN-194: abplive topic page gave a Cuddalore story) |
| 2026-10-29 | `1643d19` | Writer started by the collector waits for the queue instead of skipping; same event from another outlet is not written again |
| 2026-10-29 | `7e526c7` | Coimbatore: only news PUBLISHED TODAY (IST) is written and posted - the article must show today's date, no late-night carry-over, posting gate today only; publish times read in IST |
| 2026-10-29 | `204b989` | Collection is never cancelled by the story writer: each has its own queue; the collector waits while a writer runs, the writer skips its round while a collection runs (Coimbatore lost 2 collections on 29 Oct) |
| 2026-10-29 | `609e1c8` | Coimbatore: collect only from the 13 researched outlets (Dinamalar, Dinamani, Covai Mail, Arasiyal Today, Dinakaran, Daily Thanthi, Maalaimalar, Thanthi TV, Hindu Tamil, Polimer, Malai Murasu, News18 Tamil, Indian Express Tamil) |
| 2026-10-29 | `06baa10` | No old events and no same-event repeats: an old event re-told in a new article is not filed or posted (Coimbatore RN-29); the same event from another outlet in other words is not posted twice (RN-13/24, RN-86/115) |
| 2026-10-28 | `779647f` | Reel longer than 90 s: shorten the script automatically and render again instead of holding the story (RN-153) |
| 2026-10-29 | `5f4b464` | Font check optional: the writer and test runner have no fontTools, so letter repair still runs and tests pass on GitHub (Python 3.11) |
| 2026-10-29 | `dbb6967` | Coimbatore: news collected only from Tamil-language websites of Tamil Nadu newspapers and channels (English and foreign outlets removed and filtered out) |
| 2026-10-29 | `baea4a0` | Coimbatore workflows: newest Haiku (claude-haiku-5-5) |
| 2026-10-29 | `84aab54` | Newest Haiku (claude-haiku-5-5) for Claude calls, older Haiku only if the name is ever refused; news only from Tamil-language articles |
<!-- recent-changes:end -->

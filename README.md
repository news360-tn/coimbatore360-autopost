# Coimbatore 360 – கோயம்புத்தூர் 360 auto-posting


> **Now: Coimbatore CITY only** (owner 29 Oct). Stories about towns outside the city (Pollachi, Mettupalayam, Sulur, Annur, Valparai ...) are skipped. To cover the whole district later, set `CITY_ONLY: "0"` in `.github/workflows/research_free.yml`, `write_stories.yml` and `post.yml`.

Automatic Coimbatore-district news reels for the Instagram page **கோயம்புத்தூர் 360** (`@coimbatore360_official`, hashtag `#Coimbatore360`).
This is a separate copy of the Namakkal project (`news360-autopost`): its own GitHub repository, its own Google account,
Sheet and Apps Script, its own Instagram token, Cloudinary account and free API keys. Nothing here touches Namakkal 360.
Everything runs on GitHub Actions; the Google Sheet (through the Apps Script bridge) is the working store.
Owner rules, main files and recent changes: see `PROJECT_CONTEXT.md`.

**Status: not live.** There is no `LIVE` file and no `research_free/ENABLED` file, so nothing is collected or posted
until the owner finishes the setup checklist below.

## How a story gets from news to Instagram

```
research_free.yml (every 4 h) -> queue.json -> write_stories.yml (every 20 min) -> Google Sheet -> post.yml (every 5 min) -> Instagram
                                                                                                        ^
                                                                    insights.yml (daily) -> topic weights for the writer
```

1. **Collect** (`.github/workflows/research_free.yml`, every 4 hours at :07, `research_free/collect.py`).
   Searches newspaper sites (Dinamalar Coimbatore district page and others) and Google/Bing News, opens and checks each
   article, keeps only **Coimbatore-district** news of today or yesterday (Tiruppur, Nilgiris, Erode, Palakkad and every
   other district are rejected), removes duplicates and queues the rest by priority in `research_free/archive/queue.json`.
   Priority: **power cut (TNEB) > jobs > accident > crime > weather > the rest.**
   Manual run with `manual_url` = one article link written and posted at once.
2. **Write** (`.github/workflows/write_stories.yml`, every 20 minutes, same `collect.py` in write mode).
   Takes the queue by priority (3 at a time), writes the Tamil headline, caption and reel script with the **free** LLM chain
   only (Claude backup is off: `CLAUDE_MAX_CALLS=0`, no `ANTHROPIC_API_KEY`), makes **one** AI image of the main scene of
   the news (free first: Cloudflare FLUX schnell -> NVIDIA FLUX; paid FAL `flux/schnell` then `flux/dev` only if both free
   sources fail), uploads it to Cloudinary, saves the story in the Sheet and starts the posting job at once.
   After 25 stories in a day (`DAILY_CAP=25`) only the main / important news is written.
3. **Post** (`.github/workflows/post.yml`, every 5 minutes, `poster/post.py`).
   - `check`: reads the Sheet queue and skips stories that are on hold, stale (older than yesterday, finished power cut,
     passed date - `poster/freshness.py`), not Coimbatore-district news, or a duplicate of an already posted story.
     Urgent news goes out at once; other reels are made ahead and posted in prime time (`poster/config.json` `prime_time`,
     never more than 12 h wait). At most 25 reels a day to start with (`DAILY_CAP` in `post.yml`).
     A watchdog restarts the collector or writer if GitHub skipped their schedule.
   - `run`: builds the **reel only** (no carousel) from the one image (different camera moves / crops per scene, headline
     cards, subtitles, logo), voice **Valluvar** (free edge-tts `ta-IN-ValluvarNeural`, never Google), runs the checks
     (`poster/verify.py`) and publishes through the bridge on the one page கோயம்புத்தூர் 360 (no collaborator).
     Finished media is kept in `poster/prebuilt/` so a retry does not rebuild.
4. **Insights** (`.github/workflows/insights.yml`, daily 02:10 IST, `poster/insights.py`): Instagram insights become
   learned topic weights used for the writer's priority.

Website: **off for now** (`poster/website.py` does nothing without `WEBSITE_INGEST_KEY`, and no workflow passes it).

## Switches

| Switch | Effect |
|---|---|
| `research_free/ENABLED` (Actions -> **collect-switch** -> `pause` / `start`) | Automatic collecting and writing on/off. Posting continues |
| `LIVE` file in the repository root | Scheduled posting to Instagram only happens while it exists. Remove it to stop posting |
| Manual run of **Post stories** | Test only by default (`dry_run`); `prebuild` makes every waiting reel now without posting |
| Repository variable `PAUSED` = `true` | Full stop of posting too |

While collecting is paused you can e-mail a story yourself (subject `COIMBATORE360 STORY`, JSON in the body, one image attached) -
see `docs/manual_story_prompt.md`. Posting always runs the duplicate check and the source fact gate first.
All bridge e-mails use the tag **COIMBATORE360** (not NEWS360), so the Namakkal bridge never reads Coimbatore mails.

Repair tools (Actions, run by hand): **repost** (post a removed reel again), **reoffer-stories**, **rewrite**, **audit**,
**website-backfill** (does nothing while the website is off).

## Owner setup checklist (in this order)

1. **Instagram**: create the page (professional / creator account, handle e.g. `coimbatore360_official`), connect it to a Meta developer
   app with Instagram API, and make a long-lived token for it.
2. **New Google account** for Coimbatore 360 (not the Namakkal Gmail). In it:
   - new Google Sheet "Coimbatore 360 Log" with tab `News` and the same 31 columns as Namakkal, where column Y (25) is
     `spare_link` (unused) and column Z (26) is `coimbatore_link`;
   - new Drive folder "Coimbatore 360";
   - new Apps Script project with `apps_script/Code.gs`; set at the top `SHEET_ID`, `ROOT_FOLDER_ID`, `OWNER_EMAIL`,
     `CLOUD_NAME`, `UPLOAD_PRESET` (all marked `..._HERE`);
   - Script properties: `IG_TOKEN_COIMBATORE` (the Instagram token), optional `ALLOWED_SENDERS`; run `setup` once
     (creates `BRIDGE_KEY`, the 5-minute mail trigger and the weekly token refresh); deploy as a web app
     (Execute as: me, Who has access: anyone) and copy its URL.
3. **New free API keys** under the new account, so Namakkal's free limits are never used up: Gemini, Groq, Cloudflare
   Workers AI (token + account id), NVIDIA, and optionally Mistral, OpenRouter, GitHub Models token. FAL key only as the
   paid image fallback (optional).
4. **Cloudinary**: new free account; create an unsigned upload preset; note the cloud name and preset.
5. **GitHub**: new **public** repository (free Actions minutes) with this folder's content.
6. **Secrets** (Settings -> Secrets and variables -> Actions):
   `BRIDGE_URL`, `BRIDGE_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `NVIDIA_API_KEY`, `CLOUDFLARE_API_TOKEN`,
   `CLOUDFLARE_ACCOUNT_ID`, `CLOUDINARY_CLOUD`, `CLOUDINARY_PRESET`, optional `MISTRAL_API_KEY`, `OPENROUTER_API_KEY`,
   `GH_MODELS_TOKEN`, `FAL_KEY`. Not used here: `ANTHROPIC_API_KEY`, `GOOGLE_TTS_API_KEY`, `WEBSITE_INGEST_KEY`.
   Local copies live only in `.env` (git-ignored).
7. Test: Actions -> **ig-probe**, then **Post stories** with `dry_run` on.
8. **Go live**: add an (empty) `LIVE` file to the repository root, then Actions -> **collect-switch** -> `start`.

## Updating the Apps Script (after every change to `apps_script/Code.gs`)
1. Open the Apps Script project (Coimbatore 360 Google account), replace the code with `apps_script/Code.gs`, keep your values
   for `SHEET_ID`, `ROOT_FOLDER_ID`, `OWNER_EMAIL`, `CLOUD_NAME`, `UPLOAD_PRESET`, save.
2. Run the function `setup` once (asks for Gmail permission; creates the 5-minute mail trigger and the weekly token refresh).
3. Deploy -> Manage deployments -> pencil -> Version: New version -> Deploy (the web app URL stays the same).

## Tests

```
python3 -m unittest discover -s tests        # regression tests (also run by tests.yml on every code push)
```

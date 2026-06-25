# Bing Daily Wallpaper Gallery - Skill

## Overview
Automated Bing daily wallpaper gallery generator. Fetches wallpaper data from Bing's official APIs across 11 independent-update markets, deduplicates, and generates a single self-contained HTML file with modern UI.

**v5.4 Features**:
- **Bilingual EN+ZH**: Descriptions and QuickFacts in English and Chinese
- **Triple API strategy**: HPImageArchive (history) + global.bing.com/model (EN desc) + cn.bing.com/model (ZH desc)
- **MyMemory Translation API**: Translates local language content (DE/FR/IT/ES/PT/JA) to English for non-English markets
- **Proper language labels**: Non-English markets show local language name (Deutsch/Français/日本語) instead of "English"
- **Localized Did You Know**: Each language section has its own localized label ("Wussten Sie schon?", "Le saviez-vous ?", etc.)
- **Incremental update**: JSON cache preserves data across runs; only fetches new/updated content each time
- **Smart desc supplement**: Short descriptions (<200 chars) auto-supplemented with Title/Headline from API
- **Text logo**: "Bing Gallery" text-only header (no image dependency)
- **Enhanced back button**: Purple gradient pill button with SVG chevron icon
- **Language labels**: EN (blue), ZH (red), Local (green) on separate lines

## API Endpoints

### 1. Bing Wallpaper Archive API (14-day history + market dedup)
```
https://global.bing.com/HPImageArchive.aspx?format=js&n={n}&idx={offset}&mkt={code}&pid=hp&FORM=BEHPTB&ql=6
```
- Returns: title, caption, copyright, urlbase, desc (varies by market), copyrightlink
- `desc` availability: en-US/en-GB/en-CA/en-IN/de-DE/fr-FR/es-ES/ja-JP have desc; pt-BR/it-IT/zh-CN do NOT

### 2. Bing Model API - Global (EN + local language descriptions)
```
https://global.bing.com/hp/api/model?mkt={code}
```
- **CRITICAL**: `global.bing.com` bypasses IP geo-restriction! `mkt` parameter works.
- `www.bing.com/hp/api/model` does NOT respect `mkt` (IP-based market).
- Returns: Description, Headline, Title, QuickFact.MainText, Copyright
- Covers: Today + 7 preloaded items (may be future dates)
- ALL markets have desc via this endpoint
- **Desc length varies by market**: en-US (~950 chars), pt-BR (~630 chars), fr-FR (~350 chars) - this is Bing server behavior

### 3. Bing Model API - China (Chinese descriptions)
```
https://cn.bing.com/hp/api/model
```
- Market is IP-determined (always ZH-CN from China IP), `mkt` param ignored
- Returns Chinese Description, QuickFact, Title
- Same coverage as global: today + 7 preloaded items
- Used as primary ZH source

### 4. MyMemory Translation API (v5.4)
```
https://api.mymemory.translated.net/get?q={text}&langpair={source}|{target}
```
- Translates local language descriptions to English for non-English markets
- Rate limit: ~1000 words/day for free tier
- Fallback: If translation fails, uses original local description

## Market Configuration (11 markets)

| Market | Code | Independent? | Old API desc? | Model desc? | Local Language |
|--------|------|-------------|---------------|-------------|----------------|
| US | en-US | Yes (baseline) | Yes | Yes | English |
| UK | en-GB | No | Yes | Yes | English |
| CA | en-CA | No | Yes | Yes | English |
| DE | de-DE | No | Yes | Yes | Deutsch |
| FR | fr-FR | Yes | Yes | Yes | Français |
| IT | it-IT | No | **No** | Yes | Italiano |
| ES | es-ES | No | Yes | Yes | Español |
| BR | pt-BR | No | **No** | Yes | Português |
| JP | ja-JP | Yes | Yes | Yes | 日本語 |
| CN | zh-CN | No | **No** | Yes | 中文 |
| IN | en-IN | No | Yes | Yes | English |

**Removed**: fr-CA (100% overlap with en-CA), ko-KR/zh-TW/en-AU/zh-HK (not independent)

## Language Strategy (v5.4)

### English market images (US/UK/CA/IN)
- **Title**: English (priority: en-US > en-GB > en-CA > en-IN)
- **Description**: English from API
- **Chinese Description**: From cn.bing.com (if available)
- **QuickFact**: English from API
- **Language Label**: "English" (blue)

### Non-English market images (DE/FR/IT/ES/BR/JP/CN)
- **Title**: Local language from source market
- **Local Description**: Original local language description
- **English Description**: Translated from local via MyMemory API (with fallback)
- **Chinese Description**: From cn.bing.com (if available)
- **Local QuickFact**: Original local language QuickFact
- **English QuickFact**: Translated from local (with fallback)
- **Language Labels**:
  - Local section: Language name in native script (e.g., "Deutsch", "日本語")
  - English section: "English" (blue)
  - Chinese section: "中文" (red)

### Localized "Did You Know" Labels

| Language | Label |
|----------|-------|
| English | Did You Know |
| Deutsch | Wussten Sie schon? |
| Français | Le saviez-vous ? |
| Italiano | Lo sapevi che? |
| Español | ¿Sabías que? |
| Português | Você sabia? |
| 日本語 | 知っていましたか？ |
| 中文 | 你知道吗？ |

## Incremental Update Mechanism

### How it works
1. **Cache file**: `/workspace/.bing_cache.json` stores all image entries from previous runs
2. **On each run**: Load cache → Fetch 14-day data → Merge cache supplements → Save updated cache
3. **Cache merge**: Existing entries get supplemented with missing desc/quickFacts from cache; expired entries (>90 days) are pruned
4. **Result**: Each daily run only needs to fetch 14 days of API data, but the gallery accumulates up to 90 days of content

### Cache data structure
```json
{
  "SpainLighthouse": {
    "name": "SpainLighthouse",
    "urlbase": "/th?id=OHR.SpainLighthouse_EN-US...",
    "date": "20260519",
    "markets": [...],
    "titles": {"en-US": "...", "pt-BR": "..."},
    "descs": {"en-US": "...", "fr-FR": "...", "zh-CN": "..."},
    "quickFacts": {"en-US": "...", "zh-CN": "..."},
    ...
  }
}
```

### Retention policy
- **MAX_CACHE_DAYS = 90**: Entries older than 90 days are automatically pruned on cache load
- **Storage**: Single JSON file at `/workspace/.bing_cache.json`
- **Size estimate**: ~30 entries × ~2KB each ≈ 60KB (grows to ~180KB at 90 days)

## UI Design (v5.4)

### Header & Logo
- Background: `#1a2744` dark navy
- Logo: Text-only "Bing Gallery" (no image dependency)
- Hover: Text color transitions to green (#4caf50)

### Back Button (Detail Page)
- Purple gradient: `linear-gradient(135deg, #667eea, #764ba2)`
- SVG chevron icon (inline, no external dependency)
- Uppercase text: "RETURN TO GALLERY"
- Hover: Gradient reverses + translateY(-2px) + enhanced shadow
- Active: Returns to position + reduced shadow

### Detail Page Layout (v5.4)
```
[Local Language Section] (for non-EN exclusives)
  ├─ Green label: "Deutsch" / "日本語" / "Português" etc
  ├─ Original local description
  └─ Yellow QuickFact box: "💡 Wussten Sie schon?" (localized)

[English Section]
  ├─ Blue label: "English"
  ├─ English description (translated from local for non-EN markets)
  └─ Yellow QuickFact box: "💡 Did You Know" (if no local QF)

[Chinese Section]
  ├─ Red label: "中文"
  ├─ Chinese description
  └─ Light yellow QuickFact box: "💡 你知道吗？"
```

### Language Labels
- **English**: Blue (`#1565c0`) background `#e3f2fd`, border `#bbdefb`
- **中文**: Red (`#c62828`) background `#ffebee`, border `#ffcdd2`
- **Local**: Green (`#2e7d32`) background `#e8f5e9`, border `#c8e6c9`

## Data Fetch Flow
1. **Load cache**: Read `/workspace/.bing_cache.json` (0 API calls)
2. **HPImageArchive**: 11 markets × 2 calls = 22 API calls
3. **Model API (global)**: 11 markets × 1 call = 11 calls
4. **Model API (cn.bing.com)**: 1 call for ZH
5. **MyMemory Translation**: Variable (only for non-EN markets, rate-limited)
6. **Merge cache**: Supplement missing fields from cache (0 API calls)
7. **Save cache**: Write updated cache to disk (0 API calls)
8. **Total**: ~34-50 API calls per generation (depending on translation needs)

## Known Limitations

### 1. Model API date coverage
`/hp/api/model` PreloadMediaContents returns today + ~7 future days. Past images beyond 8 days may lack desc. Cache helps preserve desc from previous runs.

### 2. Description length varies by market
Bing server returns different Description lengths per market (en-US ~950 chars, fr-FR ~350 chars, pt-BR ~630 chars). The script supplements short descriptions (<200 chars) with Title/Headline.

### 3. MyMemory API rate limits
Free tier has ~1000 words/day limit. When rate limited, script falls back to original local description without translation.

### 4. Remaining images without desc
~3 images per 14-day cycle (non-English exclusives older than 8 days, outside both API windows).

### 5. Chinese desc coverage
~7/30 images have Chinese descriptions from cn.bing.com.

## Files
- **Generator v5.4**: `/workspace/bing_gen_v5.4.py`
- **Generator v5.3 (backup)**: `/workspace/bing_gen_v5.3_backup.py`
- **Output**: `/workspace/bing_gallery.html`
- **Cache**: `/workspace/.bing_cache.json` (auto-generated, incremental data)
- **Skill doc**: `/workspace/bing-wallpaper-skill.md`

## Usage
```bash
cd /data/user/work && python3 bing_gen.py
```

## Version History

### 2026-05-19 v5.4: Translation API + Local Language Labels
1. **MyMemory Translation API**: Translates local language descriptions to English
2. **Proper language labels**: Non-English markets show native language names (Deutsch, 日本語, etc.)
3. **Localized Did You Know**: Each language has its own label ("Wussten Sie schon?", "Le saviez-vous ?", etc.)
4. **Three-language support**: Non-English markets now show Local + English + Chinese

### 2026-05-19 v5.3: Incremental Update + UI Polish
1. **Incremental cache**: JSON-based cache preserves data across runs; auto-prunes entries >90 days
2. **Desc supplement**: Short descriptions (<200 chars) auto-prepended with Title/Headline from API
3. **Text logo**: Removed Bing image logo, replaced with "Bing Gallery" text
4. **Back button**: Purple gradient pill with SVG chevron icon
5. **Card view fix**: Verified stream/card toggle works correctly

### 2026-05-19 v5.2: Stable Baseline Reconstruction
1. **Rebuilt from v4**: Removed problematic v5 features, kept working ones
2. **Fixed blank page**: JavaScript syntax error from f-string escaping; switched to template literals
3. **Pure Bing APIs**: No translation API calls

### 2026-05-19 v5.1: Layout & Translation Fixes (deprecated)
1. Logo visibility, language label spacing, tips placement, source language labels
2. MyMemory translation (removed in v5.3 due to rate limiting)

### 2026-05-19 v4: Model API + Remove Peapix
1. Discovered /hp/api/model for complete descriptions
2. global.bing.com bypasses IP restriction
3. Removed peapix dependency

### 2026-05-18 v3-v1: Initial Implementation
- Extended API parameters, title+caption concatenation, flag-icons CDN

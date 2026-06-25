#!/usr/bin/env python3
"""
Bing Daily Wallpaper Gallery Generator v5.3

Based on v4 stable version with improvements:
- /hp/api/model for complete desc (v4)
- global.bing.com bypasses IP restriction (v4)
- QuickFact display (v4)
- Text-only logo "Bing Gallery" (v5.3)
- Enhanced back button with gradient and hover effects (v5.3)
- Language labels on separate line (v5.1 improvement)
- Tips after respective language sections (v5.1 improvement)
- Source language names for non-EN exclusives (v5.1 improvement)
- NO translation API - pure Bing official APIs only

APIs used:
1. HPImageArchive.aspx - 14-day history, dedup
2. global.bing.com/hp/api/model - EN desc + QuickFact
3. cn.bing.com/hp/api/model - ZH desc + QuickFact (no translation)

Output: /workspace/bing_gallery.html
"""

import json
import urllib.request
import urllib.parse
import time
import re
import os
from datetime import datetime, timezone

# ─── Configuration ────────────────────────────────────────────────────────────

MARKETS = [
    {"code": "en-US", "name": "US",  "flag": "us"},
    {"code": "en-GB", "name": "UK",  "flag": "gb"},
    {"code": "en-CA", "name": "CA",  "flag": "ca"},
    {"code": "de-DE", "name": "DE",  "flag": "de"},
    {"code": "fr-FR", "name": "FR",  "flag": "fr"},
    {"code": "it-IT", "name": "IT",  "flag": "it"},
    {"code": "es-ES", "name": "ES",  "flag": "es"},
    {"code": "pt-BR", "name": "BR",  "flag": "br"},
    {"code": "ja-JP", "name": "JP",  "flag": "jp"},
    {"code": "zh-CN", "name": "CN",  "flag": "cn"},
    {"code": "en-IN", "name": "IN",  "flag": "in"},
]

ENGLISH_MARKETS = ["en-US", "en-GB", "en-CA", "en-IN"]
LOCAL_PRIORITY = ["ja-JP", "zh-CN", "fr-FR", "de-DE", "es-ES", "it-IT", "pt-BR"]

LANG_NAMES = {
    "de": "Deutsch", "fr": "Français", "it": "Italiano",
    "es": "Español", "pt": "Português", "ja": "日本語",
    "zh": "中文", "en": "English"
}

BING_ARCHIVE_API = "https://global.bing.com/HPImageArchive.aspx"
BING_MODEL_API = "https://global.bing.com/hp/api/model"
BING_CN_MODEL_API = "https://cn.bing.com/hp/api/model"

OUTPUT_PATH = "/workspace/bing_gallery.html"
CACHE_PATH = "/workspace/.bing_cache.json"
MAX_CACHE_DAYS = 90  # Maximum days to keep in cache

# ─── HTTP Helpers ─────────────────────────────────────────────────────────────

def fetch_json(url, retries=3, delay=2):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                print(f"  Failed: {url}: {e}")
                return None

def fetch_market_images(market_code, n=7, idx=0):
    params = {
        "format": "js", "n": n, "idx": idx, "mkt": market_code,
        "pid": "hp", "FORM": "BEHPTB", "ql": "6",
    }
    url = f"{BING_ARCHIVE_API}?{urllib.parse.urlencode(params)}"
    data = fetch_json(url)
    return data.get("images", []) if data else []

def fetch_model_desc(market_code, base_url=None):
    base = base_url or BING_MODEL_API
    url = f"{base}?mkt={market_code}" if base_url else f"{base}?mkt={market_code}"
    data = fetch_json(url)
    if not data:
        return {}
    result = {}
    all_items = data.get("MediaContents", []) + data.get("PreloadMediaContents", [])
    for item in all_items:
        name = item.get("Name", "")
        if not name:
            continue
        ic = item.get("ImageContent", {})
        desc = ic.get("Description", "").strip()
        title = ic.get("Title", "").strip()
        headline = ic.get("Headline", "").strip()
        # Supplement short descriptions with Title/Headline
        if desc and len(desc) < 200 and title:
            supplement = headline + ". " + title if headline and headline != title else title
            if supplement not in desc:
                desc = supplement + ". " + desc
        result[name] = {
            "desc": desc,
            "title": title,
            "headline": headline,
            "quickFact": ic.get("QuickFact", {}).get("MainText", "").strip(),
            "copyright": ic.get("Copyright", "").strip(),
            "date": item.get("Ssd", ""),
        }
    return result

# ─── Incremental Cache ────────────────────────────────────────────────────────

def load_cache():
    """Load cached image data from previous runs."""
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
            # Prune entries older than MAX_CACHE_DAYS
            cutoff = (datetime.now() - __import__('datetime').timedelta(days=MAX_CACHE_DAYS)).strftime("%Y%m%d")
            pruned = {k: v for k, v in cache.items() if k >= cutoff}
            removed = len(cache) - len(pruned)
            if removed > 0:
                print(f"  Cache: pruned {removed} entries older than {MAX_CACHE_DAYS} days")
            return pruned
        except Exception as e:
            print(f"  Cache: failed to load ({e}), starting fresh")
    return {}

def save_cache(image_entries):
    """Save image entries to cache for incremental updates."""
    cache = {}
    for name, entry in image_entries.items():
        cache[name] = {
            "name": entry["name"], "urlbase": entry["urlbase"],
            "date": entry["date"], "dateFormatted": entry["dateFormatted"],
            "markets": entry["markets"], "titles": entry["titles"],
            "copyrights": entry["copyrights"], "descs": entry["descs"],
            "quickFacts": entry["quickFacts"], "captions": entry["captions"],
            "copyrightlinks": entry["copyrightlinks"], "urlbases": entry["urlbases"],
        }
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def merge_cache(image_entries, cache):
    """Merge cached data into image_entries (cache fills missing fields)."""
    merged_count = 0
    for name, cached in cache.items():
        if name not in image_entries:
            # Restore cached entry
            image_entries[name] = {
                "name": cached["name"], "urlbase": cached["urlbase"],
                "date": cached["date"], "dateFormatted": cached["dateFormatted"],
                "markets": cached.get("markets", []),
                "titles": cached.get("titles", {}),
                "copyrights": cached.get("copyrights", {}),
                "descs": cached.get("descs", {}),
                "quickFacts": cached.get("quickFacts", {}),
                "captions": cached.get("captions", {}),
                "copyrightlinks": cached.get("copyrightlinks", {}),
                "urlbases": cached.get("urlbases", {}),
            }
            merged_count += 1
        else:
            # Supplement existing entry with cached desc data if missing
            entry = image_entries[name]
            for key in ["descs", "quickFacts", "titles", "copyrights"]:
                for mk, val in cached.get(key, {}).items():
                    if mk not in entry[key] and val:
                        entry[key][mk] = val
                        merged_count += 1
    return merged_count

def fetch_all_markets():
    all_data = {}
    for market in MARKETS:
        code = market["code"]
        print(f"  {code}...", end=" ")
        images = []
        for idx in [0, 7]:
            batch = fetch_market_images(code, n=7, idx=idx)
            images.extend(batch)
            time.sleep(0.3)
        all_data[code] = images
        print(f"{len(images)} images")
    return all_data

def fetch_all_descriptions():
    all_descs = {}
    for market in MARKETS:
        code = market["code"]
        print(f"  {code}...", end=" ")
        descs = fetch_model_desc(code)
        all_descs[code] = descs
        print(f"{len(descs)} descs")
        time.sleep(0.5)
    print("  zh-CN (cn.bing.com)...", end=" ")
    cn_descs = fetch_model_desc("zh-CN", base_url=BING_CN_MODEL_API)
    all_descs["zh-CN-cn"] = cn_descs
    print(f"{len(cn_descs)} descs")
    return all_descs

# ─── Data Processing ──────────────────────────────────────────────────────────

def extract_image_name(urlbase):
    match = re.search(r'OHR\.([A-Za-z0-9]+)', urlbase)
    return match.group(1) if match else ""

def format_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y%m%d").strftime("%B %d, %Y")
    except:
        return date_str

def build_image_data(all_data, all_descs, cache=None):
    image_entries = {}

    # Phase 1: Collect from old API
    for market_code, images in all_data.items():
        for img in images:
            urlbase = img.get("urlbase", "")
            name = extract_image_name(urlbase)
            if not name:
                continue
            if name not in image_entries:
                image_entries[name] = {
                    "name": name, "urlbase": urlbase,
                    "date": img.get("startdate", ""),
                    "dateFormatted": format_date(img.get("startdate", "")),
                    "markets": [], "titles": {}, "copyrights": {},
                    "descs": {}, "quickFacts": {}, "captions": {},
                    "copyrightlinks": {}, "urlbases": {},
                }
            entry = image_entries[name]
            market_info = next((m for m in MARKETS if m["code"] == market_code), None)
            if not market_info:
                continue
            if not any(m["code"] == market_code for m in entry["markets"]):
                entry["markets"].append({"code": market_info["code"], "name": market_info["name"], "flag": market_info["flag"]})

            raw_title = img.get("title", "").strip()
            if not raw_title:
                raw_title = img.get("bsTitle", "").strip()
            raw_caption = img.get("caption", "").strip()
            if raw_title and raw_title.lower() not in ("info", ""):
                full_title = raw_title
                if raw_caption and raw_caption != raw_title:
                    full_title = raw_title + ". " + raw_caption
                entry["titles"][market_code] = full_title
                entry["captions"][market_code] = raw_caption

            copyright_text = img.get("copyright", "").strip()
            if copyright_text:
                entry["copyrights"][market_code] = copyright_text
            cl = img.get("copyrightlink", "").strip()
            if cl:
                entry["copyrightlinks"][market_code] = cl
            desc = img.get("desc", "").strip()
            if desc:
                entry["descs"][market_code] = desc
            entry["urlbases"][market_code] = urlbase

    # Phase 1.5: Merge cached data (incremental update)
    if cache:
        merged = merge_cache(image_entries, cache)
        if merged:
            print(f"  Cache merged: {merged} supplements from previous runs")

    # Phase 2: Supplement with global model API
    for market_code, market_descs in all_descs.items():
        if market_code == "zh-CN-cn":
            continue
        for img_name, desc_data in market_descs.items():
            if img_name not in image_entries:
                continue
            entry = image_entries[img_name]
            desc = desc_data.get("desc", "").strip()
            if desc:
                entry["descs"][market_code] = desc
            qf = desc_data.get("quickFact", "").strip()
            if qf:
                entry["quickFacts"][market_code] = qf
            if market_code not in entry["titles"]:
                nt = desc_data.get("title", "").strip()
                nh = desc_data.get("headline", "").strip()
                if nt and nh and nt != nh:
                    entry["titles"][market_code] = nh + ". " + nt
                elif nh:
                    entry["titles"][market_code] = nh
                elif nt:
                    entry["titles"][market_code] = nt
            nc = desc_data.get("copyright", "").strip()
            if market_code not in entry["copyrights"] and nc:
                entry["copyrights"][market_code] = nc

    # Phase 3: Supplement Chinese from cn.bing.com
    cn_descs = all_descs.get("zh-CN-cn", {})
    for img_name, desc_data in cn_descs.items():
        if img_name not in image_entries:
            continue
        entry = image_entries[img_name]
        desc = desc_data.get("desc", "").strip()
        if desc:
            entry["descs"]["zh-CN"] = desc
        qf = desc_data.get("quickFact", "").strip()
        if qf:
            entry["quickFacts"]["zh-CN"] = qf

    # Phase 4: Build final list (NO TRANSLATION)
    unique_images = []
    for name, entry in image_entries.items():
        has_english = any(mc in entry["titles"] for mc in ENGLISH_MARKETS)

        # Title
        title = ""
        if has_english:
            for mc in ENGLISH_MARKETS:
                if mc in entry["titles"]:
                    title = entry["titles"][mc]
                    break
        else:
            for mc in LOCAL_PRIORITY:
                if mc in entry["titles"]:
                    title = entry["titles"][mc]
                    break

        # Copyright
        copyright_text = ""
        if has_english:
            for mc in ENGLISH_MARKETS:
                if mc in entry["copyrights"]:
                    copyright_text = entry["copyrights"][mc]
                    break
        else:
            for mc in LOCAL_PRIORITY:
                if mc in entry["copyrights"]:
                    copyright_text = entry["copyrights"][mc]
                    break

        # English desc
        en_desc = ""
        if has_english:
            for mc in ENGLISH_MARKETS:
                if mc in entry["descs"]:
                    en_desc = entry["descs"][mc]
                    break
            if not en_desc:
                for mc in LOCAL_PRIORITY:
                    if mc in entry["descs"]:
                        en_desc = entry["descs"][mc]
                        break
        else:
            for mc in LOCAL_PRIORITY:
                if mc in entry["descs"]:
                    en_desc = entry["descs"][mc]
                    break

        # Chinese desc (from cn.bing.com only)
        zh_desc = entry["descs"].get("zh-CN", "")

        # Local language desc (for non-English exclusives)
        desc_lang = ""
        local_desc = ""
        local_lang_name = ""
        if not has_english:
            for mc in LOCAL_PRIORITY:
                if mc in entry["descs"] and mc != "zh-CN":
                    local_desc = entry["descs"][mc]
                    desc_lang = mc.split("-")[0]
                    local_lang_name = LANG_NAMES.get(desc_lang, desc_lang.upper())
                    break

        # QuickFact (from APIs only)
        en_qf = ""
        if has_english:
            for mc in ENGLISH_MARKETS:
                if mc in entry["quickFacts"]:
                    en_qf = entry["quickFacts"][mc]
                    break
        if not en_qf:
            for mc in LOCAL_PRIORITY:
                if mc in entry["quickFacts"]:
                    en_qf = entry["quickFacts"][mc]
                    break

        zh_qf = entry["quickFacts"].get("zh-CN", "")

        # Source market
        source_market = ""
        if has_english:
            for mc in ENGLISH_MARKETS:
                if mc in entry["urlbases"]:
                    source_market = mc
                    break
        if not source_market:
            for mc in LOCAL_PRIORITY:
                if mc in entry["urlbases"]:
                    source_market = mc
                    break

        img_urlbase = entry["urlbases"].get(source_market, entry["urlbases"].get("en-US", ""))
        img_id = img_urlbase.replace("/th?id=", "") if img_urlbase else ""
        if not img_id or img_id == "OHR." or "_" not in img_id:
            continue

        copyrightlink = ""
        if has_english:
            for mc in ENGLISH_MARKETS:
                if mc in entry["copyrightlinks"]:
                    copyrightlink = entry["copyrightlinks"][mc]
                    break
        if not copyrightlink:
            for mc in LOCAL_PRIORITY:
                if mc in entry["copyrightlinks"]:
                    copyrightlink = entry["copyrightlinks"][mc]
                    break

        if not title:
            title = name

        unique_images.append({
            "name": name, "urlbase": img_urlbase,
            "date": entry["date"], "dateFormatted": entry["dateFormatted"],
            "markets": entry["markets"], "has_english": has_english,
            "title": title, "copyright": copyright_text,
            "copyrightlink": copyrightlink, "sourceMarket": source_market,
            "desc": en_desc, "descZh": zh_desc,
            "localDesc": local_desc if not has_english and local_desc != en_desc else "",
            "localLangName": local_lang_name,
            "desc_lang": desc_lang,
            "quickFact": en_qf, "quickFactZh": zh_qf,
            "thumb": f"https://www.bing.com/th?id={img_id}_1920x1080.jpg",
            "uhd": f"https://www.bing.com/th?id={img_id}_UHD.jpg",
            "h1200": f"https://www.bing.com/th?id={img_id}_1920x1200.jpg",
            "h1080": f"https://www.bing.com/th?id={img_id}_1920x1080.jpg",
        })

    unique_images.sort(key=lambda x: x["date"], reverse=True)

    with_desc = sum(1 for img in unique_images if img["desc"])
    with_zh = sum(1 for img in unique_images if img["descZh"])
    with_qf = sum(1 for img in unique_images if img["quickFact"])
    print(f"\n  EN desc: {with_desc}/{len(unique_images)} | ZH desc: {with_zh}/{len(unique_images)} | QuickFact: {with_qf}/{len(unique_images)}")

    no_desc = [img for img in unique_images if not img["desc"]]
    if no_desc:
        print(f"  Without desc: {', '.join(img['name'] for img in no_desc)}")

    return unique_images, image_entries

# ─── HTML Generation ──────────────────────────────────────────────────────────

def build_image_json(images):
    result = []
    for img in images:
        result.append({
            "name": img["name"], "date": img["date"],
            "dateFormatted": img["dateFormatted"],
            "markets": img["markets"], "hasEnglish": img["has_english"],
            "title": img["title"], "copyright": img["copyright"],
            "copyrightlink": img["copyrightlink"], "sourceMarket": img["sourceMarket"],
            "desc": img["desc"], "descZh": img["descZh"],
            "localDesc": img["localDesc"], "localLangName": img.get("localLangName", ""),
            "descLang": img.get("desc_lang", ""),
            "quickFact": img["quickFact"], "quickFactZh": img["quickFactZh"],
            "thumb": img["thumb"], "uhd": img["uhd"],
            "h1200": img["h1200"], "h1080": img["h1080"],
        })
    return json.dumps(result, indent=2, ensure_ascii=False)

def generate_html(images):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    images_json = build_image_json(images)
    markets_json = json.dumps(MARKETS, indent=2, ensure_ascii=False)

    # Use double braces {{ and }} for CSS, single for Python f-string
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bing Gallery</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/css/flag-icons.min.css">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f5f5f5; color: #333;
}

/* Header */
.header {
    background: #1a2744; color: white; padding: 0 24px;
    height: 56px; display: flex; align-items: center;
    position: sticky; top: 0; z-index: 100;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.logo {
    display: flex; align-items: center; gap: 0;
    font-size: 20px; font-weight: 700; text-decoration: none;
    color: white; cursor: pointer; flex-shrink: 0;
}
.logo-text {
    font-size: 20px; font-weight: 700; color: white;
    letter-spacing: 0.5px;
}
.logo:hover .logo-text {
    color: #4caf50;
}
.header-right {
    margin-left: auto; display: flex; align-items: center; gap: 10px;
}
.view-toggle {
    display: flex; gap: 2px; background: rgba(255,255,255,0.1);
    border-radius: 8px; padding: 3px;
}
.view-btn {
    width: 34px; height: 34px; border: none; background: none;
    color: rgba(255,255,255,0.6); border-radius: 6px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.2s; font-size: 16px;
}
.view-btn:hover { background: rgba(255,255,255,0.15); color: white; }
.view-btn.active { background: rgba(76,175,80,0.8); color: white; }
.search-box {
    padding: 7px 16px; border: 2px solid transparent; border-radius: 20px;
    font-size: 14px; width: 220px; outline: none; transition: border-color 0.2s;
    background: rgba(255,255,255,0.9);
}
.search-box:focus { border-color: #4caf50; }
.search-box::placeholder { color: #999; }

/* Tabs */
.tabs-container {
    background: white; border-bottom: 1px solid #e0e0e0;
    overflow-x: auto; white-space: nowrap; -webkit-overflow-scrolling: touch;
}
.tabs-container::-webkit-scrollbar { height: 0; }
.tabs { display: flex; padding: 0 16px; }
.tab-btn {
    padding: 10px 16px; border: none; background: none; cursor: pointer;
    font-size: 14px; color: #666; border-bottom: 3px solid transparent;
    transition: all 0.2s; white-space: nowrap;
}
.tab-btn:hover { color: #1a2744; background: rgba(26,39,68,0.05); }
.tab-btn.active { color: #1a2744; border-bottom-color: #4caf50; font-weight: 600; }

.update-time {
    text-align: center; padding: 8px 16px; font-size: 12px;
    color: #999; background: #fafafa; border-bottom: 1px solid #eee;
}

.main { max-width: 1200px; margin: 0 auto; padding: 16px; }

/* Stream View */
.stream-item {
    display: flex; gap: 16px; padding: 16px; background: white;
    border-radius: 8px; margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: box-shadow 0.2s; cursor: pointer;
}
.stream-item:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
.stream-thumb {
    flex-shrink: 0; width: 200px; height: 112px;
    border-radius: 6px; overflow: hidden;
}
.stream-thumb img {
    width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s;
}
.stream-item:hover .stream-thumb img { transform: scale(1.05); }
.stream-info {
    flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px;
}
.stream-date { font-size: 12px; color: #999; }
.stream-title {
    font-size: 16px; font-weight: 600; color: #1a2744;
    line-height: 1.4; cursor: pointer;
}
.stream-title:hover { color: #4caf50; }
.stream-desc {
    font-size: 13px; color: #888; line-height: 1.5; margin-top: 4px;
    display: -webkit-box; -webkit-line-clamp: 2;
    -webkit-box-orient: vertical; overflow: hidden;
}
.stream-copyright {
    font-size: 12px; color: #aaa; line-height: 1.3;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.stream-downloads { display: flex; gap: 8px; margin-top: 4px; }
.stream-markets { font-size: 16px; margin-top: 4px; }

/* Card View */
.card-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;
}
.card {
    background: white; border-radius: 12px; overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: box-shadow 0.2s; cursor: pointer;
}
.card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
.card-image { width: 100%; aspect-ratio: 16/9; overflow: hidden; }
.card-image img {
    width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s;
}
.card:hover .card-image img { transform: scale(1.05); }
.card-body { padding: 12px 16px; }
.card-title {
    font-size: 15px; font-weight: 600; color: #1a2744;
    line-height: 1.4; cursor: pointer;
}
.card-title:hover { color: #4caf50; }
.card-desc {
    font-size: 12px; color: #999; line-height: 1.4; margin-top: 4px;
    display: -webkit-box; -webkit-line-clamp: 2;
    -webkit-box-orient: vertical; overflow: hidden;
}
.card-date { font-size: 12px; color: #bbb; margin-top: 6px; }
.card-copyright {
    font-size: 11px; color: #ccc; line-height: 1.3; margin-top: 2px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.card-downloads { display: flex; gap: 8px; margin-top: 8px; }
.card-markets { font-size: 16px; margin-top: 6px; }

/* Detail View */
.detail-container { max-width: 1200px; margin: 0 auto; padding: 24px 16px; }
.detail-back {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 10px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none; border-radius: 25px;
    font-size: 14px; font-weight: 700; color: white; cursor: pointer;
    transition: all 0.3s ease; text-decoration: none; margin-bottom: 20px;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    text-transform: uppercase; letter-spacing: 0.5px;
}
.detail-back:hover {
    background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
}
.detail-back:active {
    transform: translateY(0);
    box-shadow: 0 2px 10px rgba(102, 126, 234, 0.4);
}
.detail-image-wrap {
    background: white; border-radius: 12px; overflow: hidden;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1); margin-bottom: 24px;
}
.detail-image-wrap img { width: 100%; display: block; }
.detail-info {
    background: white; border-radius: 12px; padding: 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.detail-title {
    font-size: 24px; font-weight: 700; color: #1a2744;
    line-height: 1.4; margin-bottom: 8px;
}
.detail-date { font-size: 14px; color: #999; margin-bottom: 12px; }
.detail-copyright {
    font-size: 14px; color: #666; line-height: 1.6; margin-bottom: 16px;
}

/* Description section */
.desc-section {
    margin: 20px 0;
    padding-bottom: 20px;
    border-bottom: 1px solid #f0f0f0;
}
.desc-section:last-of-type {
    border-bottom: none;
}

/* Language label */
.lang-label {
    display: inline-block; font-size: 11px; padding: 4px 12px;
    border-radius: 12px; margin-bottom: 12px;
    text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;
}
.lang-en { color: #1565c0; background: #e3f2fd; border: 1px solid #bbdefb; }
.lang-zh { color: #c62828; background: #ffebee; border: 1px solid #ffcdd2; }
.lang-local { color: #2e7d32; background: #e8f5e9; border: 1px solid #c8e6c9; }

/* Description text */
.desc-text {
    font-size: 15px; color: #444; line-height: 1.8;
}
.desc-text-zh {
    font-size: 15px; color: #444; line-height: 1.8;
}

/* QuickFact */
.quick-fact-box {
    margin-top: 16px;
    padding: 14px 18px; background: #fff8e1; border-radius: 8px;
    border-left: 4px solid #ffc107;
}
.quick-fact-box-zh {
    margin-top: 16px;
    padding: 14px 18px; background: #fffde7; border-radius: 8px;
    border-left: 4px solid #ffca28;
}
.quick-fact-label {
    display: inline-block; font-size: 11px;
    color: #f57f17; background: #fff3cd; padding: 2px 8px;
    border-radius: 10px; margin-bottom: 8px;
    font-weight: 600;
}
.quick-fact-label-zh {
    display: inline-block; font-size: 11px;
    color: #e65100; background: #fff3e0; padding: 2px 8px;
    border-radius: 10px; margin-bottom: 8px;
    font-weight: 600;
}
.quick-fact-text {
    font-size: 14px; color: #555; line-height: 1.7;
}

/* Local desc (non-English exclusive) */
.local-desc-box {
    margin: 20px 0;
    padding: 16px; background: #f5f7fa; border-radius: 8px;
    border: 1px solid #e0e5ec;
}

.detail-downloads {
    display: flex; gap: 10px; flex-wrap: wrap; margin: 24px 0;
}
.detail-dl-btn {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 600;
    text-decoration: none; color: white; transition: all 0.2s;
}
.detail-dl-btn:hover {
    transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
.uhd-btn { background: #4caf50; }
.h1200-btn { background: #2196f3; }
.h1080-btn { background: #607d8b; }
.search-btn { background: #1a2744; }

.detail-markets-section { border-top: 1px solid #eee; padding-top: 16px; }
.detail-markets-label { font-size: 13px; color: #999; margin-bottom: 8px; }
.detail-markets-list { display: flex; flex-wrap: wrap; gap: 8px; }
.detail-market-tag {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 4px 10px; background: #f5f5f5; border-radius: 16px;
    font-size: 13px; color: #666;
}

.view-container { transition: opacity 0.3s ease; }
.view-hidden { display: none !important; }
.no-results { text-align: center; padding: 60px 20px; color: #999; font-size: 16px; }

.fi { display: inline-block; width: 1.2em; height: 1.2em; border-radius: 2px; vertical-align: middle; margin-right: 2px; }
.stream-markets .fi, .card-markets .fi { width: 1.4em; height: 1em; margin: 1px 2px; }
.detail-market-tag .fi { width: 1.4em; height: 1em; margin-right: 4px; }

.dl-btn {
    display: inline-flex; align-items: center; padding: 4px 10px;
    border-radius: 4px; font-size: 11px; font-weight: 600;
    text-decoration: none; color: white; transition: all 0.2s;
}
.dl-btn:hover { opacity: 0.85; }

@media (max-width: 768px) {
    .stream-item { flex-direction: column; }
    .stream-thumb { width: 100%; height: auto; aspect-ratio: 16/9; }
    .search-box { width: 140px; font-size: 13px; }
    .header { padding: 0 12px; }
    .main { padding: 8px; }
    .card-grid { grid-template-columns: 1fr; }
    .detail-container { padding: 12px 8px; }
    .detail-title { font-size: 20px; }
}
@media (max-width: 480px) {
    .search-box { width: 100px; }
    .view-btn { width: 30px; height: 30px; font-size: 14px; }
    .logo { font-size: 16px; gap: 6px; }
    .logo-img { height: 22px; }
}
</style>
</head>
<body>

<div class="header">
    <a class="logo" onclick="app.navigate('#/')">
        <span class="logo-text">Bing Gallery</span>
    </a>
    <div class="header-right">
        <div class="view-toggle" id="viewToggle">
            <button class="view-btn active" id="streamBtn" title="Stream view">&#9776;</button>
            <button class="view-btn" id="cardBtn" title="Card view">&#9638;</button>
        </div>
        <input type="text" class="search-box" placeholder="Search wallpapers..." id="searchBox" />
    </div>
</div>

<div class="tabs-container" id="tabsContainer">
    <div class="tabs" id="tabsBar"></div>
</div>

<div class="update-time">Last updated: ''' + now + '''</div>

<div class="main view-container" id="streamView">
    <div id="streamList"></div>
</div>

<div class="main view-container view-hidden" id="cardView">
    <div class="card-grid" id="cardGrid"></div>
</div>

<div class="view-container view-hidden" id="detailView">
    <div class="detail-container" id="detailContent"></div>
</div>

<script>
var ALL_IMAGES = ''' + images_json + ''';
var ALL_MARKETS = ''' + markets_json + ''';
var app = { currentView: 'stream', currentMarket: 'all', searchQuery: '', currentImageName: null };

function escapeHtml(s) { if (!s) return ''; return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function getFilteredImages() {
    var q = app.searchQuery.toLowerCase();
    return ALL_IMAGES.filter(function(img) {
        if (app.currentMarket !== 'all') {
            var f = false;
            for (var i = 0; i < img.markets.length; i++) { if (img.markets[i].code === app.currentMarket) { f = true; break; } }
            if (!f) return false;
        }
        if (q) {
            var t = (img.title + ' ' + img.copyright + ' ' + img.desc + ' ' + img.descZh + ' ' + img.dateFormatted).toLowerCase();
            if (t.indexOf(q) === -1) return false;
        }
        return true;
    });
}

function buildMarketFlags(markets) {
    return markets.map(function(m) { return '<span class="fi fi-' + m.flag + '" title="' + m.name + '"></span>'; }).join(' ');
}
function buildMarketTagsHtml(markets) {
    return markets.map(function(m) {
        return '<span class="detail-market-tag"><span class="fi fi-' + m.flag + '" title="' + m.name + '"></span> ' + m.name + '</span>';
    }).join('');
}

function renderTabs() {
    var h = '<button class="tab-btn' + (app.currentMarket === 'all' ? ' active' : '') + '" data-market="all">All</button>';
    ALL_MARKETS.forEach(function(m) {
        h += '<button class="tab-btn' + (app.currentMarket === m.code ? ' active' : '') + '" data-market="' + m.code + '"><span class="fi fi-' + m.flag + '"></span> ' + m.name + '</button>';
    });
    document.getElementById('tabsBar').innerHTML = h;
    document.querySelectorAll('.tab-btn').forEach(function(t) {
        t.addEventListener('click', function() { app.currentMarket = this.getAttribute('data-market'); renderTabs(); renderCurrentView(); });
    });
}

function renderStreamView() {
    var imgs = getFilteredImages(), c = document.getElementById('streamList');
    if (!imgs.length) { c.innerHTML = '<div class="no-results">No wallpapers found.</div>'; return; }
    var h = '';
    imgs.forEach(function(img) {
        var dp = img.desc ? '<div class="stream-desc">' + escapeHtml(img.desc.substring(0, 150)) + '</div>' : '';
        h += '<div class="stream-item" data-name="' + img.name + '">' +
            '<div class="stream-thumb" onclick="app.navigate(`#/image/' + img.name + '`)"><img src="' + img.thumb + '" alt="' + escapeHtml(img.title) + '" loading="lazy" /></div>' +
            '<div class="stream-info"><div class="stream-date">' + img.dateFormatted + '</div>' +
            '<div class="stream-title" onclick="app.navigate(`#/image/' + img.name + '`)">' + escapeHtml(img.title) + '</div>' +
            dp + '<div class="stream-copyright">' + escapeHtml(img.copyright) + '</div>' +
            '<div class="stream-downloads"><a href="' + img.uhd + '" class="dl-btn uhd-btn" target="_blank" onclick="event.stopPropagation()">UHD</a><a href="' + img.h1200 + '" class="dl-btn h1200-btn" target="_blank" onclick="event.stopPropagation()">1920x1200</a></div>' +
            '<div class="stream-markets">' + buildMarketFlags(img.markets) + '</div></div></div>';
    });
    c.innerHTML = h;
}

function renderCardView() {
    var imgs = getFilteredImages(), c = document.getElementById('cardGrid');
    if (!imgs.length) { c.innerHTML = '<div class="no-results">No wallpapers found.</div>'; return; }
    var h = '';
    imgs.forEach(function(img) {
        var dp = img.desc ? '<div class="card-desc">' + escapeHtml(img.desc.substring(0, 120)) + '</div>' : '';
        h += '<div class="card" data-name="' + img.name + '">' +
            '<div class="card-image" onclick="app.navigate(`#/image/' + img.name + '`)"><img src="' + img.thumb + '" alt="' + escapeHtml(img.title) + '" loading="lazy" /></div>' +
            '<div class="card-body"><div class="card-title" onclick="app.navigate(`#/image/' + img.name + '`)">' + escapeHtml(img.title) + '</div>' +
            dp + '<div class="card-date">' + img.dateFormatted + '</div><div class="card-copyright">' + escapeHtml(img.copyright) + '</div>' +
            '<div class="card-downloads"><a href="' + img.uhd + '" class="dl-btn uhd-btn" target="_blank" onclick="event.stopPropagation()">UHD</a><a href="' + img.h1200 + '" class="dl-btn h1200-btn" target="_blank" onclick="event.stopPropagation()">1920x1200</a></div>' +
            '<div class="card-markets">' + buildMarketFlags(img.markets) + '</div></div></div>';
    });
    c.innerHTML = h;
}

function renderDetailView(imageName) {
    var img = null;
    for (var i = 0; i < ALL_IMAGES.length; i++) { if (ALL_IMAGES[i].name === imageName) { img = ALL_IMAGES[i]; break; } }
    if (!img) { document.getElementById('detailContent').innerHTML = '<div class="no-results">Image not found.</div>'; return; }

    var bingBtn = img.copyrightlink ? '<a href="' + escapeHtml(img.copyrightlink) + '" class="detail-dl-btn search-btn" target="_blank">&#128269; Search on Bing</a>' : '';

    var contentHtml = '';

    // Local language section (for non-English exclusives)
    if (img.localDesc && img.localLangName) {
        contentHtml += '<div class="local-desc-box">';
        contentHtml += '<div class="lang-label lang-local">' + img.localLangName + '</div><br>';
        contentHtml += '<div class="desc-text">' + escapeHtml(img.localDesc) + '</div>';
        contentHtml += '</div>';
    }

    // English section
    if (img.desc) {
        contentHtml += '<div class="desc-section">';
        contentHtml += '<div class="lang-label lang-en">English</div><br>';
        contentHtml += '<div class="desc-text">' + escapeHtml(img.desc) + '</div>';
        if (img.quickFact) {
            contentHtml += '<div class="quick-fact-box">';
            contentHtml += '<div class="quick-fact-label">&#128161; Did You Know</div><br>';
            contentHtml += '<div class="quick-fact-text">' + escapeHtml(img.quickFact) + '</div>';
            contentHtml += '</div>';
        }
        contentHtml += '</div>';
    }

    // Chinese section
    if (img.descZh) {
        contentHtml += '<div class="desc-section">';
        contentHtml += '<div class="lang-label lang-zh">&#20013;&#25991;</div><br>';
        contentHtml += '<div class="desc-text-zh">' + escapeHtml(img.descZh) + '</div>';
        if (img.quickFactZh) {
            contentHtml += '<div class="quick-fact-box-zh">';
            contentHtml += '<div class="quick-fact-label-zh">&#128161; &#20320;&#30693;&#36947;&#21527;&#65311;</div><br>';
            contentHtml += '<div class="quick-fact-text">' + escapeHtml(img.quickFactZh) + '</div>';
            contentHtml += '</div>';
        }
        contentHtml += '</div>';
    }

    var html =
        '<a class="detail-back" onclick="app.navigate(`#/`)"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right:6px;flex-shrink:0"><path d="M15 18l-6-6 6-6"/></svg>Return to Gallery</a>' +
        '<div class="detail-image-wrap"><img src="' + img.h1080 + '" alt="' + escapeHtml(img.title) + '" /></div>' +
        '<div class="detail-info"><div class="detail-title">' + escapeHtml(img.title) + '</div>' +
        '<div class="detail-date">' + img.dateFormatted + '</div>' +
        '<div class="detail-copyright">' + escapeHtml(img.copyright) + '</div>' +
        contentHtml +
        '<div class="detail-downloads">' +
        '<a href="' + img.uhd + '" class="detail-dl-btn uhd-btn" target="_blank">UHD</a>' +
        '<a href="' + img.h1200 + '" class="detail-dl-btn h1200-btn" target="_blank">1920x1200</a>' +
        '<a href="' + img.h1080 + '" class="detail-dl-btn h1080-btn" target="_blank">1920x1080</a>' +
        bingBtn + '</div>' +
        '<div class="detail-markets-section"><div class="detail-markets-label">Appears in:</div>' +
        '<div class="detail-markets-list">' + buildMarketTagsHtml(img.markets) + '</div></div></div>';

    document.getElementById('detailContent').innerHTML = html;
}

function showView(v) {
    document.getElementById('streamView').classList.toggle('view-hidden', v !== 'stream');
    document.getElementById('cardView').classList.toggle('view-hidden', v !== 'card');
    document.getElementById('detailView').classList.toggle('view-hidden', v !== 'detail');
    var s = v !== 'detail';
    document.getElementById('tabsContainer').style.display = s ? '' : 'none';
    document.querySelector('.update-time').style.display = s ? '' : 'none';
    document.getElementById('viewToggle').style.display = s ? '' : 'none';
    app.currentView = v;
}
function renderCurrentView() {
    if (app.currentView === 'stream') renderStreamView();
    else if (app.currentView === 'card') renderCardView();
    else renderDetailView(app.currentImageName);
}

app.navigate = function(p) { window.location.hash = p; };
function handleRoute() {
    var h = window.location.hash || '#/';
    if (h.indexOf('#/image/') === 0) {
        app.currentImageName = h.replace('#/image/', '');
        showView('detail'); renderDetailView(app.currentImageName); window.scrollTo(0, 0);
    } else {
        app.currentImageName = null;
        showView(app.currentView === 'detail' ? 'stream' : app.currentView);
        renderCurrentView();
    }
}

(function init() {
    renderTabs();
    document.getElementById('streamBtn').addEventListener('click', function() {
        app.currentView = 'stream'; this.classList.add('active');
        document.getElementById('cardBtn').classList.remove('active');
        showView('stream'); renderStreamView();
    });
    document.getElementById('cardBtn').addEventListener('click', function() {
        app.currentView = 'card'; this.classList.add('active');
        document.getElementById('streamBtn').classList.remove('active');
        showView('card'); renderCardView();
    });
    document.getElementById('searchBox').addEventListener('input', function() {
        app.searchQuery = this.value;
        if (app.searchQuery) { app.currentMarket = 'all'; renderTabs(); }
        renderCurrentView();
    });
    window.addEventListener('hashchange', handleRoute);
    handleRoute(); renderStreamView(); renderCardView();
})();
</script>
</body>
</html>'''
    return html

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Bing Daily Wallpaper Gallery Generator v5.3")
    print("Text logo + Enhanced back button + Incremental update")
    print("=" * 60)

    # Load cache for incremental updates
    print("\n[0/4] Loading cache...")
    cache = load_cache()
    print(f"  Cache: {len(cache)} entries loaded")

    print("\n[1/4] Fetching 14-day history...")
    all_data = fetch_all_markets()
    print(f"  Total: {sum(len(v) for v in all_data.values())} images")

    print("\n[2/4] Fetching descriptions (global + cn.bing.com)...")
    all_descs = fetch_all_descriptions()

    print("\n[3/4] Processing and deduplicating...")
    unique_images, image_entries = build_image_data(all_data, all_descs, cache=cache)
    print(f"  Unique: {len(unique_images)} images")

    # Save cache for next incremental run
    save_cache(image_entries)
    print(f"  Cache saved: {len(image_entries)} entries -> {CACHE_PATH}")

    print("\n[4/4] Generating HTML...")
    html = generate_html(unique_images)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nDone! {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH) / 1024:.1f} KB)")

    print("\n--- Sample ---")
    for img in unique_images[:3]:
        print(f"  {img['name']}: desc={len(img['desc'])} zh={len(img['descZh'])} qf={len(img['quickFact'])} qfZh={len(img['quickFactZh'])}")

if __name__ == "__main__":
    main()

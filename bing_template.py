#!/usr/bin/env python3
"""
Bing Gallery HTML Template - Embedded Version
将完整的 HTML 模板内嵌为 Python 字符串常量
确保在任何环境中（包括 GitHub Actions）都能使用正确的样式
"""

# 模板分为三部分：
# HEAD: CSS + HTML body + <script> 开头
# MID: ALL_IMAGES 和 ALL_MARKETS 之间的部分
# TAIL: JavaScript 函数 + </script></body></html>

TEMPLATE_HEAD = r'''<!DOCTYPE html>
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

/* Dark mode */
body.dark-mode { background: #1a1a2e; color: #e0e0e0; }
body.dark-mode .tabs-container { background: #16213e; border-bottom-color: #333; }
body.dark-mode .tab-btn { color: #aaa; }
body.dark-mode .tab-btn:hover { color: #fff; background: rgba(255,255,255,0.05); }
body.dark-mode .tab-btn.active { color: #4caf50; border-bottom-color: #4caf50; }
body.dark-mode .update-time { background: #16213e; color: #666; border-bottom-color: #333; }
body.dark-mode .stream-item { background: #16213e; box-shadow: 0 1px 3px rgba(0,0,0,0.3); }
body.dark-mode .stream-item:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
body.dark-mode .stream-title { color: #e0e0e0; }
body.dark-mode .stream-title:hover { color: #4caf50; }
body.dark-mode .stream-desc { color: #aaa; }
body.dark-mode .stream-copyright { color: #666; }
body.dark-mode .card { background: #16213e; box-shadow: 0 1px 3px rgba(0,0,0,0.3); }
body.dark-mode .card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
body.dark-mode .card-title { color: #e0e0e0; }
body.dark-mode .card-title:hover { color: #4caf50; }
body.dark-mode .card-desc { color: #aaa; }
body.dark-mode .card-date { color: #666; }
body.dark-mode .card-copyright { color: #555; }
body.dark-mode .detail-info { background: #16213e; box-shadow: 0 1px 3px rgba(0,0,0,0.3); }
body.dark-mode .detail-image-wrap { box-shadow: 0 4px 20px rgba(0,0,0,0.4); }
body.dark-mode .detail-title { color: #e0e0e0; }
body.dark-mode .detail-date { color: #888; }
body.dark-mode .detail-copyright { color: #999; }
body.dark-mode .desc-text, body.dark-mode .desc-text-zh { color: #ccc; }
body.dark-mode .desc-section { border-bottom-color: #333; }
body.dark-mode .detail-market-tag { background: #0f3460; color: #aaa; }
body.dark-mode .detail-markets-section { border-top-color: #333; }
body.dark-mode .detail-markets-label { color: #666; }
body.dark-mode .search-box { background: rgba(255,255,255,0.15); color: #fff; }
body.dark-mode .search-box::placeholder { color: #888; }
body.dark-mode .local-desc-box { background: #1b2a1b; border-color: #2d4a2d; }
body.dark-mode .quick-fact-box { background: #2a2516; border-left-color: #f9a825; }
body.dark-mode .quick-fact-box-zh { background: #2a2516; border-left-color: #fbc02d; }
body.dark-mode .quick-fact-label { background: #3d3520; color: #ffd54f; }
body.dark-mode .quick-fact-label-zh { background: #3d3020; color: #ffcc80; }
body.dark-mode .quick-fact-text { color: #bbb; }
body.dark-mode .lang-en { background: #0d2137; border-color: #1565c0; color: #64b5f6; }
body.dark-mode .lang-zh { background: #2a1010; border-color: #c62828; color: #ef9a9a; }
body.dark-mode .lang-local { background: #102010; border-color: #2e7d32; color: #81c784; }
body.dark-mode .no-results { color: #666; }

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
        <button class="view-btn" id="darkBtn" title="Toggle dark mode" style="background:rgba(255,255,255,0.1)">&#9681;</button>
        <input type="text" class="search-box" placeholder="Search wallpapers..." id="searchBox" />
    </div>
</div>

<div class="tabs-container" id="tabsContainer">
    <div class="tabs" id="tabsBar"></div>
</div>

<div class="update-time">Last updated: __UPDATE_TIME__</div>

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
var ALL_IMAGES = __ALL_IMAGES__;

var ALL_MARKETS = __ALL_MARKETS__;
'''

TEMPLATE_TAIL = r'''
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

    // Primary description section
    if (img.desc) {
        contentHtml += '<div class="desc-section">';
        if (img.hasEnglish) {
            contentHtml += '<div class="lang-label lang-en">English</div><br>';
        } else {
            var langMap = {"de":"Deutsch","fr":"Francais","it":"Italiano","es":"Espanol","pt":"Portugues","ja":"日本語","zh":"中文","en":"English"};
            var langName = langMap[img.descLang] || img.descLang || "English";
            contentHtml += '<div class="lang-label lang-local">' + langName + '</div><br>';
        }
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
    document.getElementById('darkBtn').addEventListener('click', function() {
        document.body.classList.toggle('dark-mode');
        try { localStorage.setItem('bing-dark', document.body.classList.contains('dark-mode') ? '1' : '0'); } catch(e) {}
    });
    try { if (localStorage.getItem('bing-dark') === '1') document.body.classList.add('dark-mode'); } catch(e) {}
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
</html>
'''


def build_html(images_json, markets_json, update_time):
    """使用内嵌模板构建完整 HTML"""
    html = TEMPLATE_HEAD.replace('__ALL_IMAGES__', images_json)
    html = html.replace('__ALL_MARKETS__', markets_json)
    html = html.replace('__UPDATE_TIME__', update_time)
    html += TEMPLATE_TAIL
    return html

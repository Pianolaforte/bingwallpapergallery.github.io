#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bing Daily Wallpaper Auto Updater
自动获取必应每日壁纸并更新HTML页面
"""

import requests
import json
from datetime import datetime, timedelta
import os

# 必应 API 端点
BING_API_URL = "https://www.bing.com/HPImageArchive.aspx?format=js&idx={}&n=1&mkt=en-US"

def fetch_bing_image(index=0):
    """
    获取必应壁纸数据
    index: 0=今天, 1=昨天, 2=前天, 等等
    """
    try:
        url = BING_API_URL.format(index)
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        images = data.get('images', [])
        return images[0] if images else None
    except Exception as e:
        print(f"❌ Error fetching wallpaper (index {index}): {e}")
        return None

def get_image_url(image_data):
    """获取高质量图片 URL"""
    base_url = "https://www.bing.com"
    url_base = image_data.get('url', '')
    return base_url + url_base if url_base else None

def fetch_multiple_wallpapers(count=6):
    """获取多张壁纸"""
    images_data = []
    for i in range(count):
        img = fetch_bing_image(i)
        if img:
            images_data.append(img)
            print(f"✅ Fetched wallpaper {i+1}/{count}")
        else:
            print(f"⚠️  Failed to fetch wallpaper {i+1}")
    return images_data

def generate_card_html(image, index):
    """生成单个卡片 HTML"""
    title = image.get('title', 'Unknown Title')
    copyright_text = image.get('copyright', 'Unknown')
    description = image.get('tooltip', image.get('copyright', ''))
    
    # 从 copyrightlink 中提取日期信息
    copyright_link = image.get('copyrightlink', '')
    
    # 获取图片 URL
    image_url = get_image_url(image)
    if not image_url:
        return ""
    
    # 构建下载链接
    uhd_url = image_url + "&w=3840&h=2160"
    h1200_url = image_url + "&w=1920&h=1200"
    h1080_url = image_url + "&w=1920&h=1080"
    
    # 获取 startdate（YYYYMMDD 格式）
    start_date_str = image.get('startdate', '')
    if start_date_str and len(start_date_str) == 8:
        try:
            date_obj = datetime.strptime(start_date_str, '%Y%m%d')
            formatted_date = date_obj.strftime('%B %d, %Y')
        except:
            formatted_date = start_date_str
    else:
        formatted_date = datetime.now().strftime('%B %d, %Y')
    
    card_html = f"""            <!-- Card {index + 1} -->
            <div class="card">
                <div class="card-image">
                    <img src="{image_url}" alt="{title}" loading="lazy">
                </div>
                <div class="card-content">
                    <div class="card-date">{formatted_date}</div>
                    <div class="card-title">{title}</div>
                    <div class="card-desc">{description[:100]}...</div>
                    <div class="card-copyright">© {copyright_text}</div>
                    <div class="card-downloads">
                        <a href="{uhd_url}" class="dl-btn uhd-btn" title="Ultra HD">UHD ⬇</a>
                        <a href="{h1200_url}" class="dl-btn h1200-btn" title="1200p">1200p ⬇</a>
                        <a href="{h1080_url}" class="dl-btn h1080-btn" title="1080p">1080p ⬇</a>
                    </div>
                </div>
            </div>
"""
    return card_html

def generate_html(images_data):
    """生成完整 HTML 页面"""
    # 北京时间
    beijing_tz_offset = timedelta(hours=8)
    beijing_now = datetime.utcnow() + beijing_tz_offset
    update_time = beijing_now.strftime('%Y-%m-%d %H:%M:%S') + ' (Beijing Time)'
    
    # 生成卡片
    cards_html = ""
    for idx, image in enumerate(images_data):
        card = generate_card_html(image, idx)
        if card:
            cards_html += card
    
    # 完整 HTML 模板
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bing Daily Wallpaper Gallery - Auto Updated</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/css/flag-icons.min.css">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%);
            color: #333;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1a2744 0%, #2c3e50 100%);
            color: white;
            padding: 0 24px;
            height: 64px;
            display: flex;
            align-items: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        .logo-text {{
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
        
        .update-time {{
            text-align: center;
            padding: 14px 16px;
            font-size: 13px;
            color: #555;
            background: #fff;
            border-bottom: 1px solid #e0e0e0;
            font-weight: 500;
        }}
        
        .status-badge {{
            display: inline-block;
            background: #4caf50;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            margin-left: 8px;
        }}
        
        .main {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px;
        }}
        
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }}
        
        .card {{
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: all 0.3s cubic-bezier(0.23, 1, 0.320, 1);
            cursor: pointer;
            border: 1px solid #f0f0f0;
        }}
        
        .card:hover {{
            box-shadow: 0 12px 32px rgba(0,0,0,0.15);
            transform: translateY(-4px);
        }}
        
        .card-image {{
            width: 100%;
            height: 240px;
            overflow: hidden;
            background: linear-gradient(135deg, #e0e0e0 0%, #f0f0f0 100%);
        }}
        
        .card-image img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.4s cubic-bezier(0.23, 1, 0.320, 1);
        }}
        
        .card:hover .card-image img {{
            transform: scale(1.08);
        }}
        
        .card-content {{
            padding: 18px;
        }}
        
        .card-date {{
            font-size: 12px;
            color: #999;
            margin-bottom: 8px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}
        
        .card-title {{
            font-size: 17px;
            font-weight: 700;
            color: #1a2744;
            line-height: 1.4;
            margin-bottom: 10px;
            min-height: 50px;
        }}
        
        .card-desc {{
            font-size: 13px;
            color: #666;
            line-height: 1.6;
            margin-bottom: 12px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            min-height: 32px;
        }}
        
        .card-copyright {{
            font-size: 12px;
            color: #999;
            font-style: italic;
            margin-bottom: 14px;
            min-height: 18px;
        }}
        
        .card-downloads {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        
        .dl-btn {{
            display: inline-flex;
            align-items: center;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            text-decoration: none;
            color: white;
            transition: all 0.2s;
            border: none;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        }}
        
        .dl-btn:hover {{
            opacity: 0.95;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        
        .dl-btn:active {{
            transform: translateY(0);
        }}
        
        .uhd-btn {{ background: linear-gradient(135deg, #4caf50 0%, #45a049 100%); }}
        .h1200-btn {{ background: linear-gradient(135deg, #2196f3 0%, #1976d2 100%); }}
        .h1080-btn {{ background: linear-gradient(135deg, #607d8b 0%, #455a64 100%); }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
            border-top: 1px solid #e0e0e0;
        }}
        
        @media (max-width: 768px) {{
            .gallery {{
                grid-template-columns: 1fr;
                gap: 16px;
            }}
            .header {{
                height: 56px;
                padding: 0 16px;
            }}
            .logo-text {{
                font-size: 18px;
            }}
            .main {{
                padding: 16px;
            }}
            .card-title {{
                font-size: 15px;
                min-height: 45px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-text">📸 Bing Daily Wallpaper Gallery<span class="status-badge">AUTO</span></div>
    </div>
    
    <div class="update-time">✨ Last auto-updated: {update_time}</div>
    
    <div class="main">
        <div class="gallery">
{cards_html}        </div>
    </div>
    
    <div class="footer">
        <p>🤖 This page is automatically updated daily at 8:00 AM Beijing Time using GitHub Actions</p>
        <p>📝 Data fetched from Bing Daily Wallpaper API</p>
    </div>
</body>
</html>
"""
    return html_content

def main():
    """主函数"""
    print("🚀 Starting automatic wallpaper update...")
    print("⏰ Beijing Time:", (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S'))
    
    # 获取壁纸
    images = fetch_multiple_wallpapers(6)
    
    if not images:
        print("❌ Failed to fetch any wallpapers")
        return False
    
    print(f"✅ Successfully fetched {len(images)} wallpapers")
    
    # 生成 HTML
    html = generate_html(images)
    
    # 保存文件
    try:
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✅ index.html updated successfully!")
        return True
    except Exception as e:
        print(f"❌ Error writing file: {e}")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)

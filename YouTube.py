#!/usr/bin/env python3
"""
YouTube M3U8 Generator - Cookie Bypass Version
"""

import yt_dlp
import json
import re
import sys
import os
from datetime import datetime
import urllib.parse

def clean_filename(name):
    """Güvenli dosya adı"""
    if not name:
        return "youtube_stream"
    name = re.sub(r'[^\w\s\-_]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name[:40]

def extract_with_retry(url, use_cookies=False, cookie_file=None):
    """YT-DLP ile veri çek (yeniden denemeli)"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': False,
        'extract_flat': False,
        'ignoreerrors': True,
        
        # Bot algılamayı azaltan ayarlar
        'throttled_rate': '1M',
        'sleep_interval_requests': 2,
        'sleep_interval': 5,
        'max_sleep_interval': 10,
        
        # User agent ve header ayarları
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    }
    
    # Cookie desteği
    if use_cookies and cookie_file and os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file
        print(f"🍪 Using cookies from: {cookie_file}")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                print("❌ No info extracted")
                return None
            
            result = {
                'id': info.get('id', 'unknown'),
                'title': info.get('title', 'YouTube Live'),
                'channel': info.get('uploader', 'Unknown'),
                'is_live': info.get('is_live', False),
                'hls_urls': []
            }
            
            # Formatları ara
            formats = info.get('formats', [])
            hls_count = 0
            
            for fmt in formats:
                format_url = fmt.get('url', '')
                protocol = str(fmt.get('protocol', '')).lower()
                
                # HLS/M3U8 URL'lerini bul
                is_hls = ('hls' in protocol or 
                         'm3u8' in format_url or 
                         'manifest.googlevideo.com' in format_url)
                
                if is_hls and format_url:
                    format_data = {
                        'url': format_url,
                        'format_id': fmt.get('format_id', ''),
                        'height': fmt.get('height', 0),
                        'width': fmt.get('width', 0),
                        'fps': fmt.get('fps', 30),
                        'vcodec': fmt.get('vcodec', 'unknown'),
                        'acodec': fmt.get('acodec', 'unknown'),
                    }
                    result['hls_urls'].append(format_data)
                    hls_count += 1
            
            print(f"📊 Found {hls_count} streams")
            return result
            
    except Exception as e:
        print(f"❌ Extraction error: {str(e)[:200]}")
        return None

def generate_m3u8(stream_info, name=None):
    """M3U8 oluştur"""
    if not stream_info or not stream_info['hls_urls']:
        print("⚠️ No streams to create M3U8")
        return None
    
    # Dosya adı
    if name:
        base_name = clean_filename(name)
    else:
        base_name = clean_filename(stream_info['title'])
    
    stream_id = stream_info['id'][:8]
    filename = f"{base_name}_{stream_id}.m3u8"
    
    # M3U8 içeriği
    lines = [
        '#EXTM3U',
        f'#EXT-X-VERSION:3',
        f'# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'# Title: {stream_info["title"]}',
        f'# Channel: {stream_info["channel"]}',
        '#EXT-X-INDEPENDENT-SEGMENTS',
        ''
    ]
    
    # Stream'leri sırala
    streams = sorted(stream_info['hls_urls'], key=lambda x: x.get('height', 0))
    
    for stream in streams:
        height = stream.get('height', 0)
        width = stream.get('width', 0)
        fps = stream.get('fps', 30)
        
        # Bandwidth hesapla
        if height <= 144:
            bandwidth = 250000
        elif height <= 240:
            bandwidth = 500000
        elif height <= 360:
            bandwidth = 1000000
        elif height <= 480:
            bandwidth = 1500000
        elif height <= 720:
            bandwidth = 3000000
        else:
            bandwidth = 5000000
        
        vcodec = stream.get('vcodec', 'avc1.4d402a').split('.')[0]
        acodec = stream.get('acodec', 'mp4a.40.2').split('.')[0]
        
        stream_line = f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},CODECS="{acodec},{vcodec}"'
        
        if height and width:
            stream_line += f',RESOLUTION={width}x{height}'
        
        stream_line += f',FRAME-RATE={fps},VIDEO-RANGE=SDR'
        lines.append(stream_line)
        lines.append(stream['url'])
        lines.append('')
    
    # Dosyaya yaz
    os.makedirs('playlists', exist_ok=True)
    filepath = os.path.join('playlists', filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Created: {filename}")
    print(f"   Streams: {len(streams)}")
    
    # Metadata
    metadata = {
        'generated': datetime.now().isoformat(),
        'url': 'YouTube Live',
        'streams': len(streams),
        'resolutions': sorted(set(s.get('height', 0) for s in streams))
    }
    
    with open(f'playlists/{filename.replace(".m3u8", ".json")}', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return filename

def main():
    """Ana program"""
    print("="*60)
    print("YouTube M3U8 Generator (Fixed)")
    print("="*60)
    
    # Argümanları işle
    url = None
    use_cookies = False
    cookie_file = None
    
    if len(sys.argv) > 1:
        i = 1
        while i < len(sys.argv):
            if sys.argv[i] == '--url' and i+1 < len(sys.argv):
                url = sys.argv[i+1]
                i += 2
            elif sys.argv[i] == '--cookies' and i+1 < len(sys.argv):
                cookie_file = sys.argv[i+1]
                use_cookies = True
                i += 2
            elif sys.argv[i] == '--test':
                url = "https://www.youtube.com/live/na_jT2Q1rfA"
                i += 1
            else:
                i += 1
    
    if not url:
        url = "https://www.youtube.com/live/na_jT2Q1rfA"
        print(f"ℹ️ Using default URL: {url}")
    
    print(f"🎯 Target: {url}")
    
    # Veriyi çek
    stream_info = extract_with_retry(url, use_cookies, cookie_file)
    
    if stream_info:
        # M3U8 oluştur
        filename = generate_m3u8(stream_info, "HalkTV")
        
        if filename:
            print(f"\n✅ SUCCESS: M3U8 file created!")
            print(f"📁 File: playlists/{filename}")
        else:
            print("\n❌ FAILED: Could not create M3U8")
    else:
        print("\n❌ FAILED: Could not extract stream info")
        print("💡 Solution: Use --cookies option with a cookies.txt file")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()

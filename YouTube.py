#!/usr/bin/env python3
"""
YouTube Canlı Yayın → M3U8 Dönüştürücü
GitHub Actions için otomatik mod
"""

import yt_dlp
import json
import re
import sys
import os
from datetime import datetime

def clean_filename(name):
    """Dosya adı için güvenli karakterlere çevir"""
    if not name:
        return "youtube_stream"
    name = re.sub(r'[^\w\s\-_]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name[:50]

def extract_live_stream_info(url):
    """YouTube canlı yayın bilgilerini çıkar"""
    print(f"🔍 YouTube analiz ediliyor: {url}")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            result = {
                'id': info.get('id', 'unknown'),
                'title': info.get('title', 'YouTube Live Stream'),
                'channel': info.get('uploader', 'Unknown Channel'),
                'is_live': info.get('is_live', False),
                'view_count': info.get('view_count', 0),
                'duration': info.get('duration', 0),
                'hls_urls': []
            }
            
            # HLS formatlarını bul
            formats = info.get('formats', [])
            hls_count = 0
            
            for fmt in formats:
                protocol = str(fmt.get('protocol', '')).lower()
                url = fmt.get('url', '')
                
                if ('hls' in protocol or 'm3u8' in protocol or 
                    'm3u8' in url or 'googlevideo.com' in url):
                    
                    format_data = {
                        'url': url,
                        'format_id': fmt.get('format_id', 'N/A'),
                        'height': fmt.get('height', 0),
                        'width': fmt.get('width', 0),
                        'fps': fmt.get('fps', 30),
                        'vcodec': fmt.get('vcodec', 'avc1.4d402a'),
                        'acodec': fmt.get('acodec', 'mp4a.40.2'),
                        'tbr': fmt.get('tbr', 0),  # bitrate
                    }
                    
                    result['hls_urls'].append(format_data)
                    hls_count += 1
            
            print(f"✅ {hls_count} HLS stream bulundu")
            return result
            
    except Exception as e:
        print(f"❌ Hata: {str(e)}")
        return None

def generate_m3u8_playlist(stream_info, custom_name=None):
    """M3U8 playlist oluştur"""
    if not stream_info or not stream_info['hls_urls']:
        print("❌ HLS stream bulunamadı")
        return None
    
    # Dosya adını belirle
    if custom_name:
        base_name = clean_filename(custom_name)
    else:
        base_name = clean_filename(stream_info['title'])
    
    stream_id = stream_info['id'][:10]  # ID'yi kısalt
    filename = f"{base_name}_{stream_id}.m3u8"
    
    print(f"📝 M3U8 oluşturuluyor: {filename}")
    
    # M3U8 içeriği
    lines = [
        '#EXTM3U',
        f'#EXT-X-VERSION:3',
        f'# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'# Title: {stream_info["title"]}',
        f'# Channel: {stream_info["channel"]}',
        f'# Live: {stream_info["is_live"]}',
        f'# Viewers: {stream_info["view_count"]}',
        '#EXT-X-INDEPENDENT-SEGMENTS',
        ''
    ]
    
    # Formatları çözünürlüğe göre sırala (düşükten yükseğe)
    streams = sorted(stream_info['hls_urls'], key=lambda x: x.get('height', 0))
    
    for stream in streams:
        height = stream.get('height', 0)
        width = stream.get('width', 0)
        fps = stream.get('fps', 30)
        tbr = stream.get('tbr', 0)
        vcodec = stream.get('vcodec', 'avc1.4d402a')
        acodec = stream.get('acodec', 'mp4a.40.2')
        
        # Bandwidth hesapla
        if tbr > 0:
            bandwidth = int(tbr * 1000)
        elif height > 0:
            bandwidth = height * 150000  # 150kbps per pixel height
        else:
            bandwidth = 500000  # Varsayılan 500kbps
        
        # Codec temizleme
        vcodec_clean = vcodec.split('.')[0] if '.' in vcodec else vcodec
        acodec_clean = acodec.split('.')[0] if '.' in acodec else acodec
        
        # Stream bilgi satırı
        stream_line = f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},CODECS="{acodec_clean},{vcodec_clean}"'
        
        if height and width:
            stream_line += f',RESOLUTION={width}x{height}'
        
        stream_line += f',FRAME-RATE={fps},VIDEO-RANGE=SDR,CLOSED-CAPTIONS=NONE'
        
        lines.append(stream_line)
        lines.append(stream['url'])
        lines.append('')
    
    content = '\n'.join(lines)
    
    # Dosyaya yaz
    os.makedirs('playlists', exist_ok=True)
    filepath = os.path.join('playlists', filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ M3U8 oluşturuldu: {filename}")
    print(f"   📊 {len(streams)} stream eklendi")
    
    if streams:
        resolutions = sorted(set(s.get('height', 0) for s in streams))
        print(f"   📏 Çözünürlükler: {', '.join(str(r) for r in resolutions if r > 0)}p")
    
    return filename

def process_channel(url, name=None):
    """Tek kanal işle"""
    print(f"\n{'='*60}")
    print(f"🎬 İŞLENİYOR: {name if name else 'YouTube Stream'}")
    print(f"🔗 URL: {url}")
    print(f"{'='*60}")
    
    # URL formatını kontrol et
    if 'youtube.com/live/' not in url and 'youtu.be/' not in url:
        if 'youtube.com/watch?v=' in url:
            # Normal video URL'sini live'a çevir
            video_id = url.split('v=')[1].split('&')[0]
            url = f"https://www.youtube.com/live/{video_id}"
            print(f"📝 URL düzeltildi: {url}")
        else:
            print("⚠️  Uyarı: Standart YouTube canlı URL formatı değil")
    
    # Stream bilgilerini al
    stream_info = extract_live_stream_info(url)
    
    if not stream_info:
        print("❌ Stream bilgileri alınamadı")
        return False
    
    if not stream_info['hls_urls']:
        print("❌ HLS streamleri bulunamadı")
        print("   YouTube bu stream için HLS sağlamıyor olabilir")
        return False
    
    # M3U8 oluştur
    m3u8_file = generate_m3u8_playlist(stream_info, name)
    
    if m3u8_file:
        # Metadata dosyası oluştur
        metadata = {
            'generated_at': datetime.now().isoformat(),
            'original_url': url,
            'channel_name': name,
            'stream_info': {
                'id': stream_info['id'],
                'title': stream_info['title'],
                'channel': stream_info['channel'],
                'is_live': stream_info['is_live'],
                'view_count': stream_info['view_count'],
                'stream_count': len(stream_info['hls_urls']),
                'resolutions': sorted(set(s.get('height', 0) for s in stream_info['hls_urls']))
            },
            'generator': 'YouTube-M3U8-Generator v1.0'
        }
        
        metadata_file = f"playlists/{m3u8_file.replace('.m3u8', '.json')}"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"📁 Metadata kaydedildi: {metadata_file}")
        return True
    
    return False

def batch_process(file_path):
    """Toplu işlem - channels.txt dosyasını işle"""
    print(f"\n📦 TOPLU İŞLEM MODU")
    print(f"📄 Dosya: {file_path}")
    print(f"{'='*60}")
    
    if not os.path.exists(file_path):
        print(f"❌ Dosya bulunamadı: {file_path}")
        return
    
    success_count = 0
    fail_count = 0
    processed_channels = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    total_lines = len([l for l in lines if l.strip() and not l.startswith('#')])
    print(f"📋 Toplam {total_lines} kanal bulundu")
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        
        # Boş satır ve yorumları atla
        if not line or line.startswith('#'):
            continue
        
        # Format: name|url veya sadece url
        parts = line.split('|')
        if len(parts) >= 2:
            name, url = parts[0].strip(), parts[1].strip()
        else:
            url = line
            name = None
        
        print(f"\n[{success_count + fail_count + 1}/{total_lines}] {name if name else url}")
        
        try:
            if process_channel(url, name):
                success_count += 1
                processed_channels.append({'name': name, 'url': url, 'status': 'success'})
            else:
                fail_count += 1
                processed_channels.append({'name': name, 'url': url, 'status': 'failed'})
                
        except Exception as e:
            print(f"❌ İşlem hatası: {str(e)}")
            fail_count += 1
            processed_channels.append({'name': name, 'url': url, 'status': 'error', 'error': str(e)})
    
    # Sonuç raporu
    print(f"\n{'='*60}")
    print("📊 İŞLEM SONUÇLARI")
    print(f"{'='*60}")
    print(f"✅ Başarılı: {success_count}")
    print(f"❌ Başarısız: {fail_count}")
    print(f"📁 Toplam: {success_count + fail_count}")
    
    # Sonuçları JSON'a kaydet
    results_file = f"playlists/batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results = {
        'timestamp': datetime.now().isoformat(),
        'total': success_count + fail_count,
        'success': success_count,
        'failed': fail_count,
        'channels': processed_channels
    }
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"📋 Sonuçlar kaydedildi: {results_file}")
    
    return success_count > 0

def main():
    """Ana fonksiyon - GitHub Actions için otomatik mod"""
    print("=" * 60)
    print("🎬 YouTube Canlı → M3U8 Dönüştürücü")
    print("=" * 60)
    
    # Komut satırı argümanlarını kontrol et
    if len(sys.argv) > 1:
        if sys.argv[1] == "--batch" and len(sys.argv) > 2:
            # Toplu işlem modu
            batch_process(sys.argv[2])
            
        elif sys.argv[1] == "--url" and len(sys.argv) > 2:
            # Tek URL modu
            url = sys.argv[2]
            name = sys.argv[3] if len(sys.argv) > 3 else None
            process_channel(url, name)
            
        elif sys.argv[1] == "--test":
            # Test modu
            print("🧪 TEST MODU: Halk TV")
            test_url = "https://www.youtube.com/live/na_jT2Q1rfA"
            process_channel(test_url, "HalkTV_Test")
            
        elif sys.argv[1] == "--help":
            # Yardım
            print("Kullanım:")
            print("  python YouTube.py --batch channels.txt    # Toplu işlem")
            print("  python YouTube.py --url URL [NAME]        # Tek kanal")
            print("  python YouTube.py --test                  # Test (Halk TV)")
            print("  python YouTube.py --help                  # Bu yardım")
            print("\nÖrnek channels.txt formatı:")
            print("  HalkTV|https://www.youtube.com/live/na_jT2Q1rfA")
            print("  TRT1|https://www.youtube.com/live/TRT1_LIVE_ID")
            print("  https://www.youtube.com/live/OTHER_ID     # İsimsiz")
            
        else:
            print(f"❌ Bilinmeyen argüman: {sys.argv[1]}")
            print("   --help ile yardım alın")
    
    else:
        # Hiç argüman yoksa test modunda çalış
        print("ℹ️  Argüman yok, test modunda çalıştırılıyor...")
        print("   Kullanım: python YouTube.py --help")
        print("\n🧪 TEST MODU BAŞLIYOR...")
        test_url = "https://www.youtube.com/live/na_jT2Q1rfA"
        process_channel(test_url, "HalkTV_Test")

if __name__ == "__main__":
    # GitHub Actions için gerekli klasörleri oluştur
    os.makedirs('playlists', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Programı başlat
    main()
    
    print("\n" + "=" * 60)
    print("✨ Program tamamlandı")
    print("=" * 60)

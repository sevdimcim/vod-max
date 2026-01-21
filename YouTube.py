import yt_dlp
import re
from datetime import datetime
import json

def extract_youtube_live_m3u8(youtube_url):
    """
    YouTube canlı yayınından M3U8 playlistini çıkarır
    """
    print(f"🔍 YouTube canlı yayın analiz ediliyor: {youtube_url}")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'youtube_include_dash_manifest': False,
        'youtube_include_hls_manifest': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Video bilgilerini al
            info = ydl.extract_info(youtube_url, download=False)
            
            # Canlı yayın kontrolü
            if not info.get('is_live'):
                print("⚠ UYARI: Bu bir canlı yayın değil!")
                # Yine de devam edebiliriz
                
            video_title = info.get('title', 'Bilinmeyen_Yayin')
            video_id = info.get('id', 'unknown')
            channel = info.get('uploader', 'Bilinmeyen_Kanal')
            
            print(f"📺 Kanal: {channel}")
            print(f"🎬 Başlık: {video_title}")
            print(f"🔗 Video ID: {video_id}")
            print(f"📊 Kalite seçenekleri taranıyor...")
            
            # HLS manifest URL'lerini bul
            m3u8_urls = []
            
            # Formatları kontrol et
            formats = info.get('formats', [])
            
            for f in formats:
                if f.get('protocol') == 'm3u8_native' or 'hls' in f.get('protocol', ''):
                    format_info = {
                        'url': f.get('url', ''),
                        'format_id': f.get('format_id', ''),
                        'format_note': f.get('format_note', ''),
                        'height': f.get('height', 0),
                        'width': f.get('width', 0),
                        'tbr': f.get('tbr', 0),  # bitrate
                        'vcodec': f.get('vcodec', ''),
                        'acodec': f.get('acodec', ''),
                        'fps': f.get('fps', 0),
                        'dynamic_range': f.get('dynamic_range', 'SDR'),
                    }
                    m3u8_urls.append(format_info)
            
            # URL yoksa, manifest'i manuel oluştur
            if not m3u8_urls:
                print("M3U8 URL'leri bulunamadı, manifest oluşturuluyor...")
                m3u8_urls = generate_hls_manifest_from_info(info)
            
            # M3U8 playlist oluştur
            playlist_content = generate_m3u8_playlist(m3u8_urls, video_title, channel)
            
            # Dosyaya kaydet
            safe_title = re.sub(r'[^\w\-_]', '_', video_title)[:50]
            filename = f"{safe_title}_{video_id}.m3u8"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(playlist_content)
            
            print(f"\n✅ M3U8 playlist oluşturuldu: {filename}")
            print(f"📁 Toplam {len(m3u8_urls)} kalite seçeneği eklendi")
            
            # Ek bilgileri JSON olarak da kaydet
            save_stream_info(info, m3u8_urls, filename.replace('.m3u8', '.json'))
            
            return filename, playlist_content
            
    except Exception as e:
        print(f"❌ Hata oluştu: {str(e)}")
        return None, None

def generate_hls_manifest_from_info(info):
    """
    Video bilgilerinden HLS manifest URL'leri oluştur
    """
    video_id = info.get('id', '')
    formats = []
    
    # YouTube HLS manifest URL şablonu
    base_patterns = [
        f"https://manifest.googlevideo.com/api/manifest/hls_playlist/expire/*/ei/*/id/{video_id}/itag/{{itag}}/*",
        f"https://rr*.googlevideo.com/videoplayback/*/id/{video_id}/itag/{{itag}}/*",
    ]
    
    # Standart format ID'leri (YouTube HLS için)
    hls_formats = [
        {'itag': '91', 'height': 144, 'note': '144p'},
        {'itag': '92', 'height': 240, 'note': '240p'},
        {'itag': '93', 'height': 360, 'note': '360p'},
        {'itag': '94', 'height': 480, 'note': '480p'},
        {'itag': '95', 'height': 720, 'note': '720p'},
        {'itag': '96', 'height': 1080, 'note': '1080p'},
        {'itag': '300', 'height': 720, 'note': '720p60'},
        {'itag': '301', 'height': 1080, 'note': '1080p60'},
    ]
    
    for fmt in hls_formats:
        formats.append({
            'url': f"https://manifest.googlevideo.com/api/manifest/hls_playlist/id/{video_id}/itag/{fmt['itag']}/source/yt_live_broadcast/playlist_type/LIVE",
            'format_id': fmt['itag'],
            'format_note': fmt['note'],
            'height': fmt['height'],
            'width': fmt['height'] * 16 // 9,
            'vcodec': 'avc1.4D40XX',
            'acodec': 'mp4a.40.2',
            'dynamic_range': 'SDR',
        })
    
    return formats

def generate_m3u8_playlist(formats, title, channel):
    """
    M3U8 playlist içeriğini oluştur
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    playlist = [
        '#EXTM3U',
        f'# Generated: {now}',
        f'# Title: {title}',
        f'# Channel: {channel}',
        f'# Sources: YouTube Live Stream',
        '#EXT-X-INDEPENDENT-SEGMENTS',
        ''
    ]
    
    # Formatları çözünürlüğe göre sırala (düşükten yükseğe)
    formats.sort(key=lambda x: x.get('height', 0))
    
    for fmt in formats:
        height = fmt.get('height', 0)
        width = fmt.get('width', 0)
        tbr = fmt.get('tbr', 0) or 500000  # Varsayılan bitrate
        vcodec = fmt.get('vcodec', 'avc1.4D40XX').split('.')[0]
        acodec = fmt.get('acodec', 'mp4a.40.2').split('.')[0]
        fps = fmt.get('fps', 30)
        dynamic_range = fmt.get('dynamic_range', 'SDR')
        
        # BANDWIDTH hesapla (bitrate * 1.2 güvenlik faktörü)
        bandwidth = int(tbr * 1.2) if tbr > 0 else height * 2000
        
        # CODECS formatı
        codecs_str = f'{acodec},{vcodec}'
        
        # EXT-X-STREAM-INF satırı
        stream_info = f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},CODECS="{codecs_str}"'
        
        if height and width:
            stream_info += f',RESOLUTION={width}x{height}'
        
        stream_info += f',FRAME-RATE={fps},VIDEO-RANGE={dynamic_range},CLOSED-CAPTIONS=NONE'
        
        playlist.append(stream_info)
        playlist.append(fmt.get('url', ''))
        playlist.append('')
    
    return '\n'.join(playlist)

def save_stream_info(info, formats, json_filename):
    """Akış bilgilerini JSON olarak kaydet"""
    stream_data = {
        'metadata': {
            'title': info.get('title'),
            'id': info.get('id'),
            'channel': info.get('uploader'),
            'is_live': info.get('is_live', False),
            'duration': info.get('duration'),
            'view_count': info.get('view_count'),
            'timestamp': datetime.now().isoformat(),
        },
        'formats': formats,
        'generator': 'YouTube-Live-to-M3U8 v1.0',
    }
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(stream_data, f, indent=2, ensure_ascii=False)

def main():
    """Ana program"""
    print("=" * 60)
    print("YouTube Canlı Yayın → M3U8 Playlist Dönüştürücü")
    print("=" * 60)
    print("Amaç: YouTube canlı TV yayınlarını M3U8 formatına dönüştürmek")
    print("Örnek: https://www.youtube.com/live/na_jT2Q1rfA")
    print("=" * 60)
    
    while True:
        print("\n1. YouTube canlı yayın linkinden M3U8 oluştur")
        print("2. YouTube kanal linkinden canlı yayınları listele")
        print("3. Test (Halk TV örneği)")
        print("4. Çıkış")
        
        choice = input("\nSeçiminiz (1-4): ").strip()
        
        if choice == "1":
            url = input("YouTube canlı yayın URL'si: ").strip()
            if not url.startswith('http'):
                print("Geçerli bir URL girin!")
                continue
            
            filename, content = extract_youtube_live_m3u8(url)
            
            if filename and content:
                print(f"\n📋 Oluşturulan M3U8 içeriği:")
                print("-" * 40)
                # İlk 10 satırı göster
                lines = content.split('\n')
                for i, line in enumerate(lines[:15]):
                    print(line)
                if len(lines) > 15:
                    print(f"... ve {len(lines)-15} satır daha")
                print("-" * 40)
                print(f"✅ Dosya kaydedildi: {filename}")
        
        elif choice == "2":
            channel_url = input("YouTube kanal URL'si (@haber gibi): ").strip()
            list_channel_live_streams(channel_url)
        
        elif choice == "3":
            # Halk TV test
            test_url = "https://www.youtube.com/live/na_jT2Q1rfA"
            print(f"Test URL: {test_url}")
            filename, content = extract_youtube_live_m3u8(test_url)
        
        elif choice == "4":
            print("Program sonlandırılıyor...")
            break
        
        else:
            print("Geçersiz seçim!")

def list_channel_live_streams(channel_url):
    """Kanalda şu anda canlı yayın var mı kontrol et"""
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlistend': 20,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            
            if 'entries' in info:
                print(f"\n📺 Kanal: {info.get('title', 'Bilinmeyen')}")
                print("🔍 Canlı yayınlar aranıyor...")
                
                live_streams = []
                for entry in info['entries']:
                    if entry.get('live_status') == 'is_live':
                        live_streams.append(entry)
                
                if live_streams:
                    print(f"✅ {len(live_streams)} canlı yayın bulundu:")
                    for i, stream in enumerate(live_streams, 1):
                        stream_url = f"https://www.youtube.com/watch?v={stream['id']}"
                        print(f"{i}. {stream.get('title', 'Bilinmeyen')}")
                        print(f"   🔗 {stream_url}")
                        print(f"   👁️ {stream.get('view_count', 0)} izlenme")
                        print()
                else:
                    print("⚠ Şu anda canlı yayın bulunmuyor.")
            else:
                print("Kanal bilgileri alınamadı.")
                
    except Exception as e:
        print(f"Hata: {str(e)}")

if __name__ == "__main__":
    try:
        import yt_dlp
        main()
    except ImportError:
        print("yt-dlp kütüphanesi yüklü değil!")
        print("Kurulum: pip install yt-dlp")

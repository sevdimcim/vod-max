#!/usr/bin/env python3
"""
canlidizi14.com M3U8 Link Bulucu Bot
Twitter: @canlidizi14 gibi davranarak m3u8 linklerini çeker
"""

import os
import sys
import time
import re
import json
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CanliDiziM3U8Finder:
    def __init__(self, headless=True, chrome_driver_path=None):
        """
        M3U8 bulucu botu başlat
        
        Args:
            headless (bool): Headless modda çalıştır
            chrome_driver_path (str): ChromeDriver yolu
        """
        self.headless = headless
        self.chrome_driver_path = chrome_driver_path
        self.driver = None
        self.session = requests.Session()
        
        # Tarayıcı headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        self.session.headers.update(self.headers)
    
    def init_driver(self):
        """ChromeDriver başlat"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")  # Yeni headless mod
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(f"user-agent={self.headers['User-Agent']}")
        
        # Performans ve video için gerekli flags
        chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
        chrome_options.add_argument("--disable-features=PreloadMediaEngagementData,AutoplayIgnoreWebAudio,MediaEngagementBypassAutoplayPolicies")
        
        try:
            if self.chrome_driver_path and os.path.exists(self.chrome_driver_path):
                service = Service(executable_path=self.chrome_driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
            
            # Anti-bot detection için
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("ChromeDriver başlatıldı")
            return True
            
        except Exception as e:
            logger.error(f"ChromeDriver başlatılamadı: {e}")
            return False
    
    def close_driver(self):
        """Driver'ı kapat"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("ChromeDriver kapatıldı")
    
    def extract_m3u8_from_network_logs(self, timeout=30):
        """
        Network loglarında m3u8 ara
        
        Args:
            timeout (int): Bekleme süresi (saniye)
        
        Returns:
            str: m3u8 URL veya None
        """
        try:
            # Network loglarını al
            logs = self.driver.get_log('performance')
            
            m3u8_urls = set()
            
            for log_entry in logs:
                try:
                    log_data = json.loads(log_entry['message'])
                    message = log_data.get('message', {})
                    
                    if message.get('method') == 'Network.requestWillBeSent':
                        request = message.get('params', {}).get('request', {})
                        url = request.get('url', '')
                        
                        # m3u8 URL'lerini bul
                        if '.m3u8' in url:
                            # Twitter videosu veya direkt m3u8
                            if 'video.twimg.com' in url or url.endswith('.m3u8'):
                                m3u8_urls.add(url)
                    
                    elif message.get('method') == 'Network.responseReceived':
                        response = message.get('params', {}).get('response', {})
                        url = response.get('url', '')
                        
                        if '.m3u8' in url:
                            if 'video.twimg.com' in url or url.endswith('.m3u8'):
                                m3u8_urls.add(url)
                                
                except json.JSONDecodeError:
                    continue
            
            # Eğer bulunduysa en iyi olanı seç
            if m3u8_urls:
                for url in m3u8_urls:
                    if 'video.twimg.com' in url:
                        return url
                return list(m3u8_urls)[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Network logları analiz edilemedi: {e}")
            return None
    
    def extract_m3u8_from_page_source(self, html_content):
        """
        Sayfa kaynağında m3u8 ara
        
        Args:
            html_content (str): HTML içeriği
        
        Returns:
            str: m3u8 URL veya None
        """
        try:
            # Regex pattern'leri
            patterns = [
                r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',  # Direkt m3u8
                r'src=["\'](https?://video\.twimg\.com[^\s"\']*\.m3u8[^\s"\']*)["\']',  # Twitter videosu
                r'file["\']?\s*:\s*["\'](https?://[^\s"\']+\.m3u8[^\s"\']*)["\']',  # JS içinde
                r'["\'](https?://cdn\.traffmovie\.com[^\s"\']*\.m3u8[^\s"\']*)["\']',  # Traffmovie
                r'["\'](https?://canliplayer\.com[^\s"\']*\.m3u8[^\s"\']*)["\']',  # CanliPlayer
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                if matches:
                    for match in matches:
                        # URL'yi temizle
                        url = match.split('"')[0].split("'")[0].split('\\')[0].strip()
                        if url.endswith('.m3u8'):
                            return url
            
            # BeautifulSoup ile script tag'larında ara
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Script tag'ları
            for script in soup.find_all('script'):
                if script.string:
                    for pattern in patterns:
                        matches = re.findall(pattern, script.string, re.IGNORECASE)
                        if matches:
                            for match in matches:
                                url = match.split('"')[0].split("'")[0].split('\\')[0].strip()
                                if url.endswith('.m3u8'):
                                    return url
            
            # iframe src'leri
            for iframe in soup.find_all('iframe'):
                src = iframe.get('src', '')
                if '.m3u8' in src:
                    return src
            
            return None
            
        except Exception as e:
            logger.error(f"Sayfa kaynağı analiz edilemedi: {e}")
            return None
    
    def check_twitter_video(self, url):
        """
        Twitter video linkini kontrol et
        
        Args:
            url (str): Twitter video URL'si
        
        Returns:
            str: m3u8 URL veya None
        """
        try:
            # Twitter video URL'sini düzenle
            if 'video.twimg.com' in url and not url.endswith('.m3u8'):
                # m3u8 versiyonunu oluştur
                base_url = url.split('?')[0]
                if '/vid/' in base_url:
                    # Twitter video formatı
                    m3u8_url = base_url + '.m3u8?tag=14'
                    return m3u8_url
            return url
        except:
            return None
    
    def get_m3u8_url(self, url, use_selenium=True, wait_time=10):
        """
        Ana fonksiyon: Verilen URL'den m3u8 linkini bul
        
        Args:
            url (str): CanliDizi bölüm URL'si
            use_selenium (bool): Selenium kullanılsın mı
            wait_time (int): Bekleme süresi
        
        Returns:
            dict: {'success': bool, 'm3u8_url': str, 'message': str, 'method': str}
        """
        result = {
            'success': False,
            'm3u8_url': None,
            'message': '',
            'method': '',
            'source_url': url
        }
        
        logger.info(f"URL aranıyor: {url}")
        
        # Önce requests ile dene
        try:
            logger.info("Requests ile deniyorum...")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            html_content = response.text
            
            # Sayfa kaynağında m3u8 ara
            m3u8_url = self.extract_m3u8_from_page_source(html_content)
            
            if m3u8_url:
                # Twitter video kontrolü
                m3u8_url = self.check_twitter_video(m3u8_url)
                
                result['success'] = True
                result['m3u8_url'] = m3u8_url
                result['message'] = 'Requests ile bulundu'
                result['method'] = 'requests'
                
                logger.info(f"M3U8 bulundu (requests): {m3u8_url}")
                return result
                
        except Exception as e:
            logger.warning(f"Requests başarısız: {e}")
        
        # Eğer Selenium kullanılacaksa
        if use_selenium and not self.driver:
            if not self.init_driver():
                result['message'] = 'Selenium başlatılamadı'
                return result
        
        if use_selenium and self.driver:
            try:
                logger.info("Selenium ile deniyorum...")
                
                # Sayfayı yükle
                self.driver.get(url)
                
                # Sayfanın yüklenmesini bekle
                time.sleep(3)
                
                # Iframe'leri kontrol et
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                logger.info(f"{len(iframes)} iframe bulundu")
                
                for iframe in iframes:
                    try:
                        # Iframe'e geç
                        self.driver.switch_to.frame(iframe)
                        time.sleep(2)
                        
                        # Iframe içindeki sayfa kaynağı
                        iframe_html = self.driver.page_source
                        
                        # Iframe içinde m3u8 ara
                        m3u8_url = self.extract_m3u8_from_page_source(iframe_html)
                        
                        if m3u8_url:
                            m3u8_url = self.check_twitter_video(m3u8_url)
                            
                            result['success'] = True
                            result['m3u8_url'] = m3u8_url
                            result['message'] = 'Selenium iframe içinde bulundu'
                            result['method'] = 'selenium_iframe'
                            
                            logger.info(f"M3U8 bulundu (iframe): {m3u8_url}")
                            return result
                            
                    except Exception as e:
                        logger.warning(f"Iframe analiz hatası: {e}")
                    finally:
                        # Ana frame'e geri dön
                        self.driver.switch_to.default_content()
                
                # Network loglarını kontrol et
                logger.info("Network logları analiz ediliyor...")
                time.sleep(wait_time)
                
                m3u8_url = self.extract_m3u8_from_network_logs()
                
                if m3u8_url:
                    m3u8_url = self.check_twitter_video(m3u8_url)
                    
                    result['success'] = True
                    result['m3u8_url'] = m3u8_url
                    result['message'] = 'Network loglarından bulundu'
                    result['method'] = 'selenium_network'
                    
                    logger.info(f"M3U8 bulundu (network): {m3u8_url}")
                    return result
                
                # Video elementlerini kontrol et
                video_elements = self.driver.find_elements(By.TAG_NAME, "video")
                for video in video_elements:
                    src = video.get_attribute("src")
                    if src and '.m3u8' in src:
                        result['success'] = True
                        result['m3u8_url'] = src
                        result['message'] = 'Video elementinden bulundu'
                        result['method'] = 'selenium_video'
                        return result
                
                result['message'] = 'Selenium ile m3u8 bulunamadı'
                
            except Exception as e:
                logger.error(f"Selenium hatası: {e}")
                result['message'] = f'Selenium hatası: {str(e)}'
        
        result['message'] = 'M3U8 URL bulunamadı'
        return result
    
    def test_with_multiple_methods(self, url):
        """
        Birden fazla metod deneyerek m3u8 bul
        
        Args:
            url (str): Test URL'si
        
        Returns:
            dict: Sonuçlar
        """
        methods = []
        
        # Method 1: Direct requests
        logger.info("Method 1: Direct requests")
        result1 = self.get_m3u8_url(url, use_selenium=False)
        methods.append(result1)
        
        if not result1['success']:
            # Method 2: Selenium normal
            logger.info("Method 2: Selenium normal")
            result2 = self.get_m3u8_url(url, use_selenium=True, wait_time=15)
            methods.append(result2)
            
            if not result2['success']:
                # Method 3: Sayfayı JavaScript ile manipüle et
                logger.info("Method 3: JavaScript manipulation")
                try:
                    if self.driver:
                        # Video player'ı tetikle
                        self.driver.execute_script("""
                            var videos = document.querySelectorAll('video');
                            videos.forEach(function(video) {
                                video.play();
                            });
                            
                            var iframes = document.querySelectorAll('iframe');
                            iframes.forEach(function(iframe) {
                                var src = iframe.src;
                                if (src.includes('video') || src.includes('player')) {
                                    console.log('Video iframe found:', src);
                                }
                            });
                        """)
                        
                        time.sleep(10)
                        
                        # Tekrar network loglarını kontrol et
                        m3u8_url = self.extract_m3u8_from_network_logs()
                        
                        if m3u8_url:
                            result3 = {
                                'success': True,
                                'm3u8_url': m3u8_url,
                                'message': 'JavaScript manipulation ile bulundu',
                                'method': 'js_manipulation',
                                'source_url': url
                            }
                            methods.append(result3)
                except Exception as e:
                    logger.error(f"JS manipulation hatası: {e}")
        
        # En iyi sonucu bul
        best_result = None
        for result in methods:
            if result['success']:
                best_result = result
                break
        
        if not best_result:
            best_result = {
                'success': False,
                'm3u8_url': None,
                'message': 'Tüm metodlar denendi, m3u8 bulunamadı',
                'method': 'all_failed',
                'source_url': url
            }
        
        return best_result
    
    def save_result(self, result, filename="result.json"):
        """Sonucu JSON olarak kaydet"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logger.info(f"Sonuç kaydedildi: {filename}")
        except Exception as e:
            logger.error(f"Sonuç kaydedilemedi: {e}")
    
    def __del__(self):
        """Destructor - driver'ı kapat"""
        self.close_driver()


def main():
    """Ana fonksiyon"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CanliDizi14 M3U8 Bulucu Bot')
    parser.add_argument('url', help='CanliDizi bölüm URL')
    parser.add_argument('--headless', action='store_true', default=True, help='Headless mod (default: True)')
    parser.add_argument('--driver-path', help='ChromeDriver yolu')
    parser.add_argument('--output', '-o', help='Çıktı dosyası (JSON)')
    parser.add_argument('--test-all', action='store_true', help='Tüm metodları dene')
    
    args = parser.parse_args()
    
    # Botu başlat
    finder = CanliDiziM3U8Finder(
        headless=args.headless,
        chrome_driver_path=args.driver_path
    )
    
    try:
        if args.test_all:
            logger.info("Tüm metodlar deneniyor...")
            result = finder.test_with_multiple_methods(args.url)
        else:
            result = finder.get_m3u8_url(args.url, use_selenium=True, wait_time=20)
        
        # Sonuçları göster
        print("\n" + "="*60)
        print("CANLIDIZI M3U8 BULUCU - SONUÇ")
        print("="*60)
        print(f"URL: {result['source_url']}")
        print(f"Başarılı: {'Evet' if result['success'] else 'Hayır'}")
        print(f"Metod: {result['method']}")
        print(f"Mesaj: {result['message']}")
        
        if result['success'] and result['m3u8_url']:
            print(f"\nM3U8 Linki:")
            print(result['m3u8_url'])
            
            # Linki test et
            print(f"\nLink test ediliyor...")
            try:
                test_resp = requests.head(result['m3u8_url'], timeout=5)
                print(f"HTTP Durumu: {test_resp.status_code}")
                if test_resp.status_code == 200:
                    print("✓ Link çalışıyor!")
                else:
                    print("⚠ Link çalışıyor ama HTTP kodu normal değil")
            except:
                print("✗ Link test edilemedi")
        else:
            print("\nM3U8 bulunamadı!")
        
        print("\n" + "="*60)
        
        # JSON çıktısı
        if args.output:
            finder.save_result(result, args.output)
        
        # Sonuç dosyasına yaz
        with open('m3u8_result.txt', 'w', encoding='utf-8') as f:
            f.write(f"URL: {args.url}\n")
            f.write(f"Success: {result['success']}\n")
            f.write(f"Method: {result['method']}\n")
            f.write(f"Message: {result['message']}\n")
            if result['m3u8_url']:
                f.write(f"\nM3U8 URL:\n{result['m3u8_url']}\n")
        
        return 0 if result['success'] else 1
        
    except KeyboardInterrupt:
        print("\nİşlem kullanıcı tarafından durduruldu.")
        return 130
    except Exception as e:
        print(f"\nKritik hata: {e}")
        return 1
    finally:
        finder.close_driver()


if __name__ == "__main__":
    sys.exit(main())

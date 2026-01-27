from playwright.sync_api import sync_playwright
import time

URL = "https://www.canlidizi14.com/kismetse-olur-askin-gucu-74-bolum-izle.html"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        page = context.new_page()

        print("Sayfa açılıyor...")
        page.goto(URL, wait_until="networkidle", timeout=60000)

        m3u8_links = set()

        def handle_request(request):
            url = request.url
            if ".m3u8" in url:
                print("\n🔥 M3U8 YAKALANDI 🔥")
                print(url)
                m3u8_links.add(url)

        page.on("request", handle_request)

        # fireplayer oynasın diye bekle
        time.sleep(20)

        if not m3u8_links:
            print("\n❌ M3U8 yakalanamadı")
        else:
            print("\n✅ TOPLAM BULUNAN:")
            for i, link in enumerate(m3u8_links, 1):
                print(f"{i}. {link}")

        browser.close()


if __name__ == "__main__":
    run()

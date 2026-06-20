"""
Script tu dong tao RSS feed tu trang theleader.vn/tai-chinh/
Chay dinh ky boi GitHub Actions, ghi ra file feed.xml
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import format_datetime
import re
import html

SOURCE_URL = "https://theleader.vn/tai-chinh/"
OUTPUT_FILE = "feed.xml"
MAX_ITEMS = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}


def fetch_html(url):
    resp = requests.get(url, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    return resp.text


def extract_articles(page_html, base_url):
    soup = BeautifulSoup(page_html, "html.parser")
    articles = []
    seen_links = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]

        # Bai viet tren theleader.vn co dang ...-dXXXXX.html
        if not re.search(r"-d\d+\.html$", href):
            continue

        title = a_tag.get_text(strip=True)
        if not title or len(title) < 8:
            continue

        if href.startswith("/"):
            href = "https://theleader.vn" + href
        elif not href.startswith("http"):
            continue

        if href in seen_links:
            continue
        seen_links.add(href)

        # Tim anh minh hoa: tim trong pham vi vai the lien quan gan link nay
        image_url = None
        img_tag = a_tag.find("img")
        if img_tag and img_tag.get("src"):
            image_url = img_tag["src"]
        else:
            # Quet nguoc vai the truoc do de tim block chua anh thumbnail
            node = a_tag
            for _ in range(4):
                node = node.find_previous(["a", "div", "figure"])
                if node is None:
                    break
                found_img = node.find("img")
                if found_img and found_img.get("src"):
                    image_url = found_img["src"]
                    break

        # Tim doan mo ta ngan ngay sau link (the <p> hoac the em ke tiep)
        description = ""
        parent = a_tag.find_parent()
        if parent:
            next_p = parent.find_next_sibling("p")
            if next_p:
                description = next_p.get_text(strip=True)

        articles.append({
            "title": title,
            "link": href,
            "image": image_url,
            "description": description,
        })

        if len(articles) >= MAX_ITEMS:
            break

    return articles


def escape_xml(text):
    if not text:
        return ""
    return html.escape(text, quote=True)


def build_rss(articles, source_url):
    now = format_datetime(datetime.now(timezone.utc))

    items_xml = []
    for art in articles:
        title = escape_xml(art["title"])
        link = escape_xml(art["link"])
        desc = escape_xml(art["description"])

        image_block = ""
        if art["image"]:
            image_block = f'<enclosure url="{escape_xml(art["image"])}" type="image/jpeg" />'

        item = f"""
    <item>
      <title>{title}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <description>{desc}</description>
      {image_block}
      <pubDate>{now}</pubDate>
    </item>"""
        items_xml.append(item)

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>TheLEADER - Tai chinh</title>
    <link>{source_url}</link>
    <atom:link href="{source_url}" rel="self" type="application/rss+xml" />
    <description>RSS tu dong tao tu trang Tai chinh - TheLEADER</description>
    <language>vi</language>
    <lastBuildDate>{now}</lastBuildDate>
{''.join(items_xml)}
  </channel>
</rss>"""
    return rss


def main():
    print(f"Dang tai trang: {SOURCE_URL}")
    page_html = fetch_html(SOURCE_URL)

    print("Dang phan tich bai viet...")
    articles = extract_articles(page_html, SOURCE_URL)
    print(f"Tim thay {len(articles)} bai viet")

    if not articles:
        raise SystemExit("Khong tim thay bai viet nao - co the cau truc trang da thay doi")

    rss_content = build_rss(articles, SOURCE_URL)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(rss_content)

    print(f"Da ghi file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

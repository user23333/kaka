import os
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from lxml import etree
from pyquery import PyQuery as pq

def utc_to_cst(utc):
    now = datetime.now(timezone.utc)
    candidates = []
    for year in (now.year - 1, now.year, now.year + 1):
        try:
            candidates.append(datetime.strptime(f"{year}-{utc}", "%Y-%d-%m, %H:%M").replace(tzinfo=timezone.utc))
        except ValueError:
            continue
    if not candidates:
        raise ValueError("Invalid forum date")
    utc_time = min(candidates, key=lambda value: abs(value - now))
    cst_time = utc_time.astimezone(timezone(timedelta(hours=8)))
    return cst_time.strftime("%Y-%m-%d %H:%M:%S")


def markdown_escape(text):
    if not text:
        return ""
    # https://github.com/mattcone/markdown-guide/blob/master/_basic-syntax/escaping-characters.md
    chars = ["\\", "`", "*", "_", "{", "}", "[", "]", "<", ">", "(", ")", "#", "+", "-", ".", "!", "|"]
    table = str.maketrans({char: f"&#{ord(char)};" for char in chars})
    return text.translate(table)


def fetch_blocks(v2):
    url = urlsplit(f'{v2}{time.time_ns()}')
    if url.scheme != 'https' or url.hostname != 'www.unknowncheats.me':
        raise ValueError('Unexpected V2 host')
    request = Request(f'http://127.0.0.1:8000{url.path}?{url.query}', headers={'x-hostname': url.hostname})
    with urlopen(request, timeout=180) as response:
        raw = response.read()
    root = etree.fromstring(raw, etree.XMLParser(resolve_entities=False, no_network=True))
    blocks = [root.xpath(f'string(//block[@blockid="{i}"])') for i in (1, 2, 3)]
    if not all(blocks):
        raise RuntimeError('V2 response did not contain all three blocks')
    return blocks


def fetch():
    v2 = os.getenv('V2')
    v3 = os.getenv('V3')
    missing = [name for name, value in (('V2', v2), ('V3', v3)) if not value]
    if missing:
        raise RuntimeError(f'Missing environment variables: {", ".join(missing)}')
    hottest_html, files_html, latest_html = fetch_blocks(v2)
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    doc = pq(hottest_html)
    hottest = []
    for tr in doc("tr").items():
        tag = tr("td").eq(1).find("a")
        title = tag.attr("title")
        link = tag.attr("href")
        reply = tr("td").eq(2).text()

        if title and link:
            title = markdown_escape(title)
            forum = link.split("/")[0]
            link = v3 + link.split("?")[0]
            hottest.append({"title": title, "link": link, "date": scraped_at, "forum": forum, "reply": reply})

    doc = pq(files_html)
    files = []
    for tr in doc("tr").items():
        tag = tr("td").eq(1).find("a")
        title = tag.attr("title")
        link = tag.attr("href")
        downloads = tr("td").eq(2).text()

        if title and link:
            title = markdown_escape(title)
            link = v3 + link.split("&s=")[0]
            files.append({"title": title, "link": link, "date": scraped_at, "downloads": downloads})

    doc = pq(latest_html)
    latest = []
    for tr in doc("tr").items():
        td = tr("td")
        title = td.eq(0).find("a").attr("title")
        link = td.eq(0).find("a").attr("href")
        date = td.eq(2).text()
        forum = td.eq(3).find("a").attr("title")

        if title and link and date:
            title = markdown_escape(title)
            link = v3 + link.split("?")[0]
            date = utc_to_cst(date)
            latest.append({"title": title, "link": link, "date": date, "forum": forum})

    if not all((hottest, files, latest)):
        raise RuntimeError('Forum panel contained no valid rows in one or more blocks')

    return {"hottest": hottest, "files": files, "latest": latest}

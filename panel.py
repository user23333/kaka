import os
import shutil
import time
from datetime import datetime, timedelta, timezone
from DrissionPage import Chromium, ChromiumOptions
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


def get_between(s, first, last):
    start = s.find(first)
    if start == -1:
        return None
    start += len(first)

    end = s.find(last, start)
    if end == -1:
        return None

    return s[start:end]


def fetch_blocks(v2):
    options = ChromiumOptions(read_file=False).auto_port().headless(False)
    options.set_load_mode('none')
    chrome = os.getenv('CHROME_BIN') or shutil.which('google-chrome')
    if chrome:
        options.set_browser_path(chrome)
    browser = Chromium(options)
    try:
        tab = browser.latest_tab
        deadline = time.monotonic() + 55
        try:
            tab.get(f'{v2}{time.time_ns()}', retry=0, timeout=45)
        except Exception:
            raise RuntimeError('Browser navigation failed') from None
        while time.monotonic() < deadline:
            try:
                html = tab.html or ''
            except Exception:
                tab = browser.latest_tab
                time.sleep(1)
                continue
            blocks = [get_between(html, f'<block blockid="{i}"><![CDATA[', ']]></block>') for i in (1, 2, 3)]
            if all(blocks):
                return blocks
            time.sleep(1)
        raise RuntimeError('V2 blocks did not load within 55 seconds')
    finally:
        browser.quit()


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

import os
import random
import requests
from datetime import datetime, timedelta
from pyquery import PyQuery as pq
import user_agent
# TODO: Try using cfscrape or curl_cffi

v1 = os.getenv('V1')
v2 = os.getenv('V2')
v3 = os.getenv('V3')


def utc_to_cst(utc):
    utc_time = datetime.strptime(utc, "%d-%m, %H:%M").replace(year=datetime.now().year)
    cst_time = utc_time + timedelta(hours=8)
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

    end = s.find(last, start + len(first))
    if end == -1:
        return None

    return s[start:end]


def fetch():
    data = {
        "url": f"{v2}{random.random() * 99999999999999}",
        "options": {"method": "POST", "headers": {"User-Agent": user_agent.random()}},
    }
    response = requests.post(v1, json=data)
    response.raise_for_status()

    doc = pq(get_between(response.text, '<block blockid="1"><![CDATA[', "]]></block>"))
    hottest = []
    for tr in doc("tr").items():
        tag = tr("td").eq(1).find("a")
        title = tag.attr("title")
        link = tag.attr("href")
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        forum = link.split("/")[0]
        reply = tr("td").eq(2).text()

        if title and link:
            title = markdown_escape(title)
            link = v3 + link.split("?")[0]
            hottest.append({"title": title, "link": link, "date": date, "forum": forum, "reply": reply})

    doc = pq(get_between(response.text, '<block blockid="2"><![CDATA[', "]]></block>"))
    files = []
    for tr in doc("tr").items():
        tag = tr("td").eq(1).find("a")
        title = tag.attr("title")
        link = tag.attr("href")
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        downloads = tr("td").eq(2).text()

        if title and link:
            title = markdown_escape(title)
            link = v3 + link.split("&s=")[0]
            files.append({"title": title, "link": link, "date": date, "downloads": downloads})

    doc = pq(get_between(response.text, '<block blockid="3"><![CDATA[', "]]></block>"))
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

    return {"hottest": hottest, "files": files, "latest": latest}

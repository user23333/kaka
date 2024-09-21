import os
import shutil
import json
from datetime import datetime
import panel

TODAY_STR = datetime.now().strftime("%Y-%m-%d")
CACHE_FILE = "files/today.json"
TODAY_FILE = "files/today.md"
HISTORY_FILE = "files/history/%s.md" % TODAY_STR

if not os.path.exists("files"):
    os.makedirs("files/history", exist_ok=True)


def load_cache():
    default = {"date": TODAY_STR, "hottest": [], "files": [], "latest": []}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            cache = json.load(file)
            if cache["date"] == default["date"]:
                return cache
    except Exception as err:
        print("load_cache error: " + str(err))
    return default


def save_cache(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file)


def update_cache():
    cache = load_cache()
    block = panel.fetch()

    filter = set(thread["link"] for thread in cache["hottest"])
    for thread in block["hottest"]:
        if not thread["link"] in filter:
            print("hottest new thread: %(date)s %(title)s" % thread)
            cache["hottest"].append(thread)

    filter = set(thread["link"] for thread in cache["files"])
    for thread in block["files"]:
        if not thread["link"] in filter:
            print("files new thread: %(date)s %(title)s" % thread)
            cache["files"].append(thread)

    filter = set(thread["link"] for thread in cache["latest"])
    for thread in reversed(block["latest"]):
        if not thread["link"] in filter:
            print("latest new thread: %(date)s %(title)s" % thread)
            cache["latest"].insert(0, thread)

    save_cache(cache)
    return cache


def save_to_markdown(data):
    with open(TODAY_FILE, "w", encoding="utf-8") as file:
        file.write("# 🔥Hottest\n")
        file.write("|Reply|Thread|Date|Forum|\n")
        file.write("|-----|------|----|-----|\n")
        for thread in data["hottest"]:
            file.write("|%(reply)s|[%(title)s](%(link)s)|`%(date)s`|`%(forum)s`|\n" % thread)

        file.write("# 📄Files\n")
        file.write("|Downloads|Thread|Date|\n")
        file.write("|---------|------|----|\n")
        for thread in data["files"]:
            file.write("|%(downloads)s|[%(title)s](%(link)s)|`%(date)s`|\n" % thread)

        file.write("# 💬Latest\n")
        file.write("|Thread|Date|Forum|\n")
        file.write("|------|----|-----|\n")
        for thread in data["latest"]:
            file.write("|[%(title)s](%(link)s)|`%(date)s`|`%(forum)s`|\n" % thread)

    shutil.copy2(TODAY_FILE, HISTORY_FILE)
    shutil.copy2(TODAY_FILE, "README.md")


save_to_markdown(update_cache())

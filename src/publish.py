"""Merak Zihin — carousel'i Instagram API (Instagram Login) ile yayınlar.

Görseller, bu repoya commit edildikten sonra raw.githubusercontent.com
üzerinden herkese açık URL ile Instagram'a verilir.
"""
import json
import os
import sys
import time

import requests

GRAPH = "https://graph.instagram.com/" + os.environ.get("IG_API_VERSION", "v25.0")


def api(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.request(method, f"{GRAPH}/{path}", params=params if method == "GET" else None,
                         data=params if method == "POST" else None, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"Instagram API hatası {r.status_code}: {r.text[:500]}")
    return r.json()


def wait_ready(container_id, tries=30):
    for _ in range(tries):
        st = api("GET", container_id, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Konteyner {container_id} durumu: {st}")
        time.sleep(5)
    raise RuntimeError(f"Konteyner {container_id} hazır olmadı")


def build_caption(item):
    tags = " ".join(item["hashtags"][:12])
    return f"{item['caption'].strip()}\n\n{tags}"[:2200]


def publish(item, image_urls):
    ig_id = os.environ["IG_USER_ID"]
    children = []
    for url in image_urls:
        c = api("POST", f"{ig_id}/media", image_url=url, is_carousel_item="true")
        children.append(c["id"])
    for cid in children:
        wait_ready(cid)
    car = api("POST", f"{ig_id}/media", media_type="CAROUSEL",
              children=",".join(children), caption=build_caption(item))
    wait_ready(car["id"])
    res = api("POST", f"{ig_id}/media_publish", creation_id=car["id"])
    return res["id"]


if __name__ == "__main__":
    item_path, urls_path = sys.argv[1], sys.argv[2]
    with open(item_path, encoding="utf-8") as f:
        item = json.load(f)
    with open(urls_path) as f:
        urls = [u.strip() for u in f if u.strip()]
    media_id = publish(item, urls)
    print(media_id)

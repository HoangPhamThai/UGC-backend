"""
TikTok post scraper (photo or video posts).

Pulls metrics with two HTTP GETs and no browser:

  1. TikTok embed endpoint
       https://www.tiktok.com/embed/v2/<id>?lang=en-US
     ships a <script id="__FRONTITY_CONNECT_STATE__"> JSON blob with
     createTime, playCount, diggCount, commentCount, shareCount.

  2. tikwm.com proxy
       https://www.tikwm.com/api/?url=<full-url>
     fills the one field TikTok's embed does NOT expose: collect_count
     (the bookmark icon on the right rail, what we call `bookmark`).

Field mapping (TikTok internal name -> what we return):
  uniqueId      -> account_name      (also fallback: @handle in URL)
  createTime    -> created_at        (Unix seconds -> ISO 8601 UTC)
  playCount     -> views             (often null for photo posts)
  diggCount     -> favorites         (heart icon, "Likes" in TikTok UI)
  commentCount  -> comments
  collectCount  -> bookmark          (bookmark icon, "Favorites" in TikTok UI)
  shareCount    -> shares

The embed endpoint is the source of truth; tikwm only fills `bookmark`
and `nickname` (and any field embed left null). If tikwm is unreachable,
those fall back to None — the rest of the scrape still succeeds.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

URL = "https://www.tiktok.com/@cici.ajoyer/video/7606308907945905415"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
TIMEOUT = 20


def _http_get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _item_id_from_url(url):
    m = re.search(r"/(?:photo|video)/(\d+)", url)
    return m.group(1) if m else None


def _handle_from_url(url):
    m = re.search(r"/@([^/?#]+)", url)
    return m.group(1) if m else None


def _iso_utc(ts):
    """Unix seconds (int or digit-string) -> ISO 8601 UTC, or None."""
    if ts is None:
        return None
    try:
        n = int(ts)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return datetime.fromtimestamp(n, tz=timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Embed endpoint (primary source)
# --------------------------------------------------------------------------
def _fetch_embed(item_id):
    """Return itemInfos dict from the embed page, or {} on any failure."""
    url = f"https://www.tiktok.com/embed/v2/{item_id}?lang=en-US"
    try:
        html = _http_get(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return {}

    m = re.search(
        r'<script[^>]*id="__FRONTITY_CONNECT_STATE__"[^>]*>(.*?)</script>',
        html, re.DOTALL,
    )
    if not m:
        return {}
    try:
        blob = json.loads(m.group(1).strip())
    except json.JSONDecodeError:
        return {}

    # source.data is keyed by the embed path; just take the first entry
    # so we're not coupled to the exact query-string the server echoes.
    data = (blob.get("source") or {}).get("data") or {}
    for v in data.values():
        infos = (v or {}).get("videoData", {}).get("itemInfos")
        if isinstance(infos, dict):
            return infos
    return {}


# --------------------------------------------------------------------------
# tikwm proxy (fallback for collectCount + nickname)
# --------------------------------------------------------------------------
def _fetch_tikwm(post_url):
    """Return tikwm `data` dict, or {} on any failure."""
    api = (
        "https://www.tikwm.com/api/?url="
        + urllib.parse.quote(post_url, safe="")
    )
    try:
        body = _http_get(api)
        payload = json.loads(body)
    except (urllib.error.URLError, urllib.error.HTTPError,
            TimeoutError, json.JSONDecodeError):
        return {}
    if payload.get("code") != 0:
        return {}
    return payload.get("data") or {}


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------
def scrape(url=URL):
    item_id = _item_id_from_url(url)
    if not item_id:
        raise ValueError(f"could not parse a post id from URL: {url}")

    embed = _fetch_embed(item_id)
    tikwm = _fetch_tikwm(url)
    tikwm_author = tikwm.get("author") or {}

    def pick(*vals):
        """First non-None value."""
        for v in vals:
            if v is not None:
                return v
        return None

    return {
        "account_name": pick(
            tikwm_author.get("unique_id"),
            _handle_from_url(url),
        ),
        "nickname": pick(tikwm_author.get("nickname")),
        "created_at": _iso_utc(pick(
            embed.get("createTime"),
            tikwm.get("create_time"),
        )),
        "content": pick(embed.get("text"), tikwm.get("title")),
        "views": pick(embed.get("playCount"), tikwm.get("play_count")),
        "favorites": pick(embed.get("diggCount"), tikwm.get("digg_count")),
        "comments": pick(embed.get("commentCount"), tikwm.get("comment_count")),
        "bookmark": pick(tikwm.get("collect_count")),
        "shares": pick(embed.get("shareCount"), tikwm.get("share_count")),
    }


def main():
    print(json.dumps(scrape(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

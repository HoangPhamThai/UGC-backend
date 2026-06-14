"""
Threads post scraper using Playwright.

Main post: account name, created_at, views, likes (favorites),
comments (replies), reposts, shares, text.
Plus the first N DIRECT replies (comments right under the post),
NOT posts from the "related threads"/suggested section.

Why this is tricky: Threads is JS-rendered, class names are
obfuscated, and the page loads BOTH the post's replies AND a
recommended/"related" feed via GraphQL. Both look like "posts" in
the JSON, so position-based extraction picks up the wrong ones.

Strategy:
  1. Capture every JSON response the page fetches.
  2. Identify the root post by the URL shortcode.
  3. A DIRECT reply is one whose reply_to_author is the original
     poster. That content signal is independent of which JSON
     container the object lives in, so the related-feed posts
     (which reply to other people) are filtered out.
  4. Structural reply_threads order is used only to preserve display
     order among the validated direct replies.

Set DEBUG = True to dump all captured JSON to ./threads_dump/ and
print a summary of every candidate container — useful if the field
names have drifted again.

Install:  pip install playwright && playwright install chromium
Run:      python threads_scraper.py
"""

import os
import json
import re
import asyncio
from datetime import datetime, timezone
from typing import Any
from playwright.async_api import async_playwright

URL = "https://www.threads.com/@pippy.pupy/post/DUR3d95EVEC?xmt=AQF0Sh9ImE6SzISIqbfOfVi4omDAgOnefVuN6MgBsRAjEQ"
N_COMMENTS = 2
DEBUG = False  # True => dump JSON + print container summaries
DUMP_DIR = "threads_dump"


# --------------------------------------------------------------------------
# JSON helpers
# --------------------------------------------------------------------------
def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _first(obj, *keys):
    for k in keys:
        if isinstance(obj, dict) and obj.get(k) is not None:
            return obj[k]
    return None


def _looks_like_post(d) -> bool:
    return isinstance(d, dict) and (
        ("like_count" in d or "text_post_app_info" in d)
        and ("caption" in d or "text_post_app_info" in d or "pk" in d)
    )


def _post_code(d):
    return _first(d, "code", "shortcode")


def _author(post):
    """(username, pk) of the post's author."""
    u = post.get("user") or {}
    return _first(u, "username"), _first(u, "pk", "id")


def _reply_to(post):
    """
    (username, pk) of whoever this post replies to, if exposed.
    Threads puts this in text_post_app_info.reply_to_author on web,
    and sometimes in a top-level 'reply_to_author' / parent field.
    """
    tpai = post.get("text_post_app_info") or {}
    rta = tpai.get("reply_to_author") or post.get("reply_to_author")
    if isinstance(rta, dict):
        return _first(rta, "username"), _first(rta, "pk", "id")
    if isinstance(rta, str):
        return rta, None
    return None, None


def _parse_count(s):
    """'1.2K' -> 1200, '3.4M' -> 3400000, '12,345' -> 12345, '987' -> 987."""
    if not s:
        return None
    s = str(s).strip().replace(",", "").replace("\xa0", "")
    m = re.match(r"^([\d.]+)\s*([KMB])?$", s, re.IGNORECASE)
    if m:
        num = float(m.group(1))
        mult = {"k": 1e3, "m": 1e6, "b": 1e9}.get((m.group(2) or "").lower(), 1)
        return int(num * mult)
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None


def _best_candidate(image_versions2):
    """Highest-resolution URL from an image_versions2.candidates list."""
    cands = (image_versions2 or {}).get("candidates") or []
    best = None
    for c in cands:
        if not isinstance(c, dict) or not c.get("url"):
            continue
        area = (c.get("width") or 0) * (c.get("height") or 0)
        if best is None or area > best[0]:
            best = (area, c["url"])
    return best[1] if best else None


def _collect_images(post: dict):
    """
    Image URLs attached to a post/comment, best resolution each.
    Handles single images and multi-image carousels. Video posts have
    no still image here (their poster frame lives in image_versions2,
    which we still pick up if present).
    """
    urls = []
    carousel = post.get("carousel_media")
    if isinstance(carousel, list) and carousel:
        for item in carousel:
            if isinstance(item, dict):
                u = _best_candidate(item.get("image_versions2"))
                if u:
                    urls.append(u)
    else:
        u = _best_candidate(post.get("image_versions2"))
        if u:
            urls.append(u)
    # De-dupe, preserve order.
    seen, out = set(), []
    for x in urls:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def extract_post_fields(post: dict) -> dict:
    out: dict[str, Any] = {
        k: None
        for k in (
            "account_name",
            "created_at",
            "views",
            "favorites",
            "comments",
            "reposts",
            "shares",
            "content",
        )
    }
    out["account_name"] = _author(post)[0] or _first(post, "username")

    ts = _first(post, "taken_at", "taken_at_timestamp", "device_timestamp")
    if isinstance(ts, (int, float)) and ts > 1e9:
        out["created_at"] = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    out["favorites"] = _first(post, "like_count")
    out["comments"] = _first(post, "reply_count", "direct_reply_count")
    out["reposts"] = _first(post, "repost_count")
    out["shares"] = _first(post, "reshare_count", "share_count")
    out["views"] = _first(post, "view_count", "video_view_count", "play_count")

    tpai = post.get("text_post_app_info") or {}
    out["reposts"] = (
        out["reposts"] if out["reposts"] is not None else _first(tpai, "repost_count")
    )
    out["shares"] = (
        out["shares"] if out["shares"] is not None else _first(tpai, "reshare_count")
    )
    out["comments"] = (
        out["comments"]
        if out["comments"] is not None
        else _first(tpai, "direct_reply_count")
    )

    cap = post.get("caption")
    if isinstance(cap, dict):
        out["content"] = cap.get("text")
    elif isinstance(cap, str):
        out["content"] = cap

    out["images"] = _collect_images(post)
    return out


# --------------------------------------------------------------------------
# Core extraction
# --------------------------------------------------------------------------
def _all_posts(json_blobs):
    """Every post-like dict across all blobs, de-duplicated by code/pk."""
    seen, out = set(), []
    for data in json_blobs:
        for d in _walk(data):
            if not _looks_like_post(d):
                continue
            key = _post_code(d) or _first(d, "pk", "id")
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            out.append(d)
    return out


def _find_root(posts, root_code):
    if root_code:
        for p in posts:
            if _post_code(p) == root_code:
                return p
    if posts:

        def score(p):
            return sum(
                1
                for k in (
                    "like_count",
                    "reply_count",
                    "repost_count",
                    "reshare_count",
                    "video_view_count",
                    "view_count",
                )
                if k in p
            )

        return max(posts, key=score)
    return None


def _find_root_rich(json_blobs, root_code):
    """
    The root post can appear several times across the captured JSON —
    e.g. a media-less preview AND the full object. De-dup keeps only the
    first, which may be the stripped one, dropping the post's images.
    Here we scan ALL occurrences matching the URL shortcode and keep the
    copy richest in media (then in caption, then in size).
    """
    if not root_code:
        return None
    best, best_key = None, None
    for data in json_blobs:
        for d in _walk(data):
            if not (_looks_like_post(d) and _post_code(d) == root_code):
                continue
            key = (
                len(_collect_images(d)),
                1 if d.get("caption") else 0,
                len(d),
            )
            if best_key is None or key > best_key:
                best, best_key = d, key
    return best


def parse_all(json_blobs, root_code, debug=False):
    posts = _all_posts(json_blobs)
    root = _find_root_rich(json_blobs, root_code) or _find_root(posts, root_code)

    if debug:
        _print_debug(json_blobs, posts, root, root_code)

    result = extract_post_fields(root) if root else {}
    if not root:
        result["comments_preview"] = []
        return result

    root_user, root_pk = _author(root)
    root_self_code = _post_code(root)

    # ---- Primary: content-based direct-reply filter ----
    # A direct reply replies to the OP (by username or pk). This ignores
    # which JSON container it came from, so related-feed posts drop out.
    direct = []
    for p in posts:
        if _post_code(p) == root_self_code:
            continue
        rt_user, rt_pk = _reply_to(p)
        if rt_user is None and rt_pk is None:
            continue  # no reply info -> can't confirm it's a reply here
        if (root_user and rt_user == root_user) or (root_pk and rt_pk == root_pk):
            direct.append(p)

    used = "reply_to_author match"

    # ---- Secondary: structural reply_threads of the matching container ----
    # Used when reply_to_author isn't populated anywhere. We still only
    # accept the container whose containing_thread IS our root post.
    if not direct:
        for data in json_blobs:
            for d in _walk(data):
                if not isinstance(d, dict):
                    continue
                ct, rts = d.get("containing_thread"), d.get("reply_threads")
                if not (isinstance(ct, dict) and isinstance(rts, list)):
                    continue
                items = ct.get("thread_items") or []
                if not any(
                    _looks_like_post(it.get("post"))
                    and _post_code(it.get("post")) == root_self_code
                    for it in items
                    if isinstance(it, dict)
                ):
                    continue
                for rt in rts:
                    its = rt.get("thread_items") if isinstance(rt, dict) else None
                    for it in its or []:
                        p = it.get("post") if isinstance(it, dict) else None
                        if _looks_like_post(p):
                            direct.append(p)
                            break  # top-level comment of this reply thread
                break
            if direct:
                used = "reply_threads of matching container"
                break

    # Order: by timestamp ascending (oldest first ≈ top of thread).
    direct.sort(key=lambda p: _first(p, "taken_at", "taken_at_timestamp") or 0)

    if debug:
        print(f"[debug] direct replies via: {used} -> {len(direct)} found")

    result["comments_preview"] = [extract_post_fields(r) for r in direct]
    return result


def _print_debug(json_blobs, posts, root, root_code):
    os.makedirs(DUMP_DIR, exist_ok=True)
    for i, blob in enumerate(json_blobs):
        with open(
            os.path.join(DUMP_DIR, f"blob_{i:03d}.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(blob, f, ensure_ascii=False, indent=2)
    print(f"[debug] dumped {len(json_blobs)} JSON blobs to ./{DUMP_DIR}/")
    print(f"[debug] root_code from URL: {root_code}")
    print(f"[debug] total unique post-like objects: {len(posts)}")
    if root:
        ru, rpk = _author(root)
        print(f"[debug] root matched: @{ru} code={_post_code(root)} pk={rpk}")
    print("[debug] containers with containing_thread + reply_threads:")
    n = 0
    for data in json_blobs:
        for d in _walk(data):
            if (
                isinstance(d, dict)
                and isinstance(d.get("reply_threads"), list)
                and isinstance(d.get("containing_thread"), dict)
            ):
                n += 1
                items = d["containing_thread"].get("thread_items") or []
                codes = [
                    _post_code(it.get("post"))
                    for it in items
                    if isinstance(it, dict) and _looks_like_post(it.get("post"))
                ]
                reps = []
                for rt in d["reply_threads"][:4]:
                    its = rt.get("thread_items") if isinstance(rt, dict) else None
                    for it in its or []:
                        p = it.get("post") if isinstance(it, dict) else None
                        if _looks_like_post(p):
                            rtu, _ = _reply_to(p)
                            reps.append(f"@{_author(p)[0]}(reply_to=@{rtu})")
                            break
                print(f"   container#{n}: root_codes={codes} " f"replies[:4]={reps}")
    if n == 0:
        print(
            "   (none found — reply structure likely differs; "
            "inspect the dumped blobs)"
        )


# --------------------------------------------------------------------------
# Browser driver
# --------------------------------------------------------------------------
# JS: find the <a> whose href points back at this post, then read the
# "xxx views" span inside it. Threads renders views in the DOM, not JSON.
JS_VIEWS = r"""
(code) => {
  const sel = 'a[href*="/post/' + code + '"]';
  const anchors = Array.from(document.querySelectorAll(sel));
  const re = /([0-9][0-9.,]*\s*[KMB]?)\s+views?\b/i;
  for (const a of anchors) {
    const t = (a.innerText || a.textContent || '').replace(/\u00a0/g, ' ');
    const m = t.match(re);
    if (m) return m[1].trim();
  }
  return null;
}
"""


async def scrape(url=URL, n_comments=N_COMMENTS, headless=True, debug=DEBUG):
    root_code = None
    m = re.search(r"/post/([^/?]+)", url)
    if m:
        root_code = m.group(1)

    captured = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1280, "height": 1800},
        )
        page = await context.new_page()

        async def on_response(resp):
            ct = (resp.headers or {}).get("content-type", "")
            if "application/json" not in ct and "/graphql" not in resp.url:
                return
            try:
                captured.append(await resp.json())
            except Exception:
                pass

        page.on("response", on_response)
        await page.goto(url, wait_until="networkidle", timeout=60_000)

        for label in (
            "Allow all cookies",
            "Decline optional cookies",
            "Close",
            "Not now",
        ):
            try:
                btn = page.get_by_role("button", name=label)
                if await btn.count():
                    await btn.first.click(timeout=2_000)
            except Exception:
                pass

        # Scroll to trigger the replies GraphQL request.
        for _ in range(3):
            await page.mouse.wheel(0, 1500)
            await page.wait_for_timeout(1_200)
        await page.wait_for_timeout(1_500)

        html = await page.content()
        embedded = []
        for raw in re.findall(
            r'<script[^>]+type="application/json"[^>]*>(.*?)</script>',
            html,
            flags=re.DOTALL,
        ):
            raw = raw.strip()
            if raw:
                try:
                    embedded.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass

        data = parse_all(embedded + captured, root_code, debug=debug)

        if not data.get("account_name"):
            t = await page.locator('meta[property="og:title"]').get_attribute("content")
            if t:
                mt = re.search(r"\(@([^)]+)\)", t)
                data["account_name"] = mt.group(1) if mt else t
        if not data.get("content"):
            data["content"] = await page.locator(
                'meta[property="og:description"]'
            ).get_attribute("content")

        # Views live in the DOM, inside the anchor linking back to the post.
        if data.get("views") is None and root_code:
            try:
                raw = await page.evaluate(JS_VIEWS, root_code)
                parsed = _parse_count(raw)
                if parsed is not None:
                    data["views"] = parsed
            except Exception:
                pass

        await browser.close()

    data["comments_preview"] = data.get("comments_preview", [])[:n_comments]
    return data


def main():
    data = asyncio.run(scrape())
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

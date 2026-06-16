import html


def build_article_link(base_url: str, workspace_id: str, article_id: str) -> str:
    root = base_url.rstrip("/")
    return f"{root}/workspaces/{workspace_id}/articles/{article_id}"


def render_html_email(*, subject: str, body_text: str, article_url: str) -> str:
    safe_subject = html.escape(subject)
    safe_body = html.escape(body_text)
    safe_url = html.escape(article_url, quote=True)
    return f"""<!DOCTYPE html>
<html lang="vi">
<head><meta charset="utf-8"><title>{safe_subject}</title></head>
<body style="font-family: sans-serif; line-height: 1.5; color: #222;">
  <p>{safe_body}</p>
  <p><a href="{safe_url}" style="display:inline-block;padding:10px 16px;background:#2563eb;color:#fff;text-decoration:none;border-radius:6px;">Xem bài viết</a></p>
</body>
</html>"""

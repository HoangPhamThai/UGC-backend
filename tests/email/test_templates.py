from app.modules.email.templates import build_article_link, render_html_email


def test_build_article_link_strips_trailing_slash():
    assert build_article_link(
        "https://ugc.example.com/", "ws_1", "art_1"
    ) == "https://ugc.example.com/workspaces/ws_1/articles/art_1"


def test_render_html_email_contains_subject_body_and_button():
    html = render_html_email(
        subject="Tiêu đề",
        body_text="Nội dung email.",
        article_url="https://ugc.example.com/workspaces/ws_1/articles/art_1",
    )
    assert "Tiêu đề" in html
    assert "Nội dung email." in html
    assert "Xem bài viết" in html
    assert "https://ugc.example.com/workspaces/ws_1/articles/art_1" in html
    assert html.startswith("<!DOCTYPE html>")

from app.modules.workspaces.domain.link_platform import detect_platform


def test_detects_tiktok():
    assert detect_platform("https://www.tiktok.com/@cici/photo/761") == "tiktok"


def test_detects_threads_com_and_net():
    assert detect_platform("https://www.threads.com/@ha/post/DM") == "threads"
    assert detect_platform("https://threads.net/@ha/post/DM") == "threads"


def test_rejects_other_urls():
    assert detect_platform("https://facebook.com/x") is None
    assert detect_platform("not a url") is None
    assert detect_platform("") is None

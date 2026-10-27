from datetime import datetime, timezone
from time import struct_time

from wartahayati.normalize import canonical_url, clean_text, compile_filter, merge, to_item

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)


def test_clean_text_strips_tags_entities_and_truncates():
    assert clean_text("<b>Padi &amp; jagung</b>\n  gogo") == "Padi & jagung gogo"
    assert clean_text("a" * 300, limit=50).endswith("…")
    assert len(clean_text("a" * 300, limit=50)) == 50


def test_canonical_url_removes_tracking_and_rejects_unsafe_schemes():
    assert canonical_url("https://Example.com/a?utm_source=x&id=7#top") == "https://example.com/a?id=7"
    assert canonical_url("javascript:alert(1)") is None
    assert canonical_url("") is None


def test_to_item_defaults_missing_date_and_clips_future():
    entry = {"title": "Judul", "link": "https://a.id/x"}
    assert to_item(entry, NOW)["published"] == "2026-10-27T12:00:00+00:00"
    future = {**entry, "published_parsed": struct_time((2030, 1, 1, 0, 0, 0, 0, 1, 0))}
    assert to_item(future, NOW)["published"] == "2026-10-27T12:00:00+00:00"
    assert to_item({"title": "", "link": "https://a.id/x"}, NOW) is None


def test_merge_dedupes_by_url_and_keeps_old_date():
    old = [{"title": "Budidaya lele", "link": "https://a.id/lele/", "published": "2026-10-01T00:00:00+00:00"}]
    new = [
        {"title": "Budidaya lele", "link": "https://www.a.id/lele", "published": "2026-10-27T00:00:00+00:00"},
        {"title": "Nila salin", "link": "https://a.id/nila", "published": "2026-10-25T00:00:00+00:00"},
    ]
    out = merge(old, new, limit=10)
    assert [i["title"] for i in out] == ["Nila salin", "Budidaya lele"]
    assert out[1]["published"] == "2026-10-01T00:00:00+00:00"


def test_merge_dedupes_same_title_from_different_urls_keeping_newest():
    items = [
        {"title": "Budidaya lele", "link": "https://a.id/lele", "published": "2026-10-01T00:00:00+00:00"},
        {"title": "BUDIDAYA  LELE!", "link": "https://b.id/lain", "published": "2026-10-20T00:00:00+00:00"},
    ]
    out = merge([], items, limit=10)
    assert len(out) == 1
    assert out[0]["link"] == "https://b.id/lain"


def test_include_filter_is_case_insensitive():
    flt = compile_filter(["Indonesia", "Borneo"])
    assert flt.search("palm oil in indonesia")
    assert not flt.search("Amazon deforestation")
    assert compile_filter(()) is None

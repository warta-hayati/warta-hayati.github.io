import pytest

from wartahayati.config import ConfigError, load


def test_default_config_is_valid_and_covers_every_topic():
    cfg = load()
    enabled = [s for s in cfg.sources if s.enabled]
    for topic in cfg.topics:
        assert any(topic.slug in s.topics for s in enabled), f"topik tanpa sumber: {topic.slug}"
    assert len({s.id for s in cfg.sources}) == len(cfg.sources)


def test_unknown_topic_is_rejected(tmp_path):
    bad = tmp_path / "s.yaml"
    bad.write_text(
        "topics: [{slug: a, name: A}]\ntiers: {riset: {label: Riset}}\n"
        "sources: [{id: x, name: X, url: 'https://x.id', tier: riset, lang: id, topics: [zzz]}]\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load(bad)

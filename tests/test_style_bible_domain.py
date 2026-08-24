from xerama.domain.style_bible import StyleBible


def test_style_bible_defaults() -> None:
    style_bible = StyleBible(id="SB_1", series_id="SER_1")
    assert style_bible.locked is False
    assert style_bible.version == 1
    assert style_bible.style_asset_id is None
    assert style_bible.palette == []
    assert style_bible.negatives == []

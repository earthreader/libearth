from libearth.feed import MarkupTagCleaner


def test_markup_tag_cleaner():
    assert MarkupTagCleaner.clean('<b>Hello</b>') == 'Hello'
    assert MarkupTagCleaner.clean('<p><b>Hello</b></p>') == 'Hello'
    assert MarkupTagCleaner.clean('<p>Hello <b>world</b></p>') == 'Hello world'

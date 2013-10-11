from libearth.sanitizer import clean_html


def test_markup_tag_cleaner():
    assert clean_html('<b>Hello</b>') == 'Hello'
    assert clean_html('<p><b>Hello</b></p>') == 'Hello'
    assert clean_html('<p>Hello <b>world</b></p>') == 'Hello world'

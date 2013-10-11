from libearth.sanitizer import clean_html


def test_markup_tag_cleaner():
    assert clean_html('<b>Hello</b>') == 'Hello'
    assert clean_html('<p><b>Hello</b></p>') == 'Hello'
    assert clean_html('<p>Hello <b>world</b></p>') == 'Hello world'
    assert (clean_html('<p>&quot;&lt;Entity&gt; test&quot;</p>') ==
            '"<Entity> test"')
    assert clean_html('<p>&#34;charref test&#x22;</p>') == '"charref test"'

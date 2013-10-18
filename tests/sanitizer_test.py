from libearth.sanitizer import clean_html, sanitize_html


def test_markup_tag_cleaner():
    assert clean_html('<b>Hello</b>') == 'Hello'
    assert clean_html('<p><b>Hello</b></p>') == 'Hello'
    assert clean_html('<p>Hello <b>world</b></p>') == 'Hello world'
    assert (clean_html('<p>&quot;&lt;Entity&gt; test&quot;</p>') ==
            '"<Entity> test"')
    assert clean_html('<p>&#34;charref test&#x22;</p>') == '"charref test"'


def test_sanitize_html():
    assert sanitize_html('<b>Hello</b>') == '<b>Hello</b>'
    # <script> tags
    assert (sanitize_html('<b>Hello</b><script>alert(1)</script><b>1</b>') ==
            '<b>Hello</b><b>1</b>')
    # ``display: xxxx;`` styles
    assert (sanitize_html('<b style="display: none;">Hello</b>') ==
            '<b style="">Hello</b>')
    assert (sanitize_html('<b style="  display:none">Hello</b>') ==
            '<b style="">Hello</b>')
    assert (sanitize_html('<b style="  display:none; color: red;">Hello</b>') ==
            '<b style="color: red;">Hello</b>')
    assert (sanitize_html('<b style="font-weight: normal; display:none; '
                          'color: red;">Hello</b>') ==
            '<b style="font-weight: normal;color: red;">Hello</b>')
    assert (sanitize_html('<b style="font-weight: normal;'
                          'display: inline-block; color: red;">Hello</b>') ==
            '<b style="font-weight: normal;color: red;">Hello</b>')
    assert (sanitize_html('<b style="font-weight: normal;'
                          'display: block; color: red;">Hello</b>') ==
            '<b style="font-weight: normal;color: red;">Hello</b>')
    assert (sanitize_html('<b style="display:block">Hello</b>') ==
            '<b style="">Hello</b>')
    # JavaScript event attributes
    assert sanitize_html('<b onclick="alert(1);">Hello</b>') == '<b>Hello</b>'
    assert (sanitize_html('<img onload="alert(1);" src="a.gif">') ==
            '<img src="a.gif">')
    # Disallowed schemes
    assert (sanitize_html('<a href="javascript:alert(1)">Hello</a>') ==
            '<a href="">Hello</a>')
    assert (sanitize_html('<a href="jscript:alert(1)">Hello</a>') ==
            '<a href="">Hello</a>')

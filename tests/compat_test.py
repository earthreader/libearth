from libearth.compat import binary, text_type


def test_binary():
    assert binary(b'test') == b'test'
    assert binary(text_type('Test')) == b'Test'

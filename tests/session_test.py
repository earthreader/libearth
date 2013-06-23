from pytest import raises

from libearth.session import Session


def test_repository_type_error():
    with raises(TypeError):
        Session(1234)
    with raises(TypeError):
        Session('abc')

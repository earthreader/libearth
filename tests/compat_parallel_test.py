import numbers

from pytest import raises

from libearth.compat.parallel import cpu_count, parallel_map


def test_cpu_count():
    assert isinstance(cpu_count(), numbers.Integral)
    assert 0 < cpu_count()


def test_parallel_map():
    input = [1, 2, 3, 4]
    fn = lambda n: n * 2
    result = parallel_map(4, fn, input)
    assert frozenset(result) == frozenset(map(fn, input))


def test_parallel_map_multiargs():
    input1 = [1, 2, 3, 4]
    input2 = [5, 6, 7, 8]
    fn = lambda n, m: n * m
    result = parallel_map(4, fn, input1, input2)
    assert frozenset(result) == frozenset(map(fn, input1, input2))


def test_parallel_map_errors():
    input = [1, 2, 3, 0]
    result = parallel_map(4, lambda n: 1 // n, input)
    it = iter(result)
    with raises(ZeroDivisionError):
        next(it)
        next(it)
        next(it)
        next(it)

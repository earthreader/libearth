from libearth.session import RevisionSet


def pytest_assertrepr_compare(op, left, right):
    if op == '==' and isinstance(left, RevisionSet) and \
       isinstance(right, RevisionSet):
        return list(compare_revision_sets(left, right))


def compare_revision_sets(left, right):
    left_keys = frozenset(left.keys())
    right_keys = frozenset(right.keys())
    yield 'RevisionSet(...{0} items...) != RevisionSet(...{1} items...)'.format(
        len(left_keys), len(right_keys)
    )
    left_more = left_keys - right_keys
    if left_more:
        yield '{0} session(s) the left set has more:'.format(len(left_more))
        for session in left_more:
            yield '- {0!r}'.format(session)
    right_more = right_keys - left_keys
    if right_more:
        yield '{0} session(s) the right set has more:'.format(len(right_more))
        for session in right_more:
            yield '- {0!r}'.format(session)
    common = left_keys & right_keys
    different_keys = frozenset(k for k in common if left[k] != right[k])
    if different_keys:
        yield '{0} session(s) have different times:'.format(len(different_keys))
        for k in different_keys:
            yield '- {0!r}: {1!r} != {2!r}'.format(k, left[k], right[k])

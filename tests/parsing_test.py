from __future__ import print_function

import logging
import os
import os.path
import sys

from pytest import mark

from libearth.compat import IRON_PYTHON
from libearth.compat.etree import fromstringlist
from libearth.parser.autodiscovery import get_format
from libearth.schema import write


test_suite_dir = os.path.join(os.path.dirname(__file__), 'parsing')
test_files = frozenset(f
                       for f in os.listdir(test_suite_dir)
                       if not f.startswith('.') and f.endswith('.xml'))
test_pairs = {}
missing_inputs = set()

for in_file in test_files:
    if not in_file.endswith('.out.xml'):
        out_file = in_file.rstrip('.xml') + '.out.xml'
        if out_file in test_files:
            test_pairs[in_file] = out_file
        else:
            missing_inputs.add(in_file)


@mark.parametrize(('input_', 'expected'), test_pairs.items())
def test_parse(input_, expected):
    with open(os.path.join(test_suite_dir, input_), 'rb') as f:
        xml = f.read()
        if IRON_PYTHON:
            xml = bytes(xml)
    parse = get_format(xml)
    assert callable(parse)
    uri_filename = input_.rstrip('.xml') + '.uri.txt'
    try:
        with open(os.path.join(test_suite_dir, uri_filename)) as f:
            base_uri = f.read().strip()
    except (IOError, OSError):
        base_uri = 'http://example.com/'
    parsed_feed, _ = parse(xml, feed_url=base_uri)
    parsed_tree = fromstringlist(
        write(parsed_feed, canonical_order=True, hints=False)
    )
    with open(os.path.join(test_suite_dir, expected)) as f:
        if IRON_PYTHON:
            f = f.read().decode('utf-8'),
        expected_tree = fromstringlist(f)
    compare_tree(expected_tree, parsed_tree)


def compare_tree(expected, parsed, path=''):
    assert expected.tag == parsed.tag, (
        'expected: {0}{1}\nparsed:   {0}{2}'.format(path, expected.tag,
                                                    parsed.tag)
    )
    path += '/' + expected.tag
    for name, value in expected.attrib.items():
        expected_value = parsed.attrib.get(name)
        assert expected_value == value, (
            '{0}@{1}\n  expected: {2!r}\n  parsed:   {3!r}'.format(
                path, name, expected_value, value
            )
        )
    for name, value in parsed.attrib.items():
        assert name in expected.attrib, (
            '{0}@{1}\n  expected: None\n  parsed:   {2!r}'.format(
                path, name, value
            )
        )
    assert expected.text == parsed.text, (
        '{0}/text()\n  expected: {1!r}\n  parsed:   {2!r}'.format(
            path, expected.text, parsed.text
        )
    )
    expected_children = expected.getchildren()
    parsed_children = parsed.getchildren()
    for e, p in zip(expected_children, parsed_children):
        compare_tree(e, p, path)
    expected_len = len(expected_children)
    parsed_len = len(parsed_children)
    if expected_len > parsed_len:
        longer = 'expected'
        children = expected_children
    else:
        longer = 'parsed'
        children = parsed_children
    diff_len = abs(expected_len - parsed_len)
    delta = '\n    '.join(e.tag for e in children[-diff_len:])
    assert expected_len == parsed_len, (
        '{0}\n  expected: {1} children\n  parsed:   {2}'
        '\n  {3} {4} more elements\n    {5}'.format(
            path, expected_len, parsed_len, longer, diff_len, delta
        )
    )


if __name__ == '__main__':
    if not missing_inputs:
        print('All XML files have their paired .out.xml file.')
        raise SystemExit()
    try:
        input = raw_input
    except NameError:
        pass
    print('There are', len(missing_inputs),
          'XML files that have no paired .out.xml files:')
    for missing_input in sorted(missing_inputs):
        print('\t' + missing_input)
    confirm = input('Do you want to create scaffold .out.xml files? ')
    if not confirm.strip().lower() in ('y', 'yes'):
        raise SystemExit()
    logging.basicConfig()
    formats = {}
    for filename in missing_inputs:
        print(filename)
        with open(os.path.join(test_suite_dir, filename)) as f:
            xml = f.read()
        try:
            parse = get_format(xml)
        except Exception:
            print('Failed to detect the format of', filename, file=sys.stderr)
            raise
        uri_filename = filename.rstrip('.xml') + '.uri.txt'
        try:
            with open(os.path.join(test_suite_dir, uri_filename)) as f:
                base_uri = f.read().strip()
        except (IOError, OSError):
            base_uri = 'http://example.com/'
        try:
            feed, _ = parse(xml, feed_url=base_uri)
        except Exception:
            print('Failed to parse', filename, file=sys.stderr)
            raise
        out_filename = filename.rstrip('.xml') + '.out.xml'
        try:
            expected = ''.join(write(feed, canonical_order=True, hints=False))
            with open(os.path.join(test_suite_dir, out_filename), 'w') as f:
                f.write(expected)
        except Exception:
            print('Failed to write', out_filename, file=sys.stderr)
            raise

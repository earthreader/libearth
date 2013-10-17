""":mod:`libearth.stage` --- Staging updates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import re

__all__ = 'compile_format_to_pattern',


def compile_format_to_pattern(format_string):
    """Compile a ``format_string`` to regular expression pattern.
    For example, ``'string{0}like{1}this{{2}}'`` will be compiled to
    ``/^string(.*?)like(.*?)this\{2\}$/``.

    :param format_string: format string to compile
    :type format_string: :class:`str`
    :returns: compiled pattern object
    :rtype: :class:`re.RegexObject`

    """
    pattern = ['^']
    i = 0
    for match in re.finditer(r'(^|[^{])\{\d+\}|(\{\{)|(\}\})', format_string):
        if match.group(2):
            j = match.start()
            chunk = r'\{'
        elif match.group(3):
            j = match.start()
            chunk = r'\}'
        else:
            j = match.end(1)
            chunk = '(.*?)'
        pattern.append(re.escape(format_string[i:j]))
        pattern.append(chunk)
        i = match.end(0)
    if len(format_string) > i:
        pattern.append(re.escape(format_string[i:]))
    pattern.append('$')
    return re.compile(''.join(pattern))

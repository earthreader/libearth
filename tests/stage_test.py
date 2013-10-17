from libearth.stage import compile_format_to_pattern


def test_compile_format_to_pattern():
    p = compile_format_to_pattern('{0}')
    p_msg = 'p.pattern = ' + repr(p.pattern)
    assert p.match('anything'), p_msg
    assert p.match('something'), p_msg
    assert p.match('no-match'), p_msg
    assert p.match('somehow'), p_msg
    p2 = compile_format_to_pattern('{0}thing')
    p2_msg = 'p2.pattern = ' + repr(p2.pattern)
    assert p2.match('anything'), p2_msg
    assert p2.match('something'), p2_msg
    assert not p2.match('no-match'), p2_msg
    assert not p2.match('somehow'), p2_msg
    p3 = compile_format_to_pattern('some{0}')
    p3_msg = 'p3.pattern = ' + repr(p3.pattern)
    assert not p3.match('anything'), p3_msg
    assert p3.match('something'), p3_msg
    assert not p3.match('no-match'), p3_msg
    assert p3.match('somehow'), p3_msg
    p4 = compile_format_to_pattern('pre{0}post')
    p4_msg = 'p4.pattern = ' + repr(p4.pattern)
    assert not p4.match('something'), p4_msg
    assert not p4.match('no-match'), p4_msg
    assert not p4.match('preonly'), p4_msg
    assert not p4.match('onlypost'), p4_msg
    assert p4.match('preandpost'), p4_msg
    p5 = compile_format_to_pattern('pre{0}in{1}post')
    p5_msg = 'p5.pattern = ' + repr(p5.pattern)
    assert not p5.match('something'), p5_msg
    assert not p5.match('no-match'), p5_msg
    assert not p5.match('preonly'), p5_msg
    assert not p5.match('onlypost'), p5_msg
    assert not p5.match('preandpost'), p5_msg
    assert not p5.match('inandpost'), p5_msg
    assert not p5.match('preandin'), p5_msg
    assert p5.match('preandinandpost'), p5_msg
    p6 = compile_format_to_pattern('pre{0}and{{1}}post')
    p6_msg = 'p6.pattern = ' + repr(p6.pattern)
    assert not p6.match('something'), p6_msg
    assert not p6.match('no-match'), p6_msg
    assert not p6.match('preonly'), p6_msg
    assert not p6.match('onlypost'), p6_msg
    assert not p6.match('preandpost'), p6_msg
    assert not p6.match('inandpost'), p6_msg
    assert not p6.match('preandin'), p6_msg
    assert not p6.match('preandinandpost'), p6_msg
    assert p6.match('pre,and{1}post'), p6_msg

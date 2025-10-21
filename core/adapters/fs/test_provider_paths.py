from core.adapters.fs.provider import _is_under_root


def test_is_under_root_same_drive():
    assert _is_under_root(r"D:\\root\\child\\file.txt", r"D:\\root")


def test_is_under_root_different_drive():
    assert not _is_under_root(r"C:\\other\\file.txt", r"D:\\root")


def test_is_under_root_unc_share():
    assert _is_under_root(r"\\srv\share\root\dir", r"\\srv\share\root")


def test_is_under_root_boundary():
    assert not _is_under_root(r"D:\\root2", r"D:\\root")

from copydeps import parse_ldd_output


def test_parse_ldd_output():
    LDD_OUTPUT = b"""
    linux-vdso.so.1 =>  (0x00007ffd6f3cd000)
    libcrypto.so.1.0.0 => /home/ci/build/genymotion/./libcrypto.so.1.0.0 (0x00007f5ea40b6000)
    /lib64/ld-linux-x86-64.so.2 (0x0000562cf1094000)
    """
    dct = parse_ldd_output(LDD_OUTPUT)
    assert dct == {
        'libcrypto.so.1.0.0': '/home/ci/build/genymotion/./libcrypto.so.1.0.0'
    }

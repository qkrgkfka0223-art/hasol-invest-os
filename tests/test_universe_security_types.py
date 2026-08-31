from hasol_quant.universe import is_common_equity_security_name


def test_allows_common_and_ordinary_shares():
    assert is_common_equity_security_name("Moderna, Inc. Common Stock")
    assert is_common_equity_security_name("Ballard Power Systems, Inc. Common Shares")
    assert is_common_equity_security_name("GCL Global Holdings Ltd Ordinary Shares")


def test_rejects_depositary_security_forms():
    assert not is_common_equity_security_name("Quoin Pharmaceuticals, Ltd. American Depositary Shares")
    assert not is_common_equity_security_name("Example plc American Depositary Receipts")
    assert not is_common_equity_security_name("Example Corp Depositary Shares")


def test_rejects_other_non_common_security_forms():
    assert not is_common_equity_security_name("Example Corp Warrants")
    assert not is_common_equity_security_name("Example Corp Units")
    assert not is_common_equity_security_name("Example Corp Preferred Stock")
    assert not is_common_equity_security_name("Example Corp Shares of Beneficial Interest")
    assert not is_common_equity_security_name("Example LP Limited Partnership Units")

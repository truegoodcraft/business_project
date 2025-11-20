# SPDX-License-Identifier: AGPL-3.0-or-later
from core.public_api import PUBLIC_IMPORTS_ALLOWLIST


def test_allowlist_is_minimal_and_stable() -> None:
    assert "core.conn_broker" in PUBLIC_IMPORTS_ALLOWLIST
    assert "core.contracts.plugin_v2" in PUBLIC_IMPORTS_ALLOWLIST
    assert "core.capabilities" in PUBLIC_IMPORTS_ALLOWLIST
    assert "core._internal.runtime" not in PUBLIC_IMPORTS_ALLOWLIST

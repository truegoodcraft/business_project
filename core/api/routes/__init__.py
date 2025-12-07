# Copyright (C) 2025 BUS Core Authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Route package exports.

Ledger routes live in ``ledger_api.py`` to avoid a name collision with
``core.appdb.ledger``. Import the router here for clarity when using
``core.api.routes`` as a package.
"""

from .ledger_api import router as ledger_router

__all__ = ["ledger_router"]

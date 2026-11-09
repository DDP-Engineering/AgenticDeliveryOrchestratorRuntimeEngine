#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file server.py
@brief Entrypoint for the optional ADORE web service.
@details Binds loopback by default; a reverse proxy supplies TLS for remote use.
"""

# IMPORTS
import argparse
from pathlib import Path

import uvicorn

from adore.web.app import create_app


# PUBLIC API
def main(argv: list[str] | None = None) -> int:
    """@brief Run the bundled web API and frontend."""
    parser = argparse.ArgumentParser(description="ADORE web interface")
    parser.add_argument("--home", type=Path, default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if args.host not in ("127.0.0.1", "::1", "localhost"):
        parser.error("bind to loopback and use a TLS reverse proxy for remote access")
    uvicorn.run(create_app(args.home), host=args.host, port=args.port,
                proxy_headers=True, forwarded_allow_ips="127.0.0.1,::1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# END OF FILE

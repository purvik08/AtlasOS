#!/usr/bin/env python
"""Generate OpenAPI spec for Atlas OS API.

Usage:
    python scripts/generate_openapi.py
    python scripts/generate_openapi.py --output docs/api/openapi.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure we can import atlas modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from atlas.api import create_api_app
from atlas.config.loader import load_config
from atlas.runtime.application import AtlasApplication


def generate_openapi_spec(output_path: Path) -> None:
    """Generate OpenAPI spec and write to file."""
    # Load config
    config = load_config("configs/atlas.yaml")

    # Create application and API app
    app = AtlasApplication(config)
    fastapi_app = create_api_app(app)

    # Generate OpenAPI spec
    openapi_spec = fastapi_app.openapi()

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write spec
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(openapi_spec, f, indent=2)

    print(f"OpenAPI spec written to {output_path}")
    print(f"  Paths: {len(openapi_spec.get('paths', {}))}")
    print(f"  Components: {len(openapi_spec.get('components', {}).get('schemas', {}))}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate OpenAPI spec for Atlas OS API")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("docs/api/openapi.json"),
        help="Output path for OpenAPI spec (default: docs/api/openapi.json)",
    )
    args = parser.parse_args()

    try:
        generate_openapi_spec(args.output)
        return 0
    except Exception as e:
        print(f"Error generating OpenAPI spec: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
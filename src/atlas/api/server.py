"""Run Atlas OS API server."""

import uvicorn

from atlas.api import create_api_app
from atlas.config.loader import load_config
from atlas.runtime.application import AtlasApplication


def main():
    config = load_config("configs/atlas.yaml")
    app = AtlasApplication(config)
    api_app = create_api_app(app)
    
    import sys
    if sys.platform == "win32":
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    uvicorn.run(
        api_app,
        host="127.0.0.1",
        port=8000,
        loop="asyncio",
    )


if __name__ == "__main__":
    main()
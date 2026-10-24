import argparse
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.config import Config, ROOT
from app.state.app_state import AppState
from app.runtime import Runtime
from app.api.routes import router as api_router
from app.api.websocket import router as ws_router


def create_app(config=None, start_runtime=True):
    config = config or Config.from_env()
    state = AppState(config)

    @asynccontextmanager
    async def lifespan(app):
        if start_runtime:
            app.state.runtime.start()
        try:
            yield
        finally:
            if start_runtime:
                app.state.runtime.stop()

    app = FastAPI(title="Halloween Dance Display", version="1.0.0", lifespan=lifespan)
    app.state.show = state
    app.state.shutting_down = False
    app.state.runtime = Runtime(config, state) if start_runtime else None

    @app.middleware("http")
    async def local_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if (
            request.method == "POST"
            and origin
            and origin != f"{request.url.scheme}://{request.headers.get('host')}"
        ):
            return JSONResponse(
                {"detail": "Cross-origin control is disabled"}, status_code=403
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.include_router(api_router)
    app.include_router(ws_router)
    app.mount("/static", StaticFiles(directory=ROOT / "app/static"), name="static")

    @app.get("/")
    def dashboard():
        return FileResponse(ROOT / "app/static/index.html")

    return app


def main():
    parser = argparse.ArgumentParser(description="Local Halloween dance display")
    parser.add_argument(
        "--demo", action="store_true", help="Synthetic dancers; no webcam needed"
    )
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    values = Config.from_env().model_dump()
    if args.demo:
        values["demo_mode"] = True
    if args.port:
        values["port"] = args.port
    config = Config(**values)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    import uvicorn

    application = create_app(config)

    class ShowServer(uvicorn.Server):
        def handle_exit(self, sig, frame):
            # Finish long-lived MJPEG responses before waiting for connections.
            application.state.shutting_down = True
            super().handle_exit(sig, frame)

    server = ShowServer(
        uvicorn.Config(
            application,
            host=config.host,
            port=config.port,
            workers=1,
            ws_max_size=8192,
            timeout_graceful_shutdown=3,
        )
    )
    server.run()


if __name__ == "__main__":
    main()

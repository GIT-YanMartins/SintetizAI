from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from aplicacao.configuracao import get_settings
from aplicacao.rotas.resumos import SummaryController


class ApplicationFactory:
    """Assembles the FastAPI application, routes, middleware and static frontend."""

    @staticmethod
    def create() -> FastAPI:
        settings = get_settings()

        app = FastAPI(
            title="SintetizaAI — Resumo Automático de Textos",
            description=(
                "API desenvolvida para resumir textos extensos, relatórios e solicitações "
                "com saída JSON estruturada e integração com fluxo n8n."
            ),
            version="1.0.0",
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        controller = SummaryController()
        app.include_router(controller.router)

        frontend_dir = settings.frontend_dir
        if frontend_dir.exists():
            styles_dir = frontend_dir / "estilos"
            scripts_dir = frontend_dir / "scripts"
            if styles_dir.exists():
                app.mount(
                    "/estilos",
                    StaticFiles(directory=str(styles_dir)),
                    name="estilos",
                )
            if scripts_dir.exists():
                app.mount(
                    "/scripts",
                    StaticFiles(directory=str(scripts_dir)),
                    name="scripts",
                )

            @app.get("/", include_in_schema=False)
            async def serve_frontend() -> FileResponse:
                return FileResponse(str(frontend_dir / "index.html"))

        return app


app = ApplicationFactory.create()

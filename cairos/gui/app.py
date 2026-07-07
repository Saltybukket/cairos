"""FastAPI application factory for the optional CAIROS GUI."""

from pathlib import Path
from typing import Any, Callable

from . import actions
from .security import mask_secret_text, same_origin, token_matches
from .state import PROVIDER_PRESETS, load_gui_state


def create_app(session_token: str, debug: bool = False) -> Any:
    """Create the local-only FastAPI app.

    Imports are intentionally lazy so normal CLI usage does not require GUI
    dependencies.
    """
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates

    root = Path(__file__).resolve().parent
    templates = Jinja2Templates(directory=str(root / "templates"))
    app = FastAPI(title="CAIROS GUI", debug=debug)
    app.mount("/static", StaticFiles(directory=str(root / "static")), name="static")

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Callable[..., Any]) -> Any:
        response = await call_next(request)
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def context(request: Request, alert: Any = None) -> dict[str, Any]:
        return {
            "request": request,
            "state": load_gui_state(),
            "token": session_token,
            "alert": alert,
            "presets": PROVIDER_PRESETS,
        }

    def render(request: Request, template: str, alert: Any = None) -> HTMLResponse:
        return templates.TemplateResponse(name=template, context=context(request, alert), request=request)

    async def require_post_token(request: Request) -> dict[str, Any]:
        if not same_origin(request.url, request.headers.get("origin")):
            raise HTTPException(status_code=403, detail="Cross-origin POST rejected")
        form = dict(await request.form())
        if not token_matches(session_token, str(form.get("token") or "")):
            raise HTTPException(status_code=403, detail="Missing or invalid GUI session token")
        return form

    async def handle_action(request: Request, func: Callable[..., Any], partial: str, **kwargs: Any) -> HTMLResponse:
        try:
            result = func(**kwargs)
        except Exception as exc:  # pragma: no cover - defensive UI guard
            result = actions.ActionResult(False, mask_secret_text(str(exc)), "error")
        return render(request, partial, result)

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return render(request, "index.html")

    @app.get("/partials/overview", response_class=HTMLResponse)
    async def overview(request: Request) -> HTMLResponse:
        return render(request, "partials/overview.html")

    @app.get("/partials/profiles", response_class=HTMLResponse)
    async def profiles(request: Request) -> HTMLResponse:
        return render(request, "partials/profiles.html")

    @app.get("/partials/provider-setup", response_class=HTMLResponse)
    async def provider_setup(request: Request) -> HTMLResponse:
        return render(request, "partials/provider_setup.html")

    @app.get("/partials/fallback", response_class=HTMLResponse)
    async def fallback(request: Request) -> HTMLResponse:
        return render(request, "partials/fallback.html")

    @app.get("/partials/doctor", response_class=HTMLResponse)
    async def doctor(request: Request) -> HTMLResponse:
        return render(request, "partials/doctor.html")

    @app.get("/partials/update", response_class=HTMLResponse)
    async def update(request: Request) -> HTMLResponse:
        return render(request, "partials/update.html")

    @app.post("/profiles/switch", response_class=HTMLResponse)
    async def switch_profile(request: Request) -> HTMLResponse:
        form = await require_post_token(request)
        return await handle_action(request, actions.switch_profile, "partials/profiles.html", profile_name=str(form.get("profile_name") or ""))

    @app.post("/profiles/create/openrouter-free", response_class=HTMLResponse)
    async def create_openrouter_free(request: Request) -> HTMLResponse:
        form = await require_post_token(request)
        return await handle_action(request, actions.create_openrouter_free_profile, "partials/provider_setup.html", profile_name=str(form.get("profile_name") or "openrouter-free"))

    @app.post("/profiles/create/gemini", response_class=HTMLResponse)
    async def create_gemini(request: Request) -> HTMLResponse:
        form = await require_post_token(request)
        return await handle_action(
            request,
            actions.create_gemini_profile,
            "partials/provider_setup.html",
            profile_name=str(form.get("profile_name") or "gemini-flash"),
            model=str(form.get("model") or "gemini-2.5-flash"),
            api_key_env=str(form.get("api_key_env") or "GEMINI_API_KEY"),
        )

    @app.post("/profiles/create/groq", response_class=HTMLResponse)
    async def create_groq(request: Request) -> HTMLResponse:
        form = await require_post_token(request)
        return await handle_action(
            request,
            actions.create_groq_profile,
            "partials/provider_setup.html",
            profile_name=str(form.get("profile_name") or "groq-llama"),
            model=str(form.get("model") or "llama-3.1-8b-instant"),
            api_key_env=str(form.get("api_key_env") or "GROQ_API_KEY"),
        )

    @app.post("/profiles/create/openai", response_class=HTMLResponse)
    async def create_openai(request: Request) -> HTMLResponse:
        form = await require_post_token(request)
        return await handle_action(
            request,
            actions.create_openai_profile,
            "partials/provider_setup.html",
            profile_name=str(form.get("profile_name") or "openai-mini"),
            model=str(form.get("model") or "gpt-4.1-mini"),
            api_key_env=str(form.get("api_key_env") or "OPENAI_API_KEY"),
            endpoint=str(form.get("endpoint") or "https://api.openai.com/v1"),
        )

    @app.post("/profiles/create/ollama", response_class=HTMLResponse)
    async def create_ollama(request: Request) -> HTMLResponse:
        form = await require_post_token(request)
        return await handle_action(
            request,
            actions.create_ollama_profile,
            "partials/provider_setup.html",
            profile_name=str(form.get("profile_name") or "ollama-local"),
            model=str(form.get("model") or "llama3.1"),
            endpoint=str(form.get("endpoint") or "http://localhost:11434"),
        )

    @app.post("/profiles/test", response_class=HTMLResponse)
    async def test_profile(request: Request) -> HTMLResponse:
        await require_post_token(request)
        return await handle_action(request, actions.run_ai_doctor, "partials/doctor.html")

    @app.post("/fallback/toggle", response_class=HTMLResponse)
    async def toggle_fallback(request: Request) -> HTMLResponse:
        form = await require_post_token(request)
        return await handle_action(request, actions.toggle_auto_fallback, "partials/fallback.html", enabled=str(form.get("enabled") or "") == "true")

    @app.post("/fallback/persist", response_class=HTMLResponse)
    async def toggle_persist(request: Request) -> HTMLResponse:
        form = await require_post_token(request)
        return await handle_action(request, actions.toggle_persist_switch, "partials/fallback.html", enabled=str(form.get("enabled") or "") == "true")

    @app.post("/fallback/reorder", response_class=HTMLResponse)
    async def reorder_fallback(request: Request) -> HTMLResponse:
        form = await require_post_token(request)
        order = [item.strip() for item in str(form.get("order") or "").replace(",", " ").split() if item.strip()]
        return await handle_action(request, actions.set_fallback_order, "partials/fallback.html", names=order)

    @app.post("/doctor/run", response_class=HTMLResponse)
    async def run_doctor(request: Request) -> HTMLResponse:
        await require_post_token(request)
        return await handle_action(request, actions.run_ai_doctor, "partials/doctor.html")

    @app.post("/config/backup", response_class=HTMLResponse)
    async def backup_config(request: Request) -> HTMLResponse:
        await require_post_token(request)
        return await handle_action(request, actions.backup_config, "partials/update.html")

    return app

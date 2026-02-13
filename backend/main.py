from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import httpx
import os
import html

app = FastAPI(title="Hand-E Demo App")

# Configuration Hand-E
API_URL = os.getenv("HAND_E_API_URL", "http://localhost:3001/api")
APP_SECRET = os.getenv("HAND_E_APP_SECRET")
DEPLOYMENT_ID = os.getenv("HAND_E_DEPLOYMENT_ID")
print(f"API_URL: {API_URL}")
print(f"APP_SECRET: {'***' if APP_SECRET else 'None'}")
print(f"DEPLOYMENT_ID: {DEPLOYMENT_ID}")

COOKIE_NAME = "hande_user_token"
COOKIE_MAX_AGE = 7 * 24 * 3600  # 7 days


async def get_hand_e_context():
    if not APP_SECRET:
        return {"status": "offline", "message": "Secret non configuré"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_URL}/sdk/me",
                headers={"X-HandE-Secret": APP_SECRET},
                timeout=5.0,
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}


async def get_current_sdk_user(user_token: str | None) -> dict | None:
    if not user_token or not APP_SECRET:
        return None
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_URL}/sdk/me/user",
                headers={
                    "X-HandE-Secret": APP_SECRET,
                    "X-HandE-User-Token": user_token,
                },
                timeout=5.0,
            )
            data = response.json()
            return data.get("user") if response.status_code == 200 else None
        except Exception:
            return None


def _h(s: str) -> str:
    """Escape for HTML."""
    return html.escape(s) if s else ""


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    context = await get_hand_e_context()
    user_token = request.cookies.get(COOKIE_NAME)
    current_user = await get_current_sdk_user(user_token) if user_token else None
    access_mode = context.get("accessMode", "PUBLIC")
    access_mode_label = "Public (*)" if access_mode == "PUBLIC" else "Liste restreinte"
    login_error = request.query_params.get("error")
    error_messages = {
        "offline": "SDK non configuré (mode hors ligne).",
        "invalid": "Email ou mot de passe incorrect.",
        "no_token": "Réponse Hand-E invalide.",
        "injoignable": "Impossible de joindre Hand-E. Vérifiez HAND_E_API_URL.",
    }
    error_text = error_messages.get(login_error, _h(login_error)) if login_error else ""

    # Contexte pour le template
    owner_email = context.get("user", {}).get("email", "Invité")
    owner_company = context.get("user", {}).get("company", "N/A")
    pricing = context.get("application", {}).get("pricingModel", "FREE")
    memory = context.get("resources", {}).get("memory", "512m")

    if current_user:
        login_block = f"""
            <div class="rounded-xl bg-emerald-50 border border-emerald-100 p-4">
                <p class="text-sm font-semibold text-emerald-800">Connecté (SDK)</p>
                <p class="mt-1 text-slate-700">{_h(current_user.get("email", ""))}</p>
                <form method="post" action="/logout" class="mt-3">
                    <button type="submit" class="text-sm text-emerald-600 hover:text-emerald-800 font-medium">Se déconnecter</button>
                </form>
            </div>
        """
        usage_note = f"L'usage sera attribué à <strong>{_h(current_user.get('email', ''))}</strong>."
    else:
        error_html = f'<div class="mb-3 rounded-lg bg-red-50 border border-red-100 text-red-700 px-3 py-2 text-sm">{error_text}</div>' if error_text else ""
        login_block = f"""
            <div class="rounded-xl bg-slate-50 border border-slate-200 p-4">
                <p class="text-sm font-semibold text-slate-700 mb-3">Connexion (compte Hand-E)</p>
                {error_html}
                <form method="post" action="/login" class="space-y-3">
                    <input type="email" name="email" placeholder="Email" required
                        class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
                    <input type="password" name="password" placeholder="Mot de passe" required
                        class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
                    <button type="submit" class="w-full bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium py-2 px-4 rounded-lg">
                        Se connecter
                    </button>
                </form>
                <p class="mt-2 text-xs text-slate-500">En mode liste restreinte, seuls les utilisateurs autorisés peuvent se connecter.</p>
            </div>
        """
        usage_note = "Connectez-vous pour attribuer l'usage à votre compte (KPIs par utilisateur)."

    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hand-E Demo App</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css"/>
    </head>
    <body class="bg-slate-50 min-h-screen font-sans text-slate-900">
        <div class="max-w-4xl mx-auto py-12 px-4">
            <header class="flex items-center justify-between mb-12 animate__animated animate__fadeInDown">
                <div class="flex items-center gap-4">
                    <div class="bg-emerald-600 text-white p-3 rounded-2xl shadow-lg shadow-emerald-200">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                    </div>
                    <div>
                        <h1 class="text-2xl font-bold">Hand-E App Demo</h1>
                        <p class="text-slate-500 text-sm">Identité : {_h((DEPLOYMENT_ID or "Locale")[:8])}</p>
                    </div>
                </div>
                <span class="px-4 py-1.5 rounded-full text-xs font-bold tracking-wider uppercase bg-emerald-100 text-emerald-700 border border-emerald-200">
                    Hand-E Native
                </span>
            </header>

            <div class="grid md:grid-cols-2 gap-8">
                <section class="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm animate__animated animate__fadeInLeft animate__delay-1s">
                    <h2 class="text-lg font-bold mb-6 flex items-center gap-2">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-slate-400" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd" />
                        </svg>
                        Contexte Hand-E
                    </h2>
                    <div class="space-y-4">
                        <div class="flex justify-between items-center py-3 border-b border-slate-50">
                            <span class="text-slate-500">Propriétaire déploiement</span>
                            <span class="font-semibold text-slate-700">{_h(owner_email)}</span>
                        </div>
                        <div class="flex justify-between items-center py-3 border-b border-slate-50">
                            <span class="text-slate-500">Entreprise</span>
                            <span class="font-semibold text-slate-700">{_h(owner_company)}</span>
                        </div>
                        <div class="flex justify-between items-center py-3 border-b border-slate-50">
                            <span class="text-slate-500">Mode d'accès</span>
                            <span class="px-3 py-1 rounded-lg text-xs font-bold { 'bg-sky-100 text-sky-700' if access_mode == 'PUBLIC' else 'bg-amber-100 text-amber-700' }">{_h(access_mode_label)}</span>
                        </div>
                        <div class="flex justify-between items-center py-3 border-b border-slate-50">
                            <span class="text-slate-500">Plan Tarifaire</span>
                            <span class="px-3 py-1 bg-amber-100 text-amber-700 rounded-lg text-xs font-bold">{_h(pricing)}</span>
                        </div>
                        <div class="flex justify-between items-center py-3">
                            <span class="text-slate-500">Mémoire Allouée</span>
                            <span class="font-semibold text-slate-700">{_h(memory)}</span>
                        </div>
                    </div>

                    <h3 class="text-sm font-bold mt-6 mb-3 text-slate-700">Utilisateur connecté (SDK)</h3>
                    {login_block}
                </section>

                <section class="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm animate__animated animate__fadeInRight animate__delay-1s">
                    <h2 class="text-lg font-bold mb-6 flex items-center gap-2">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-slate-400" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z" />
                            <path fill-rule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z" clip-rule="evenodd" />
                        </svg>
                        Test de Consommation
                    </h2>
                    <p class="text-slate-500 text-sm mb-2 leading-relaxed">
                        Cliquez pour simuler une action payante. Le SDK enverra un rapport d'usage à Hand-E.
                    </p>
                    <p class="text-slate-500 text-xs mb-6">{usage_note}</p>
                    <button id="taskBtn" onclick="executeTask()" class="w-full bg-slate-900 hover:bg-slate-800 text-white font-bold py-4 px-6 rounded-2xl transition-all active:scale-95 shadow-xl shadow-slate-200 flex items-center justify-center gap-3">
                        <span id="btnText">Exécuter une tâche (+1.0 unité)</span>
                        <div id="btnLoader" class="hidden animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                    </button>
                    <div id="feedback" class="mt-6 hidden animate__animated animate__fadeInUp">
                        <div class="bg-emerald-50 border border-emerald-100 text-emerald-700 px-4 py-3 rounded-xl text-sm flex items-center gap-3">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                            </svg>
                            Usage rapporté avec succès !
                        </div>
                    </div>
                </section>
            </div>

            <footer class="mt-12 text-center text-slate-400 text-sm">
                Démo propulsée par le Hand-E SDK — Login, accès restreint et consommation par utilisateur
            </footer>
        </div>

        <script>
            async function executeTask() {{
                const btn = document.getElementById('taskBtn');
                const btnText = document.getElementById('btnText');
                const btnLoader = document.getElementById('btnLoader');
                const feedback = document.getElementById('feedback');
                btn.disabled = true;
                btnText.textContent = 'Envoi au SDK...';
                btnLoader.classList.remove('hidden');
                feedback.classList.add('hidden');
                try {{
                    const response = await fetch('/execute-task', {{ method: 'POST', credentials: 'same-origin' }});
                    const data = await response.json();
                    if (response.ok) {{
                        feedback.classList.remove('hidden');
                    }} else {{
                        alert('Erreur: ' + (data.detail || data.message || 'inconnue'));
                    }}
                }} catch (e) {{
                    alert('Erreur réseau');
                }} finally {{
                    btn.disabled = false;
                    btnText.textContent = 'Exécuter une tâche (+1.0 unité)';
                    btnLoader.classList.add('hidden');
                }}
            }}
        </script>
    </body>
    </html>
    """
    return html_content


@app.post("/login")
async def login(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
):
    if not APP_SECRET:
        return RedirectResponse(url="/?error=offline", status_code=303)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_URL}/sdk/auth/login",
                json={"email": email.strip(), "password": password},
                headers={"X-HandE-Secret": APP_SECRET},
                timeout=10.0,
            )
            if response.status_code != 200:
                return RedirectResponse(url="/?error=invalid", status_code=303)
            data = response.json()
            token = data.get("token")
            if not token:
                return RedirectResponse(url="/?error=no_token", status_code=303)
            redir = RedirectResponse(url="/", status_code=303)
            redir.set_cookie(
                key=COOKIE_NAME,
                value=token,
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax",
                path="/",
            )
            return redir
        except Exception as e:
            return RedirectResponse(url=f"/?error=injoignable", status_code=303)


@app.post("/logout")
async def logout():
    redir = RedirectResponse(url="/", status_code=303)
    redir.delete_cookie(COOKIE_NAME, path="/")
    return redir


@app.post("/execute-task")
async def execute_task(request: Request):
    user_token = request.cookies.get(COOKIE_NAME)
    headers = {"X-HandE-Secret": APP_SECRET} if APP_SECRET else {}
    if user_token:
        headers["X-HandE-User-Token"] = user_token

    if APP_SECRET:
        print(f"[SDK] Reporting usage to {API_URL}/sdk/usage... (user_token={'yes' if user_token else 'no'})")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{API_URL}/sdk/usage",
                    json={"metric": "task_execution", "value": 1.0},
                    headers=headers,
                    timeout=5.0,
                )
                print(f"[SDK] Response Status: {response.status_code}")
                if response.status_code not in [200, 201]:
                    print(f"[SDK] Error Body: {response.text}")
                response.raise_for_status()
            except Exception as e:
                print(f"[SDK] Request Failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Injoignable ({API_URL}): {str(e)}")
    else:
        print("[Offline] Usage reported: task_execution = 1.0")

    return {"message": "Tâche exécutée", "reported": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

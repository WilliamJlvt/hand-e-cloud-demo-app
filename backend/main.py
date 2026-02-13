from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import httpx
import os
import html
import json

app = FastAPI(title="Reactor — Hand-E Demo Chatbot")

API_URL = os.getenv("HAND_E_API_URL", "http://localhost:3001/api")
APP_SECRET = os.getenv("HAND_E_APP_SECRET")
DEPLOYMENT_ID = os.getenv("HAND_E_DEPLOYMENT_ID")
print(f"API_URL: {API_URL}")
print(f"APP_SECRET: {'***' if APP_SECRET else 'None'}")
print(f"DEPLOYMENT_ID: {DEPLOYMENT_ID}")

COOKIE_NAME = "hande_user_token"
COOKIE_MAX_AGE = 7 * 24 * 3600


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
    return html.escape(s) if s else ""


def _js(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    context = await get_hand_e_context()
    user_token = request.cookies.get(COOKIE_NAME)
    current_user = await get_current_sdk_user(user_token) if user_token else None
    login_error = request.query_params.get("error")
    error_messages = {
        "offline": "SDK non configuré (mode hors ligne).",
        "invalid": "Email ou mot de passe incorrect.",
        "no_token": "Réponse Hand-E invalide.",
        "injoignable": "Impossible de joindre Hand-E.",
    }
    error_text = error_messages.get(login_error, _h(login_error)) if login_error else ""
    owner_id = context.get("user", {}).get("id") or ""
    is_owner = bool(current_user and owner_id and current_user.get("id") == owner_id)

    # Données pour le front
    page_config = {
        "ownerId": owner_id,
        "currentUser": (
            {
                "id": current_user.get("id"),
                "email": current_user.get("email"),
                "firstName": current_user.get("firstName"),
                "lastName": current_user.get("lastName"),
            }
            if current_user
            else None
        ),
        "isOwner": is_owner,
        "loginError": error_text,
    }

    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reactor — Chatbot Hand-E</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen font-sans antialiased">
        <div id="app" class="flex flex-col h-screen max-w-3xl mx-auto">
            <!-- Barre supérieure: logo + login ou user + admin -->
            <header class="flex items-center justify-between px-4 py-3 border-b border-slate-800 shrink-0">
                <div class="flex items-center gap-2">
                    <span class="text-emerald-400 font-bold text-lg">Reactor</span>
                    <span class="text-slate-500 text-xs">Hand-E SDK</span>
                </div>
                <div id="headerAuth" class="flex items-center gap-3"></div>
            </header>

            <!-- Zone login (si non connecté) -->
            <div id="loginSection" class="p-6 border-b border-slate-800">
                <p class="text-sm text-slate-400 mb-3">Connectez-vous pour discuter et voir votre consommation.</p>
                <div id="loginError" class="mb-3 hidden rounded-lg bg-red-900/30 border border-red-800 text-red-200 px-3 py-2 text-sm"></div>
                <form id="loginForm" method="post" action="/login" class="space-y-3">
                    <input type="email" name="email" placeholder="Email" required
                        class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-emerald-500" />
                    <input type="password" name="password" placeholder="Mot de passe" required
                        class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-emerald-500" />
                    <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2 px-4 rounded-lg text-sm">
                        Se connecter
                    </button>
                </form>
            </div>

            <!-- Zone chat (si connecté) -->
            <div id="chatSection" class="hidden flex-1 flex flex-col min-h-0">
                <div id="messages" class="flex-1 overflow-y-auto p-4 space-y-4"></div>
                <div class="p-4 border-t border-slate-800">
                    <form id="chatForm" class="flex gap-2">
                        <input id="chatInput" type="text" placeholder="Écrivez un message..."
                            class="flex-1 rounded-xl bg-slate-800 border border-slate-700 px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-emerald-500" />
                        <button type="submit" class="bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-5 py-3 rounded-xl text-sm shrink-0">
                            Envoyer
                        </button>
                    </form>
                    <p class="mt-2 text-xs text-slate-500">Chaque message rapporte 1 unité d'usage (attribuée à votre compte).</p>
                </div>
            </div>

            <!-- Onglet Admin (propriétaire uniquement) -->
            <div id="adminSection" class="hidden border-t border-slate-800 flex flex-col max-h-80">
                <div class="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                    <span class="font-semibold text-slate-200">Admin — Consommation par utilisateur</span>
                    <button id="adminRefresh" type="button" class="text-sm text-emerald-400 hover:text-emerald-300">Rafraîchir</button>
                </div>
                <div id="adminContent" class="flex-1 overflow-auto p-4 text-sm">
                    <p class="text-slate-500">Chargement...</p>
                </div>
            </div>
        </div>

        <script>
            const CONFIG = {_js(page_config)};

            (function() {{
                const headerAuth = document.getElementById('headerAuth');
                const loginSection = document.getElementById('loginSection');
                const chatSection = document.getElementById('chatSection');
                const adminSection = document.getElementById('adminSection');
                const loginErrorEl = document.getElementById('loginError');
                const messagesEl = document.getElementById('messages');
                const chatForm = document.getElementById('chatForm');
                const chatInput = document.getElementById('chatInput');

                if (CONFIG.loginError) {{
                    loginErrorEl.textContent = CONFIG.loginError;
                    loginErrorEl.classList.remove('hidden');
                }}

                if (CONFIG.currentUser) {{
                    loginSection.classList.add('hidden');
                    chatSection.classList.remove('hidden');
                    headerAuth.innerHTML = `
                        <span class="text-slate-400 text-sm">${{CONFIG.currentUser.email}}</span>
                        <form method="post" action="/logout" class="inline">
                            <button type="submit" class="text-slate-500 hover:text-slate-300 text-xs">Déconnexion</button>
                        </form>
                    `;
                    if (CONFIG.isOwner) {{
                        adminSection.classList.remove('hidden');
                        loadAdminConsumption();
                    }}
                }} else {{
                    headerAuth.innerHTML = '<span class="text-slate-500 text-sm">Non connecté</span>';
                }}

                function addMessage(role, text, isStreaming) {{
                    const div = document.createElement('div');
                    div.className = 'flex gap-3 ' + (role === 'user' ? 'justify-end' : '');
                    const bubble = document.createElement('div');
                    bubble.className = 'max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ' +
                        (role === 'user' ? 'bg-emerald-600/80 text-white' : 'bg-slate-800 text-slate-200 border border-slate-700');
                    bubble.textContent = text;
                    if (isStreaming) bubble.classList.add('animate-pulse');
                    div.appendChild(bubble);
                    messagesEl.appendChild(div);
                    messagesEl.scrollTop = messagesEl.scrollHeight;
                    return bubble;
                }}

                chatForm.addEventListener('submit', async (e) => {{
                    e.preventDefault();
                    const text = chatInput.value.trim();
                    if (!text) return;
                    chatInput.value = '';
                    addMessage('user', text, false);
                    const botBubble = addMessage('assistant', '…', true);
                    try {{
                        const r = await fetch('/chat', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            credentials: 'same-origin',
                            body: JSON.stringify({{ message: text }})
                        }});
                        const data = await r.json();
                        const reply = data.reply || 'Message reçu. (Usage enregistré.)';
                        botBubble.classList.remove('animate-pulse');
                        botBubble.textContent = reply;
                    }} catch (err) {{
                        botBubble.classList.remove('animate-pulse');
                        botBubble.textContent = 'Erreur réseau.';
                    }}
                    messagesEl.scrollTop = messagesEl.scrollHeight;
                }});

                async function loadAdminConsumption() {{
                    const el = document.getElementById('adminContent');
                    el.innerHTML = '<p class="text-slate-500">Chargement...</p>';
                    try {{
                        const r = await fetch('/admin/consumption', {{ credentials: 'same-origin' }});
                        if (!r.ok) {{
                            el.innerHTML = '<p class="text-red-400">Réservé au propriétaire du déploiement.</p>';
                            return;
                        }}
                        const data = await r.json();
                        let html = '<p class="text-slate-400 mb-2">Crédits déploiement: <strong>' + data.deploymentCreditsUsed + '</strong></p>';
                        if (data.anonymousTotal > 0) html += '<p class="text-slate-400 mb-2">Usage anonyme: ' + data.anonymousTotal + '</p>';
                        html += '<table class="w-full text-left"><thead><tr class="text-slate-500 border-b border-slate-700"><th>Utilisateur</th><th>Total</th><th>Métriques</th></tr></thead><tbody>';
                        (data.byUser || []).forEach(function(u) {{
                            const name = (u.firstName || '') + ' ' + (u.lastName || '').trim() || u.email;
                            const metrics = Object.entries(u.metrics || {{}}).map(function([k,v]) {{ return k + ': ' + v; }}).join(', ');
                            html += '<tr class="border-b border-slate-800"><td class="py-2">' + (u.email || u.userId) + '</td><td class="py-2">' + u.totalValue + '</td><td class="py-2 text-slate-500">' + metrics + '</td></tr>';
                        }});
                        if (!data.byUser || data.byUser.length === 0) html += '<tr><td colspan="3" class="py-4 text-slate-500">Aucune donnée par utilisateur.</td></tr>';
                        html += '</tbody></table>';
                        el.innerHTML = html;
                    }} catch (err) {{
                        el.innerHTML = '<p class="text-red-400">Erreur: ' + err.message + '</p>';
                    }}
                }}

                document.getElementById('adminRefresh').addEventListener('click', loadAdminConsumption);
            }})();
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
        except Exception:
            return RedirectResponse(url="/?error=injoignable", status_code=303)


@app.post("/logout")
async def logout():
    redir = RedirectResponse(url="/", status_code=303)
    redir.delete_cookie(COOKIE_NAME, path="/")
    return redir


def _sdk_headers(request: Request):
    headers = {"X-HandE-Secret": APP_SECRET} if APP_SECRET else {}
    token = request.cookies.get(COOKIE_NAME)
    if token:
        headers["X-HandE-User-Token"] = token
    return headers


@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    message = (body.get("message") or "").strip() or "Hello"
    headers = _sdk_headers(request)

    if APP_SECRET:
        async with httpx.AsyncClient() as client:
            try:
                await client.post(
                    f"{API_URL}/sdk/usage",
                    json={"metric": "chat_message", "value": 1.0},
                    headers=headers,
                    timeout=5.0,
                )
            except Exception as e:
                print(f"[SDK] Usage failed: {e}")

    # Réponse type chatbot légère
    replies = [
        f"Reçu : « {message} ». Votre usage a été enregistré.",
        "Message noté. Consommation attribuée à votre compte.",
        "OK ! Une unité d'usage a été rapportée au SDK Hand-E.",
    ]
    import random
    reply = random.choice(replies)
    return {"reply": reply, "reported": True}


@app.get("/admin/consumption")
async def admin_consumption(request: Request):
    """Proxy vers Hand-E GET /sdk/consumption-by-user (réservé au propriétaire)."""
    token = request.cookies.get(COOKIE_NAME)
    if not token or not APP_SECRET:
        raise HTTPException(status_code=401, detail="Non connecté")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_URL}/sdk/consumption-by-user",
                headers={
                    "X-HandE-Secret": APP_SECRET,
                    "X-HandE-User-Token": token,
                },
                timeout=10.0,
            )
            if response.status_code == 403:
                raise HTTPException(status_code=403, detail="Réservé au propriétaire du déploiement")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

from fastapi import FastAPI, HTTPException, Header
import httpx
import os
import time

app = FastAPI(title="Hand-E Demo App")

# Configuration Hand-E (injectée par la plateforme)
API_URL = os.getenv("HAND_E_API_URL", "http://backend:3000/api")
APP_SECRET = os.getenv("HAND_E_APP_SECRET")
DEPLOYMENT_ID = os.getenv("HAND_E_DEPLOYMENT_ID")

async def report_usage(metric: str, value: float):
    """Simule l'appel au SDK Hand-E"""
    if not APP_SECRET:
        print(f"[Offline] Usage reported: {metric} = {value}")
        return
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_URL}/sdk/usage",
                json={"metric": metric, "value": value},
                headers={"X-HandE-Secret": APP_SECRET}
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to report usage: {e}")

@app.get("/")
async def root():
    """Récupère le contexte via le SDK"""
    context = {"status": "offline", "message": "Secret non configuré"}
    
    if APP_SECRET:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{API_URL}/sdk/me",
                    headers={"X-HandE-Secret": APP_SECRET}
                )
                context = response.json()
            except Exception as e:
                context = {"error": str(e)}

    return {
        "app": "Hand-E Demo Application",
        "version": "1.0.0",
        "hand_e_context": context
    }

@app.post("/execute-task")
async def execute_task():
    """Simule une tâche coûteuse qui facture l'utilisateur"""
    start_time = time.time()
    
    # Simulation de travail
    time.sleep(0.5)
    
    # Rapport de consommation : 1 tâche exécutée (valeur 1.0)
    # Dans Hand-E, vous pourriez avoir un prix par 'task_execution'
    await report_usage("task_execution", 1.0)
    
    return {
        "message": "Tâche exécutée avec succès",
        "cost": "1 execution unit reported to Hand-E",
        "duration": f"{time.time() - start_time:.2f}s"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

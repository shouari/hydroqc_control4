"""
Hydro-Quebec API Wrapper
General purpose REST API wrapper for Hydro-Quebec data.
Based on the hydroqc library by titilambert.

Wrapper API Hydro-Québec
Wrapper API REST à usage général pour les données d'Hydro-Québec.
Basé sur la librairie hydroqc de titilambert.
"""
import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, PlainTextResponse
from dotenv import load_dotenv
import httpx

from hydroqc.webuser import WebUser
from hydroqc.customer import Customer

# Load environment variables / Chargement des variables d'environnement
load_dotenv()

# Configure logging / Configuration de la journalisation
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("hydroqc_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
HYDRO_USERNAME = os.getenv("HYDRO_USERNAME")
HYDRO_PASSWORD = os.getenv("HYDRO_PASSWORD")
REFRESH_INTERVAL_SECONDS = 600  # 10 minutes

# Global client instance / Instance client globale
_webuser_client: Optional[WebUser] = None

# Global Cache / Cache global
class Cache:
    def __init__(self):
        self.peak_events = []
        self.customers = []
        self.consumption = []
        self.balances = []
        self.last_updated = None
        self.initialized = False

_data_cache = Cache()
_background_task: Optional[asyncio.Task] = None


async def get_webuser() -> WebUser:
    """
    Get or create authenticated WebUser instance
    Obtenir ou créer une instance WebUser authentifiée
    """
    global _webuser_client
    
    if not HYDRO_USERNAME or not HYDRO_PASSWORD:
        logger.error("❌ Credentials missing in .env file / Identifiants manquants dans le fichier .env")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hydro-Quebec credentials not configured. Please set HYDRO_USERNAME and HYDRO_PASSWORD in .env file"
        )
    
    if _webuser_client is None:
        try:
            logger.info(f"🔐 Attempting login for user: {HYDRO_USERNAME}")
            _webuser_client = WebUser(
                HYDRO_USERNAME, 
                HYDRO_PASSWORD, 
                verify_ssl=True,
                log_level="DEBUG"
            )
            await _webuser_client.login()
            logger.info("✅ Login successful / Connexion réussie")
            
        except Exception as e:
            logger.error(f"❌ Login failed: {str(e)}", exc_info=True)
            _webuser_client = None
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}"
            )
    
    return _webuser_client


async def refresh_cache():
    """
    Fetch all data from Hydro-Quebec and update the global cache
    Récupérer toutes les données d'Hydro-Québec et mettre à jour le cache global
    """
    global _data_cache
    logger.info("🔄 Starting cache refresh... / Démarrage du rafraîchissement du cache...")
    
    try:
        webuser = await get_webuser()
        
        # CRITICAL: Must call get_info() to populate customers list
        # CRITIQUE : Doit appeler get_info() pour remplir la liste des clients
        await webuser.get_info()
        logger.info(f"📋 Found {len(webuser.customers)} customer(s) / Trouvé {len(webuser.customers)} client(s)")
        
        # Fetch additional info for each customer
        # Récupérer des informations supplémentaires pour chaque client
        for customer in webuser.customers:
            await customer.get_info()
            logger.info(f"👤 Customer {customer.customer_id}: {len(customer.accounts)} account(s)")

        # 1. Process Peak Events / Traiter les événements de pointe
        peak_events_data = []
        for customer in webuser.customers:
            if not hasattr(customer, 'accounts') or not customer.accounts:
                continue
            
            for account in customer.accounts:
                if not hasattr(account, 'contracts') or not account.contracts:
                    continue
                
                for contract in account.contracts:
                    # Check if contract has peak handler (Winter Credit / Rate D CPC)
                    # Vérifier si le contrat a un gestionnaire de pointe (Crédit hivernal / Tarif D CPC)
                    if not hasattr(contract, 'peak_handler') or not contract.peak_handler:
                        continue
                    
                    handler = contract.peak_handler
                    
                    # Refresh peak handler data / Rafraîchir les données du gestionnaire de pointe
                    try:
                        await handler.refresh_data()
                    except Exception as e:
                        logger.error(f"❌ Failed to refresh handler data: {e}")
                    
                    # Determine status / Déterminer le statut
                    is_peak = False
                    try:
                        is_peak = getattr(handler, 'current_peak_is_critical', None)
                        if is_peak is None:
                            is_peak = False
                    except Exception as e:
                        is_peak = False
                    
                    start_date = None
                    end_date = None
                    current_state = "unknown"
                    
                    try:
                        current_state = getattr(handler, 'current_state', 'unknown')
                    except Exception as e:
                        pass
                    
                    # Get current_peak if available / Obtenir le pic actuel si disponible
                    try:
                        current_peak = getattr(handler, 'current_peak', None)
                        next_critical = getattr(handler, 'next_critical_peak', None)
                        
                        if is_peak and current_peak:
                            start_date = getattr(current_peak, 'start_date', None)
                            end_date = getattr(current_peak, 'end_date', None)
                        elif next_critical:
                            start_date = getattr(next_critical, 'start_date', None)
                            end_date = getattr(next_critical, 'end_date', None)
                    except Exception as e:
                        pass
                    
                    peak_events_data.append({
                        "customer_id": customer.customer_id,
                        "account_id": account.account_id,
                        "contract_id": contract.contract_id,
                        "ispeak": is_peak,
                        "start": start_date.isoformat() if start_date else None,
                        "end": end_date.isoformat() if end_date else None,
                        "state": current_state
                    })

        # 2. Process Customers / Traiter les clients
        customers_data = []
        for customer in webuser.customers:
            if not hasattr(customer, 'accounts') or not customer.accounts:
                continue
                
            customer_data = {
                "customer_id": customer.customer_id,
                "accounts": []
            }
            
            for account in customer.accounts:
                account_data = {
                    "account_id": account.account_id,
                    "balance": getattr(account, 'balance', None),
                    "contracts": [
                        {
                            "contract_id": contract.contract_id,
                            "balance": getattr(contract, 'balance', None),
                        }
                        for contract in getattr(account, 'contracts', [])
                    ]
                }
                customer_data["accounts"].append(account_data)
            
            customers_data.append(customer_data)

        # 3. Process Consumption / Traiter la consommation
        consumption_data = []
        for customer in webuser.customers:
            if not hasattr(customer, 'accounts') or not customer.accounts:
                continue
                
            for account in customer.accounts:
                if not hasattr(account, 'contracts') or not account.contracts:
                    continue
                    
                for contract in account.contracts:
                    if hasattr(contract, 'current_period') and contract.current_period:
                        period = contract.current_period
                        consumption_data.append({
                            "contract_id": contract.contract_id,
                            "period_start": getattr(period, 'period_start_date', None),
                            "period_end": getattr(period, 'period_end_date', None),
                            "total_consumption": getattr(period, 'total_consumption', None),
                            "lower_price_consumption": getattr(period, 'lower_price_consumption', None),
                            "higher_price_consumption": getattr(period, 'higher_price_consumption', None),
                            "total_days": getattr(period, 'period_total_days', None),
                            "mean_daily_consumption": getattr(period, 'period_mean_daily_consumption', None),
                        })

        # 4. Process Balance / Traiter le solde
        balances_data = []
        for customer in webuser.customers:
            if not hasattr(customer, 'accounts') or not customer.accounts:
                continue
                
            for account in customer.accounts:
                if not hasattr(account, 'contracts') or not account.contracts:
                    continue
                    
                for contract in account.contracts:
                    balances_data.append({
                        "contract_id": contract.contract_id,
                        "balance": getattr(contract, 'balance', None),
                        "account_id": account.account_id,
                        "customer_id": customer.customer_id
                    })

        # Update Cache / Mettre à jour le cache
        _data_cache.peak_events = peak_events_data
        _data_cache.customers = customers_data
        _data_cache.consumption = consumption_data
        _data_cache.balances = balances_data
        _data_cache.last_updated = datetime.now()
        _data_cache.initialized = True
        
        logger.info(f"✅ Cache refreshed at / Cache rafraîchi à {_data_cache.last_updated}")
        
    except Exception as e:
        logger.error(f"❌ Error refreshing cache / Erreur lors du rafraîchissement du cache: {str(e)}", exc_info=True)
        # We don't raise here to keep the background task running


async def background_refresh_task():
    """
    Periodic background task to refresh data
    Tâche d'arrière-plan périodique pour rafraîchir les données
    """
    while True:
        await refresh_cache()
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown
    Gestionnaire de contexte de durée de vie pour le démarrage et l'arrêt
    """
    # Startup / Démarrage
    logger.info("🚀 Starting Hydro-Quebec API Wrapper / Démarrage du Wrapper API Hydro-Québec")
    
    # Start background task / Démarrer la tâche d'arrière-plan
    global _background_task
    _background_task = asyncio.create_task(background_refresh_task())
    
    yield
    
    # Shutdown / Arrêt
    logger.info("🛑 Shutting down Hydro-Quebec API Wrapper / Arrêt du Wrapper API Hydro-Québec")
    if _background_task:
        _background_task.cancel()
        try:
            await _background_task
        except asyncio.CancelledError:
            pass
            
    global _webuser_client
    if _webuser_client:
        await _webuser_client.close_session()


# Create FastAPI app / Créer l'application FastAPI
app = FastAPI(
    title="Hydro-Quebec API Wrapper",
    description="General purpose REST API wrapper for Hydro-Quebec data / Wrapper API REST à usage général pour les données d'Hydro-Québec",
    version="1.1.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """
    Health check endpoint
    Endpoint de vérification de l'état
    """
    return {
        "status": "running",
        "service": "Hydro-Quebec API Wrapper",
        "version": "1.1.0",
        "timestamp": datetime.now().isoformat(),
        "configured": bool(HYDRO_USERNAME and HYDRO_PASSWORD),
        "cache_initialized": _data_cache.initialized,
        "last_updated": _data_cache.last_updated.isoformat() if _data_cache.last_updated else None
    }


@app.get("/api/peak-events")
async def get_peak_events():
    """
    Get peak events information from cache
    Obtenir les informations sur les événements de pointe depuis le cache
    """
    if not _data_cache.initialized:
        # If cache not ready, try to wait a bit or return empty/error
        # Si le cache n'est pas prêt, essayez d'attendre un peu ou retournez vide/erreur
        logger.warning("⚠️ Cache not yet initialized, returning empty peak events / Cache pas encore initialisé, retour d'événements de pointe vides")
    
    return _data_cache.peak_events


@app.get("/api/control4/peak-status")
async def get_control4_peak_status():
    """
    Get simplified peak event status for Control4 integration
    Returns only the peak event data without customer/account/contract IDs
    IMPORTANT: Never returns null values - uses empty strings instead for Control4 compatibility
    
    Obtenir le statut simplifié des événements de pointe pour l'intégration Control4
    Retourne uniquement les données d'événement de pointe sans les IDs client/compte/contrat
    """
    if not _data_cache.initialized:
        logger.warning("⚠️ Cache not yet initialized / Cache pas encore initialisé")
        return {
            "ispeak": False,
            "start": "",
            "end": "",
            "state": "unknown"
        }
    
    # Return the first peak event if available, otherwise return default values
    # Retourner le premier événement de pointe si disponible, sinon retourner les valeurs par défaut
    if _data_cache.peak_events and len(_data_cache.peak_events) > 0:
        first_event = _data_cache.peak_events[0]
        # Convert None to empty string for Control4 compatibility
        start_val = first_event.get("start")
        end_val = first_event.get("end")
        return {
            "ispeak": first_event.get("ispeak", False),
            "start": start_val if start_val is not None else "",
            "end": end_val if end_val is not None else "",
            "state": first_event.get("state", "unknown")
        }
    
    # No peak events found / Aucun événement de pointe trouvé
    return {
        "ispeak": False,
        "start": "",
        "end": "",
        "state": "normal"
    }


@app.get("/api/control4/test")
async def get_control4_test():
    """
    Hardcoded test endpoint for Control4.
    Modify these values to test different scenarios.
    """
    # Example dates (ISO format)
    # start = datetime.now().isoformat()
    # end = (datetime.now() + timedelta(hours=3)).isoformat()
    
    # Example dates (ISO format) - hardcoded for testing
    start_str = "2025-12-05T17:00:00"
    end_str = "2025-12-05T21:00:00"
    
    return {
        "ispeak": True,
        "start": start_str,
        "end": end_str,
        "state": "normal"
    }


@app.get("/api/customers")
async def get_customers():
    """
    Get all customer information from cache
    Obtenir toutes les informations client depuis le cache
    """
    return _data_cache.customers


@app.get("/api/consumption/current")
async def get_current_consumption():
    """
    Get current period consumption data from cache
    Obtenir les données de consommation de la période actuelle depuis le cache
    """
    return _data_cache.consumption


@app.get("/api/balance")
async def get_balance():
    """
    Get account balance from cache
    Obtenir le solde du compte depuis le cache
    """
    return _data_cache.balances


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

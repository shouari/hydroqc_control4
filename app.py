"""
Hydro-Quebec API Integration for Control4
Exposes Hydro-Quebec data through REST API endpoints with focus on peak events.
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from hydroqc.webuser import WebUser
from hydroqc.customer import Customer

# Load environment variables
load_dotenv()

# Configure logging
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
HYDRO_CONTRACT = os.getenv("HYDRO_CONTRACT")

# Global client instance
_webuser_client: Optional[WebUser] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    yield
    # Shutdown
    global _webuser_client
    if _webuser_client:
        await _webuser_client.close_session()


# Create FastAPI app
app = FastAPI(
    title="Hydro-Quebec API",
    description="REST API for accessing Hydro-Quebec account data including peak events",
    version="1.0.0",
    lifespan=lifespan
)


async def get_webuser() -> WebUser:
    """Get or create authenticated WebUser instance"""
    global _webuser_client
    
    if not HYDRO_USERNAME or not HYDRO_PASSWORD:
        logger.error("Credentials missing in .env file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hydro-Quebec credentials not configured. Please set HYDRO_USERNAME and HYDRO_PASSWORD in .env file"
        )
    
    if _webuser_client is None:
        try:
            logger.info(f"Attempting login for user: {HYDRO_USERNAME}")
            _webuser_client = WebUser(HYDRO_USERNAME, HYDRO_PASSWORD, verify_ssl=True)
            await _webuser_client.login()
            logger.info("Login successful")
        except Exception as e:
            logger.error(f"Login failed: {str(e)}", exc_info=True)
            _webuser_client = None
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}"
            )
    
    return _webuser_client


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Hydro-Quebec Control4 Integration",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "configured": bool(HYDRO_USERNAME and HYDRO_PASSWORD)
    }


@app.get("/api/peak-events")
async def get_peak_events():
    """
    Get peak events information (winter credit events)
    Returns simplified structure: ispeak, start, end
    """
    try:
        webuser = await get_webuser()
        
        # Fetch customer info which contains peak events data
        customers = await webuser.fetch_customers_info()
        
        # Extract peak events from all customers
        peak_events_data = []
        
        for customer in customers:
            # Check each contract for peak events
            for contract in customer.contracts:
                # Check if contract has peak handler (Winter Credit / Rate D CPC)
                if hasattr(contract, 'peak_handler'):
                    handler = contract.peak_handler
                    
                    # Determine status
                    is_peak = handler.current_peak_is_critical or False
                    start_date = None
                    end_date = None
                    
                    if is_peak and handler.current_peak:
                        start_date = handler.current_peak.start_date
                        end_date = handler.current_peak.end_date
                    elif handler.next_critical_peak:
                        start_date = handler.next_critical_peak.start_date
                        end_date = handler.next_critical_peak.end_date
                        
                    peak_events_data.append({
                        "customer_id": customer.customer_id,
                        "contract_id": contract.contract_id,
                        "ispeak": is_peak,
                        "start": start_date.isoformat() if start_date else None,
                        "end": end_date.isoformat() if end_date else None,
                        "state": handler.current_state
                    })
        
        return {
            "success": True,
            "data": peak_events_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch peak events: {str(e)}"
        )


@app.get("/api/customers")
async def get_customers():
    """Get all customer information"""
    try:
        webuser = await get_webuser()
        customers = await webuser.fetch_customers_info()
        
        customers_data = []
        for customer in customers:
            customer_data = {
                "customer_id": customer.customer_id,
                "account_id": customer.account_id,
                "contracts": [
                    {
                        "contract_id": contract.contract_id,
                        "balance": contract.balance,
                    }
                    for contract in customer.contracts
                ]
            }
            customers_data.append(customer_data)
        
        return {
            "success": True,
            "data": customers_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch customers: {str(e)}"
        )


@app.get("/api/consumption/current")
async def get_current_consumption():
    """Get current period consumption data"""
    try:
        webuser = await get_webuser()
        customers = await webuser.fetch_customers_info()
        
        consumption_data = []
        for customer in customers:
            for contract in customer.contracts:
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
        
        return {
            "success": True,
            "data": consumption_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch consumption: {str(e)}"
        )


@app.get("/api/balance")
async def get_balance():
    """Get account balance for all contracts"""
    try:
        webuser = await get_webuser()
        customers = await webuser.fetch_customers_info()
        
        balances = []
        for customer in customers:
            for contract in customer.contracts:
                balances.append({
                    "contract_id": contract.contract_id,
                    "balance": contract.balance,
                    "customer_id": customer.customer_id
                })
        
        return {
            "success": True,
            "data": balances,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch balance: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

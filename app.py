"""
Hydro-Quebec API Integration for Control4
Exposes Hydro-Quebec data through REST API endpoints with focus on peak events.
CORRECTED VERSION - Properly uses HydroQC library based on official examples
"""
import os
import logging
from typing import Optional, Dict, Any, List
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

# Global client instance
_webuser_client: Optional[WebUser] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    logger.info("🚀 Starting Hydro-Quebec API")
    yield
    # Shutdown
    logger.info("🛑 Shutting down Hydro-Quebec API")
    global _webuser_client
    if _webuser_client:
        await _webuser_client.close_session()


# Create FastAPI app
app = FastAPI(
    title="Hydro-Quebec API",
    description="REST API for accessing Hydro-Quebec account data including peak events",
    version="1.0.2",
    lifespan=lifespan
)


async def get_webuser() -> WebUser:
    """Get or create authenticated WebUser instance"""
    global _webuser_client
    
    if not HYDRO_USERNAME or not HYDRO_PASSWORD:
        logger.error("❌ Credentials missing in .env file")
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
            logger.info("✅ Login successful")
            
            # CRITICAL: Must call get_info() to populate customers list
            await _webuser_client.get_info()
            logger.info(f"📋 Found {len(_webuser_client.customers)} customer(s)")
            
            # Fetch additional info for each customer
            for customer in _webuser_client.customers:
                await customer.get_info()
                logger.info(f"👤 Customer {customer.customer_id}: {len(customer.accounts)} account(s)")
            
        except Exception as e:
            logger.error(f"❌ Login failed: {str(e)}", exc_info=True)
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
        "version": "1.0.2",
        "timestamp": datetime.now().isoformat(),
        "configured": bool(HYDRO_USERNAME and HYDRO_PASSWORD)
    }


@app.get("/api/peak-events")
async def get_peak_events():
    """
    Get peak events information (winter credit events)
    Returns simplified structure: ispeak, start, end, state
    
    This is the PRIMARY endpoint for Control4 integration.
    Data structure follows: webuser.customers[].accounts[].contracts[]
    """
    try:
        webuser = await get_webuser()
        
        logger.debug("🔄 Processing customers and contracts...")
        
        # Extract peak events from all customers
        peak_events_data = []
        
        for customer in webuser.customers:
            logger.debug(f"👤 Processing customer: {customer.customer_id}")
            
            if not hasattr(customer, 'accounts') or not customer.accounts:
                logger.warning(f"⚠️ Customer {customer.customer_id} has no accounts")
                continue
            
            for account in customer.accounts:
                logger.debug(f"💼 Processing account: {account.account_id}")
                
                if not hasattr(account, 'contracts') or not account.contracts:
                    logger.warning(f"⚠️ Account {account.account_id} has no contracts")
                    continue
                
                for contract in account.contracts:
                    logger.debug(f"📃 Processing contract: {contract.contract_id}")
                    
                    # Check if contract has peak handler (Winter Credit / Rate D CPC)
                    if not hasattr(contract, 'peak_handler') or not contract.peak_handler:
                        logger.debug(f"ℹ️ Contract {contract.contract_id} has no peak_handler (not CPC-D)")
                        continue
                    
                    handler = contract.peak_handler
                    logger.debug(f"🔍 Peak handler found for contract {contract.contract_id}")
                    
                    # Refresh peak handler data
                    try:
                        await handler.refresh_data()
                        logger.debug(f"✅ Data refreshed for contract {contract.contract_id}")
                    except Exception as e:
                        logger.error(f"❌ Failed to refresh handler data: {e}")
                        # Continue with existing data
                    
                    # Determine status with robust error handling
                    is_peak = False
                    try:
                        is_peak = getattr(handler, 'current_peak_is_critical', None)
                        if is_peak is None:
                            is_peak = False
                    except Exception as e:
                        logger.error(f"Error getting current_peak_is_critical: {e}")
                        is_peak = False
                    
                    start_date = None
                    end_date = None
                    current_state = "unknown"
                    
                    try:
                        current_state = getattr(handler, 'current_state', 'unknown')
                    except Exception as e:
                        logger.error(f"Error getting current_state: {e}")
                    
                    # Get current_peak if available
                    try:
                        current_peak = getattr(handler, 'current_peak', None)
                        next_critical = getattr(handler, 'next_critical_peak', None)
                        
                        if is_peak and current_peak:
                            start_date = getattr(current_peak, 'start_date', None)
                            end_date = getattr(current_peak, 'end_date', None)
                            logger.debug(f"🔴 PEAK ACTIVE: {start_date} to {end_date}")
                        elif next_critical:
                            start_date = getattr(next_critical, 'start_date', None)
                            end_date = getattr(next_critical, 'end_date', None)
                            logger.debug(f"📅 Next critical peak: {start_date} to {end_date}")
                    except Exception as e:
                        logger.error(f"Error getting peak dates: {e}")
                    
                    event_data = {
                        "customer_id": customer.customer_id,
                        "account_id": account.account_id,
                        "contract_id": contract.contract_id,
                        "ispeak": is_peak,
                        "start": start_date.isoformat() if start_date else None,
                        "end": end_date.isoformat() if end_date else None,
                        "state": current_state
                    }
                    
                    peak_events_data.append(event_data)
                    logger.debug(f"✅ Added event data: {event_data}")
        
        logger.info(f"✅ Returning {len(peak_events_data)} peak event(s)")
        
        return {
            "success": True,
            "data": peak_events_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in peak-events endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch peak events: {str(e)}"
        )


@app.get("/api/customers")
async def get_customers():
    """Get all customer information"""
    try:
        webuser = await get_webuser()
        
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
        
        return {
            "success": True,
            "data": customers_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in customers endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch customers: {str(e)}"
        )


@app.get("/api/consumption/current")
async def get_current_consumption():
    """Get current period consumption data"""
    try:
        webuser = await get_webuser()
        
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
        
        return {
            "success": True,
            "data": consumption_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in consumption endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch consumption: {str(e)}"
        )


@app.get("/api/balance")
async def get_balance():
    """Get account balance for all contracts"""
    try:
        webuser = await get_webuser()
        
        balances = []
        for customer in webuser.customers:
            if not hasattr(customer, 'accounts') or not customer.accounts:
                continue
                
            for account in customer.accounts:
                if not hasattr(account, 'contracts') or not account.contracts:
                    continue
                    
                for contract in account.contracts:
                    balances.append({
                        "contract_id": contract.contract_id,
                        "balance": getattr(contract, 'balance', None),
                        "account_id": account.account_id,
                        "customer_id": customer.customer_id
                    })
        
        return {
            "success": True,
            "data": balances,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in balance endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch balance: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

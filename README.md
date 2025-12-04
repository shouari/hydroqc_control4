# Hydro-Quebec Control4 Integration

REST API for accessing Hydro-Quebec account data with a focus on **peak events** for Control4 home automation integration.

## Features

- ⚡ **Peak Events Endpoint** - Primary feature for monitoring Hydro-Quebec winter credit peak events
- 📊 Real-time consumption data
- 💰 Account balance information
- 🔄 Async API with automatic documentation
- 🔒 Secure credential management via environment variables

## Quick Start

### 1. Installation

```bash
# Clone or navigate to the project directory
cd d:\Codes\hydroqc_control4

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Edit the `.env` file and add your Hydro-Quebec credentials:

```env
HYDRO_USERNAME=your_email@example.com
HYDRO_PASSWORD=your_password
HYDRO_CONTRACT=your_contract_number
```

> **Note**: Get your credentials from [Hydro-Quebec Portal](https://www.hydroquebec.com/portail/)

### 3. Run the Server

```bash
# Start the API server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The server will start at `http://localhost:8000`

## API Endpoints

### 🏠 Health Check
```
GET /
```
Returns server status and configuration state.

**Example Response:**
```json
{
  "status": "running",
  "service": "Hydro-Quebec Control4 Integration",
  "version": "1.0.0",
  "timestamp": "2025-12-04T11:45:00",
  "configured": true
}
```

---

### ⚡ Peak Events (PRIMARY ENDPOINT)
```
GET /api/peak-events
```
Get winter credit peak events information - **the main endpoint for Control4 integration**.

**Example Response:**
```json
{
  "success": true,
  "data": [
    {
      "customer_id": "123456",
      "contract_id": "345678",
      "ispeak": true,
      "start": "2025-12-04T06:00:00-05:00",
      "end": "2025-12-04T09:00:00-05:00",
      "state": "critical_peak"
    }
  ],
  "timestamp": "2025-12-04T11:45:00"
}
```

**Fields:**
- `ispeak`: `true` if a peak event is currently active, `false` otherwise
- `start`: Start date-time of the current or next event (ISO 8601)
- `end`: End date-time of the current or next event (ISO 8601)
- `state`: Current state (e.g., "normal", "peak", "critical_peak")

---

### 👥 Customers
```
GET /api/customers
```
Get all customer and contract information.

---

### 📊 Current Consumption
```
GET /api/consumption/current
```
Get current billing period consumption data.

---

### 💰 Balance
```
GET /api/balance
```
Get account balance for all contracts.

---

## Interactive API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Use these interfaces to test all endpoints directly from your browser!

## Control4 Integration

### Recommended Setup

1. **Poll the Peak Events Endpoint**: Configure Control4 to poll `/api/peak-events` every 15-30 minutes
2. **Monitor Winter Credit Status**: Check `winter_credit_enabled` field
3. **Track Peak Events**: Use the `peak_events` array to trigger automations
4. **Current Consumption**: Use `/api/consumption/current` for real-time usage monitoring

### Example Control4 Driver Configuration

```lua
-- Example polling configuration
local API_BASE_URL = "http://your-server-ip:8000"
local POLL_INTERVAL = 900  -- 15 minutes in seconds

function CheckPeakEvents()
    local url = API_BASE_URL .. "/api/peak-events"
    -- Make HTTP GET request and process response
    -- Trigger automation based on peak event status
end
```

## Testing

### Using curl

```bash
# Health check
curl http://localhost:8000/

# Get peak events
curl http://localhost:8000/api/peak-events

# Get current consumption
curl http://localhost:8000/api/consumption/current

# Get balance
curl http://localhost:8000/api/balance
```

### Using Python

```python
import requests

response = requests.get("http://localhost:8000/api/peak-events")
data = response.json()

if data["success"]:
    for customer in data["data"]:
        for contract in customer["contracts"]:
            if contract["winter_credit_enabled"]:
                print(f"Winter credit active for contract {contract['contract_id']}")
```

## Project Structure

```
hydroqc_control4/
├── app.py              # Main FastAPI application
├── requirements.txt    # Python dependencies
├── .env               # Configuration (credentials)
└── README.md          # This file
```

## Dependencies

- **FastAPI** - Modern web framework for building APIs
- **Uvicorn** - ASGI server for running FastAPI
- **Hydro-Quebec-API-Wrapper** - Official wrapper for Hydro-Quebec API
- **python-dotenv** - Environment variable management

## Security Notes

- ⚠️ Never commit your `.env` file to version control
- 🔒 Keep your Hydro-Quebec credentials secure
- 🌐 Consider using HTTPS in production
- 🔐 Add authentication if exposing to the internet

## Troubleshooting

### Server won't start
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check that port 8000 is not in use
- Ensure Python 3.10+ is installed

### Authentication errors
- Verify credentials in `.env` file are correct
- Check that you can log in to the Hydro-Quebec portal manually
- Ensure no special characters in password are causing issues

### No data returned
- Confirm your Hydro-Quebec account has active contracts
- Check that winter credit is enabled on your account
- Verify you're enrolled in peak events program

## Support

For issues with:
- **This API wrapper**: Check the [Hydro-Quebec-API-Wrapper documentation](https://pypi.org/project/Hydro-Quebec-API-Wrapper/)
- **FastAPI**: See [FastAPI documentation](https://fastapi.tiangolo.com/)
- **Control4 integration**: Consult your Control4 dealer or developer

## License

This project uses the Hydro-Quebec-API-Wrapper library. Please refer to its license for usage terms.

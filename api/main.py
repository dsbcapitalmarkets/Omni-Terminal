
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from core.db import load
from config import DATA_FILES


app = FastAPI(title="Omni-Terminal API")


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Omni-Terminal API is running",
    }


# ============================================================
# GENERIC MODULE LOADER
# ============================================================

def load_module(module_name: str):
    """
    Load a module's JSON using the existing core.db.load()
    and DATA_FILES configuration.
    """

    try:
        filename = DATA_FILES[module_name]
        data = load(filename)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unable to load {filename}",
            )

        return data

    except KeyError:
        raise HTTPException(
            status_code=500,
            detail=f"'{module_name}' not found in DATA_FILES",
        )

    except HTTPException:
        raise

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
        }


# ============================================================
# STOCK SCREENER
# ============================================================

@app.get("/api/stock-screener")
def stock_screener(
    exchange: str = Query(
        default="BOTH",
        description="Exchange filter: NSE, BSE or BOTH",
    )
):
    """
    Return screener results filtered by exchange.

    Examples:
        /api/stock-screener?exchange=NSE
        /api/stock-screener?exchange=BSE
        /api/stock-screener?exchange=BOTH

    Filtering is performed on existing screener results.
    No additional market data download is triggered.
    """

    exchange = exchange.strip().upper()

    if exchange not in ("NSE", "BSE", "BOTH"):
        raise HTTPException(
            status_code=400,
            detail="Invalid exchange. Choose NSE, BSE or BOTH.",
        )

    data = load_module("Stock Screener")

    if not isinstance(data, dict):
        return data

    if data.get("status") != "ok":
        return data

    stocks = data.get("stocks", [])

    if not isinstance(stocks, list):
        raise HTTPException(
            status_code=500,
            detail="Invalid stocks data in screener.json",
        )

    # Exchange filtering
    if exchange == "BOTH":
        filtered_stocks = stocks
    else:
        filtered_stocks = [
            stock
            for stock in stocks
            if stock.get("exchange", "").upper() == exchange
        ]

    # Preserve original screener metadata
    result = data.copy()

    result.update({
        "exchange_filter": exchange,
        "stocks": filtered_stocks,
        "passed_count": len(filtered_stocks),
        "filtered_count": len(filtered_stocks),
        "total_signals": len(stocks),
    })

    return result


# ============================================================
# GOLD / SILVER RATIO
# ============================================================

@app.get("/api/gold-silver")
def gold_silver():
    return load_module("Gold Silver Ratio")


# ============================================================
# SECTOR ROTATION
# ============================================================

@app.get("/api/sector-rotation")
def sector_rotation():
    return load_module("Sector Rotation")


# ============================================================
# SMART MONEY FLOW
# ============================================================

@app.get("/api/smart-money")
def smart_money():
    return load_module("Smart Money Flow")


# ============================================================
# MARKET BREADTH
# ============================================================

@app.get("/api/market-breadth")
def market_breadth():
    return load_module("Market Breadth")


# ============================================================
# EARNINGS TRACKER
# ============================================================

@app.get("/api/earnings")
def earnings():
    return load_module("Earnings Tracker")


# ============================================================
# PORTFOLIO REVIEW
# ============================================================

@app.get("/api/portfolio-review")
def portfolio_review():
    return load_module("Portfolio Review")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "modules": list(DATA_FILES.keys()),
    }

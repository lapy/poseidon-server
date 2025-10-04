"""
Shark Foraging Hotspot Prediction Server
Main FastAPI application entry point
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from datetime import datetime, date
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from api.routes import hotspots
from models.hsi_model import HSIModel
from data.nasa_data import NASADataManager

app = FastAPI(
    title="Shark Foraging Hotspot Prediction API",
    description="API for predicting global shark foraging hotspots using NASA satellite data",
    version="1.0.0"
)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(hotspots.router, prefix="/api", tags=["hotspots"])

@app.get("/")
async def root():
    """Root endpoint - serves the frontend"""
    from fastapi.responses import FileResponse
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Shark Foraging Hotspot Prediction Server - Frontend not found"}

# Serve static files for frontend (CSS, JS, etc.)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )

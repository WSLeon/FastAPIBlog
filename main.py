"""
PhD Survival Station (博士生精神状态监测站)
Root Entrypoint
"""
from phd_station.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

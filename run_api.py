import os

import uvicorn
from dotenv import load_dotenv
from api.main import app

load_dotenv()

host = os.getenv("API_HOST")
port = os.getenv("API_PORT")

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
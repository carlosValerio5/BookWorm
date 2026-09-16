from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import base64
import os
from datetime import datetime
import random

app = FastAPI(title="BookWorm Mobile API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ruta real de dataset de fotos y etiquetas
DATASET_PHOTOS_DIR = Path("./dataset/photos")
DATASET_LABELS_DIR = Path("./dataset/labels")

# carpetas existan en la computadora
DATASET_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
DATASET_LABELS_DIR.mkdir(parents=True, exist_ok=True)

class ScanRequest(BaseModel):
    image: str

@app.post("/api/scan")
async def scan_book(payload: ScanRequest):
    try:
        header, encoded = payload.image.split(",", 1)
        image_data = base64.b64decode(encoded)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scan_{timestamp}.jpg"
        file_path = DATASET_PHOTOS_DIR / filename

        with open(file_path, "wb") as f:
            f.write(image_data)

        print(f"¡Foto guardada exitosamente en el dataset!: {file_path}")

        libro_detectado = {
            "title": "Drácula",
            "author": "Bram Stoker",
            "isbn": "978-84-206-3397-8",
            "coverImage": "https://images.cdn3.buscalibre.com/fit-in/360x360/2c/a8/2ca8067278e80ee8f95d91d9a7fce8fc.jpg"
        }

        return libro_detectado


    except Exception as e:
        print(f"Error procesando la imagen en el dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
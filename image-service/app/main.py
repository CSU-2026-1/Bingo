import logging
import os
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pipe = None

app = FastAPI(title="image-service")


class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    url: str


@app.on_event("startup")
async def load_model():
    global pipe
    from diffusers import StableDiffusionPipeline
    import torch
    
    from app.core.config import settings
    
    os.makedirs(settings.images_dir, exist_ok=True)
    
    logger.info("Загружаем модель %s...", settings.hf_model)
    pipe = StableDiffusionPipeline.from_pretrained(
        settings.hf_model,
        torch_dtype=torch.float32,
    )
    pipe = pipe.to("cpu")
    pipe.set_progress_bar_config(disable=True)
    logger.info("Модель загружена")


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": pipe is not None}


@app.post("/generate", response_model=GenerateResponse)
async def generate_image(payload: GenerateRequest):
    if pipe is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")
    
    from app.core.config import settings
    
    logger.info("Генерируем изображение для промпта: %s", payload.prompt[:100])
    
    try:
        result = pipe(
            payload.prompt,
            width=settings.image_size,
            height=settings.image_size,
            num_inference_steps=settings.num_inference_steps,
            guidance_scale=7.0,
        )
        image = result.images[0]
        
        filename = f"{uuid4()}.png"
        filepath = os.path.join(settings.images_dir, filename)
        image.save(filepath)
        
        logger.info("Изображение сохранено: %s", filename)
        return GenerateResponse(url=f"/images/{filename}")
    except Exception as exc:
        logger.error("Ошибка генерации: %s", exc)
        raise HTTPException(status_code=500, detail="Ошибка генерации изображения")


@app.get("/images/{filename}")
async def get_image(filename: str):
    from app.core.config import settings
    
    filepath = os.path.join(settings.images_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Изображение не найдено")
    return FileResponse(filepath, media_type="image/png")

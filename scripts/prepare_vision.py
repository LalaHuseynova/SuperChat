"""Download the local visual model once, ahead of an offline demo."""

from transformers import CLIPModel, CLIPProcessor
from dotenv import load_dotenv
import os

load_dotenv()
model = os.getenv("VISION_MODEL", "openai/clip-vit-base-patch32")
CLIPProcessor.from_pretrained(model)
CLIPModel.from_pretrained(model, use_safetensors=True)
print("Visual search model is cached. Set VISION_OFFLINE=true for offline use.")

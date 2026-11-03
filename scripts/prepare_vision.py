"""Download the local visual model once, ahead of an offline demo."""

from transformers import CLIPModel, CLIPProcessor
from dotenv import load_dotenv
import os

load_dotenv()
model = os.getenv("VISION_MODEL", "openai/clip-vit-base-patch32")
CLIPProcessor.from_pretrained(model)
CLIPModel.from_pretrained(model, use_safetensors=True)
print("Visual search model is cached. Set VISION_OFFLINE=true for offline use.")
if '--catalogue' in __import__('sys').argv:
    from superchat.config import CATALOGUE_DB, REAL_DATA_DIR
    from superchat.database import CatalogueDatabase
    from superchat.ai import AIProvider
    from superchat.vision import VisualSearch
    database = CatalogueDatabase(CATALOGUE_DB, REAL_DATA_DIR)
    database.seed()
    provider = AIProvider()
    provider.key = ''
    vectors = VisualSearch(provider).index_catalogue(database)
    print(f'Indexed {len(vectors)} product images for similarity search.')

import glob
import json
import os
import shutil
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from langchain_chroma import Chroma
from langchain_core.documents import Document
from sentence_transformers import SentenceTransformer
from transformers import CLIPModel, CLIPProcessor
from downloader import extract_dir

with open("structured_restaurant_data.json", "r") as f:
    restaurants = json.load(f)  #restaurant_json_data

with open("augmented_food_recipe.json", "r") as f:
    recipes = json.load(f)  #food_recipe json data with image captions

print(f"✅ Loaded restaurants: {len(restaurants)}")
print(f"✅ Loaded recipes:     {len(recipes)}")

# ================================
# Initialize embedding models
# ================================

# ---- Text embedding model (384-d) ----
text_model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_texts(texts, batch_size=64):  #convert text to vector embeddings
    return text_model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,  # cosine-ready
    ).astype(np.float32)

print("✅ Text embedder ready")


# ---- Image embedding model (512-d) ----
device = "cpu"
clip_name = "openai/clip-vit-base-patch32"
clip_model = CLIPModel.from_pretrained(clip_name).to(device)
clip_processor = CLIPProcessor.from_pretrained(clip_name, use_fast=True)
clip_model.eval()

@torch.no_grad()
def embed_images(paths, batch_size=16):  #vector embeddings for images
    vecs = [] #list of vectors(floats)
    for i in range(0, len(paths), batch_size): #loop from 0 to len(paths) and increment i by batch_size
        batch = paths[i:i+batch_size]
        imgs = [Image.open(p).convert("RGB") for p in batch]
        inputs = clip_processor(images=imgs, return_tensors="pt").to(device)
        feats = clip_model.get_image_features(**inputs)          # (B,512)
        feats = feats / feats.norm(dim=-1, keepdim=True)         # cosine-ready
        vecs.append(feats.cpu().numpy().astype(np.float32))
    return np.vstack(vecs)

print("✅ Image embedder ready")


# ================================
# Build article and image documents
# ================================

# -------- articles --------
#Convert Structured Restaurant and Recipe Data into Document Objects and store them in list
article_docs = []

for i, r in enumerate(restaurants):
    name = str(r.get("name", "")).strip()
    if not name:
        continue

    text = (
    f"Restaurant: {name}\n"
    f"Cuisine: {r.get('food_style','')}\n"
    f"Location: {r.get('location','')}"
    ) #formatted string: these are text content of Document object, it includes each restaurant's name,food style and location

    # GUARANTEED UNIQUE
    doc_id = f"rest_{i}"

    article_docs.append(
        Document(  #append each restaurant as Document object
            page_content=text.strip(),
            metadata={
                "doc_id": doc_id,
                "cuisine": r.get("food_style"),
                "location": r.get("location"),
                "source": "restaurant",
            },  #other details of restaurant like cuisine, food style become metadata
        )
    )

print("✅ article docs:", len(article_docs))


# -------- images --------
#now convert images from extracted recipe images, into Document objects and store them in list


image_docs = []
#logic for getting image paths
nested_image_folder = os.path.join(extract_dir, "synthetic_recipe_images")

if not os.path.exists(nested_image_folder):
    raise FileNotFoundError(f"Could not find image folder: {nested_image_folder}")

valid_images = sorted(
    f for f in os.listdir(nested_image_folder)
    if f.lower().endswith((".png", ".jpg", ".jpeg"))
)

image_paths = [
    os.path.normpath(os.path.abspath(os.path.join(nested_image_folder, image_name)))
    for image_name in valid_images
]

if len(image_paths) < len(recipes):
    raise ValueError("Not enough recipe images for recipe data.")

for i, (p, rec) in enumerate(zip(image_paths, recipes)): #for each picture in image_paths and each recipe in recipes
    doc_id = f"img_{i}" #index counter is doc id

    image_docs.append(
        Document(
            # keeps retrieval results readable
            page_content=rec.get("name", f"recipe image {i}"),
            metadata={
                "doc_id": doc_id,
                "image_path": p,
                "source": "recipe_image",
                "recipe_id": rec.get("id"),
                "cuisine": rec.get("cuisine"),
            },
        )
    )

print("✅ image docs:", len(image_docs)) #we have list of Document object(which consist of recipes structured data and their images)

# ================================
# Construct and Persist Multimodal Vector Indexes
# ================================

DB_DIR = str((Path.home() / "chroma_multimodal").resolve())

if os.path.isdir(DB_DIR):
    shutil.rmtree(DB_DIR)  # Reset vector DB (important for reruns)

# ----- article DB -----
A = embed_texts([d.page_content for d in article_docs]) #for each Document object in article docs,embed only its page_content i.e the text

article_db = Chroma(  #create new collection with name and directory where it persists
    collection_name="restaurant_articles",
    persist_directory=DB_DIR,
)

article_db._collection.upsert( #each element in db collection has an id, we use the id we created in Document objects' metadata
    ids=[d.metadata["doc_id"] for d in article_docs],
    embeddings=A.tolist(), #store the embeddings as a list of floats
    documents=[d.page_content for d in article_docs], #store the original, umembedded text as well
    metadatas=[d.metadata for d in article_docs], #store the metadata too
)

print("✅ Article DB ready")


# ----- image DB -----
V = embed_images([d.metadata["image_path"] for d in image_docs])

image_db = Chroma(
    collection_name="food_images",
    persist_directory=DB_DIR,
)

image_db._collection.upsert(
    ids=[d.metadata["doc_id"] for d in image_docs],
    embeddings=V.tolist(),
    documents=[d.page_content for d in image_docs],
    metadatas=[d.metadata for d in image_docs],
)

print("✅ Image DB ready")
print("🎉 Multimodal Vector Index Construction COMPLETE")

#DONE WITH STORING EMBEDDED AND UN-EMBEDDED DOCUMENTS IN CHROMA VECTOR DB
#next step is similarity retrieval
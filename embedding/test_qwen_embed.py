from sentence_transformers import SentenceTransformer
import time

print("Loading model...")
start = time.time()

model = SentenceTransformer(
    "Qwen/Qwen3-Embedding-0.6B",
    model_kwargs={"attn_implementation": "eager"},
    tokenizer_kwargs={"padding_side": "left"},
)

print(f"Model loaded in {time.time() - start:.2f} sec")

# Test embeddings
texts = [
    "Hello world.",
    "This is a test of the Qwen3 embedding model."
]

print("Generating embeddings...")
start = time.time()
emb = model.encode(texts, normalize_embeddings=True)
elapsed = time.time() - start

print(f"Generated {len(emb)} embeddings in {elapsed:.2f} sec")
print("Embedding shape:", emb.shape)

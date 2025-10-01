from sentence_transformers import SentenceTransformer
import numpy as np
import pickle

# Load the model
model = SentenceTransformer("Qwen/Qwen3-Embedding-8B")

# Your text document(s)
documents = [
    "Your first document text here...",
    "Your second document text here...",
    # Add more documents as needed
]

# Generate embeddings
embeddings = model.encode(documents)

# Save embeddings to file
np.save('document_embeddings.npy', embeddings)

# Or save as pickle for more flexibility
with open('document_embeddings.pkl', 'wb') as f:
    pickle.dump({
        'embeddings': embeddings,
        'documents': documents
    }, f)

print(f"Generated embeddings shape: {embeddings.shape}")
# Output will be (num_documents, 4096) - 4096 is the embedding dimension

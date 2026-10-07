from functools import lru_cache
from app.config import settings

@lru_cache
def model():
    from sentence_transformers import SentenceTransformer
    c=settings()
    return SentenceTransformer(c.embedding_model, revision=c.embedding_revision)

def embed(texts):
    return model().encode(texts,normalize_embeddings=True,show_progress_bar=False,batch_size=32).tolist()

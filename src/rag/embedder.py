from functools import lru_cache
from sentence_transformers import SentenceTransformer
from src.config.settings import settings


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Load embedding model sekali dan cache — model ini cukup besar (~90MB),
    tidak efisien jika diload ulang setiap request.
    """
    return SentenceTransformer(settings.embedding_model)


def embed_text(text: str) -> list[float]:
    """Ubah satu string teks menjadi vector 384 dimensi."""
    model = get_embedding_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Ubah list teks menjadi list vector — lebih efisien dari embed satu per satu."""
    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [v.tolist() for v in vectors]

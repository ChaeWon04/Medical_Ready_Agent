import chromadb
from sentence_transformers import SentenceTransformer
from config import CHROMA_DIR, EMBEDDING_MODEL, TOP_K

_client = None
_collection = None
_embedder = None


def _init():
    global _client, _collection, _embedder
    if _client is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _client.get_or_create_collection("pmc_patients")
        _embedder = SentenceTransformer(EMBEDDING_MODEL)


def retrieve(query: str) -> list[str]:
    _init()
    embedding = _embedder.encode([query]).tolist()
    results = _collection.query(query_embeddings=embedding, n_results=TOP_K)
    return results["documents"][0] if results["documents"] else []

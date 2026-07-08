import zipfile
import chromadb
from sentence_transformers import SentenceTransformer
from config import CHROMA_DIR, EMBED_MODEL_ID, CHROMA_COLLECTION, RAG_TOP_K

_VECTORDB_ZIP = CHROMA_DIR.parent / "pmc_vectordb.zip"


def _ensure_vectordb_extracted():
    if CHROMA_DIR.exists() and any(CHROMA_DIR.iterdir()):
        return
    if not _VECTORDB_ZIP.exists():
        return
    print(f"[Retriever] {_VECTORDB_ZIP.name} 압축 해제 중...")
    with zipfile.ZipFile(_VECTORDB_ZIP) as zf:
        zf.extractall(CHROMA_DIR.parent)


class PMCRetriever:
    """Agent 2 Critic이 의학적 팩트체크에 사용하는 PMC 검색기"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        print(f"[Retriever] ChromaDB 연결 중...")
        _ensure_vectordb_extracted()
        self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._collection = self._client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        self._embedder = SentenceTransformer(EMBED_MODEL_ID)
        self._initialized = True
        print(f"[Retriever] 준비 완료 ({self._collection.count()}개 청크)")

    def retrieve(self, query: str, top_k: int = RAG_TOP_K) -> list[str]:
        """쿼리와 가장 관련 높은 PMC 패시지 반환"""
        return [text for text, _ in self.retrieve_with_scores(query, top_k)]

    def retrieve_with_scores(self, query: str, top_k: int = RAG_TOP_K) -> list[tuple[str, float]]:
        """쿼리와 가장 관련 높은 PMC 패시지 + 유사도 점수(코사인, 1에 가까울수록 유사) 반환"""
        if self._collection.count() == 0:
            return []

        embedding = self._embedder.encode(query).tolist()
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, self._collection.count()),
        )
        docs = results["documents"][0]
        dists = results["distances"][0]
        return [(doc, round(1 - dist, 3)) for doc, dist in zip(docs, dists)]

    def format_context(self, query: str) -> str:
        """Critic 프롬프트에 바로 삽입할 수 있는 컨텍스트 문자열 생성"""
        passages = self.retrieve(query)
        if not passages:
            return "No reference context available."
        return "\n\n".join(
            f"[Reference {i+1}]\n{p}" for i, p in enumerate(passages)
        )


retriever = PMCRetriever()

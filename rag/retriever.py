import chromadb
from sentence_transformers import SentenceTransformer
from config import CHROMA_DIR, EMBED_MODEL_ID, CHROMA_COLLECTION, RAG_TOP_K


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
        if self._collection.count() == 0:
            return []

        embedding = self._embedder.encode(query).tolist()
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, self._collection.count()),
        )
        return results["documents"][0]  # 텍스트 리스트

    def format_context(self, query: str) -> str:
        """Critic 프롬프트에 바로 삽입할 수 있는 컨텍스트 문자열 생성"""
        passages = self.retrieve(query)
        if not passages:
            return "No reference context available."
        return "\n\n".join(
            f"[Reference {i+1}]\n{p}" for i, p in enumerate(passages)
        )


retriever = PMCRetriever()

"""
PMC 논문 텍스트 → ChromaDB 구축 스크립트 (1회 실행)
사용법: python rag/build_vectordb.py
"""
import xml.etree.ElementTree as ET
import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path
from config import PMC_DIR, CHROMA_DIR, EMBED_MODEL_ID, CHROMA_COLLECTION

CHUNK_SIZE = 400
CHUNK_OVERLAP = 50


def load_pmc_texts(pmc_dir: Path) -> list[dict]:
    docs = []
    files = list(pmc_dir.glob("*.txt")) + list(pmc_dir.glob("*.xml"))
    if not files:
        print(f"[RAG] {pmc_dir}에 파일 없음. data/pmc/에 PMC 파일을 넣어주세요.")
        return docs
    for path in files:
        text = _read_file(path)
        if text:
            docs.append({"source": path.name, "text": text})
    print(f"[RAG] {len(docs)}개 PMC 문서 로드 완료")
    return docs


def _read_file(path: Path) -> str:
    if path.suffix == ".xml":
        return _parse_xml(path)
    return path.read_text(encoding="utf-8", errors="ignore")


def _parse_xml(path: Path) -> str:
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        texts = []
        for elem in root.iter():
            if elem.tag in {"p", "title", "abstract"} and elem.text:
                texts.append(elem.text.strip())
        return " ".join(texts)
    except ET.ParseError:
        return ""


def chunk_text(text: str, source: str) -> list[dict]:
    words = text.split()
    chunks = []
    idx = 0
    chunk_id = 0
    while idx < len(words):
        chunk_words = words[idx: idx + CHUNK_SIZE]
        chunks.append({
            "id": f"{source}_{chunk_id}",
            "text": " ".join(chunk_words),
            "source": source,
        })
        idx += CHUNK_SIZE - CHUNK_OVERLAP
        chunk_id += 1
    return chunks


def build(force: bool = False):
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    existing = [c.name for c in client.list_collections()]

    if CHROMA_COLLECTION in existing and not force:
        count = client.get_collection(CHROMA_COLLECTION).count()
        print(f"[RAG] ChromaDB 이미 존재 ({count}개 청크). force=True로 재구축 가능.")
        return

    if CHROMA_COLLECTION in existing:
        client.delete_collection(CHROMA_COLLECTION)

    collection = client.create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    docs = load_pmc_texts(PMC_DIR)
    if not docs:
        return

    print(f"[RAG] 임베딩 모델 로딩: {EMBED_MODEL_ID}")
    embedder = SentenceTransformer(EMBED_MODEL_ID)

    all_chunks = []
    for doc in docs:
        all_chunks.extend(chunk_text(doc["text"], doc["source"]))

    print(f"[RAG] 총 {len(all_chunks)}개 청크 임베딩 중...")
    batch_size = 64
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i: i + batch_size]
        texts = [c["text"] for c in batch]
        embeddings = embedder.encode(texts, show_progress_bar=False).tolist()
        collection.add(
            ids=[c["id"] for c in batch],
            documents=texts,
            embeddings=embeddings,
            metadatas=[{"source": c["source"]} for c in batch],
        )

    print(f"[RAG] ChromaDB 구축 완료: {collection.count()}개 청크 저장")


if __name__ == "__main__":
    build()

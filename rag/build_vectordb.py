import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path
from config import PMC_DIR, CHROMA_DIR, EMBEDDING_MODEL


def build_vectordb():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection("pmc_patients")

    embedder = SentenceTransformer(EMBEDDING_MODEL)

    docs, ids = [], []
    for i, fpath in enumerate(Path(PMC_DIR).glob("*.txt")):
        text = fpath.read_text(encoding="utf-8")
        docs.append(text)
        ids.append(f"pmc_{i}")

    if not docs:
        print("PMC 문서 없음. data/pmc/ 에 .txt 파일을 추가하세요.")
        return

    embeddings = embedder.encode(docs).tolist()
    collection.add(documents=docs, embeddings=embeddings, ids=ids)
    print(f"ChromaDB 구축 완료: {len(docs)}개 문서")


if __name__ == "__main__":
    build_vectordb()

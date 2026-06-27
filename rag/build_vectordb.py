"""
build_vectorDB.py
PMC XML 논문을 파싱, 청킹, 배치 임베딩하여 ChromaDB에 저장하는 RAG 파이프라인
pmc.py가 추출해둔 ./pmc_xml_selected 폴더의 XML(.xml/.nxml, 하위 폴더 포함)을 읽어들입니다.
"""

from pathlib import Path
from typing import List, Dict, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from lxml import etree

# ---------- 경로 설정 ----------
BASE_DIR = Path(__file__).parent
XML_DIR = BASE_DIR / "pmc_xml_selected"
CHROMA_DIR = BASE_DIR / "pmc_vectordb"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# PMC 논문은 영어 원문이므로 생의학 도메인 특화 영어 임베딩을 기본으로 사용
EMBEDDING_MODEL = "pritamdeka/S-PubMedBert-MS-MARCO"


# ---------- JATS XML 파싱 ----------
def parse_jats(xml_bytes: bytes) -> Dict:
    """PMC JATS XML에서 제목/초록/섹션/메타데이터를 추출"""
    root = etree.fromstring(xml_bytes)

    def get_text(xpath_expr: str) -> str:
        nodes = root.xpath(xpath_expr)
        return " ".join("".join(n.itertext()).strip() for n in nodes)

    title = get_text(".//article-title")
    abstract = get_text(".//abstract")

    # 'pmcid'와 'pmc' 속성값 둘 다 시도 (신형/구형 JATS 포맷 차이 대응)
    pmcid_raw = (
        root.xpath(".//article-id[@pub-id-type='pmcid']/text()")
        or root.xpath(".//article-id[@pub-id-type='pmc']/text()")
    )
    pmcid = None
    if pmcid_raw:
        raw = pmcid_raw[0].strip()
        pmcid = raw if raw.upper().startswith("PMC") else f"PMC{raw}"

    doi = root.xpath(".//article-id[@pub-id-type='doi']/text()")
    year = root.xpath(".//pub-date//year/text()")

    sections = []
    for sec in root.xpath(".//body//sec"):
        title_node = sec.find("title")
        sec_title = title_node.text if title_node is not None else ""
        paragraphs = ["".join(p.itertext()).strip() for p in sec.findall("p")]
        sec_text = " ".join(p for p in paragraphs if p)
        if sec_text:
            sections.append({"title": sec_title, "text": sec_text})

    return {
        "pmcid": pmcid,
        "doi": doi[0] if doi else None,
        "title": title,
        "abstract": abstract,
        "year": int(year[0]) if year else None,
        "sections": sections,
    }


# ---------- Vector Store ----------
class PMCVectorStore:
    """PMC 논문 Vector Store - ChromaDB 기반"""

    def __init__(self, collection_name: str = "pmc_corpus"):
        self.collection_name = collection_name

        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )

        print(f"[VectorStore] Loading embedding model: {EMBEDDING_MODEL}")
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        print(f"[VectorStore] Collection '{self.collection_name}' ready. "
              f"Current docs: {self.collection.count()}")

    def add_papers_from_dir(self, xml_dir: Path = XML_DIR, chunk_size: int = 300, overlap: int = 50):
        """XML 폴더 전체를 파싱 → 섹션 단위 청킹 → 배치 임베딩 → 저장"""
        xml_files = list(xml_dir.rglob("*.xml")) + list(xml_dir.rglob("*.nxml"))
        if not xml_files:
            print(f"[VectorStore] No XML files found in {xml_dir}")
            return

        print(f"[VectorStore] 총 {len(xml_files)}개 파일 발견. 파싱 시작...")

        # ---------- 1단계: 파싱 + 청킹 ----------
        pending_documents, pending_metadatas, pending_ids = [], [], []
        parse_failed = []

        for idx, xml_path in enumerate(xml_files, 1):
            try:
                with open(xml_path, "rb") as f:
                    parsed = parse_jats(f.read())
            except Exception:
                parse_failed.append(xml_path.name)
                continue

            if not parsed["pmcid"]:
                parsed["pmcid"] = xml_path.stem

            if not parsed["abstract"] and not parsed["sections"]:
                parse_failed.append(xml_path.name)
                continue

            for chunk_text, section_name, chunk_idx in self._chunk_paper(parsed, chunk_size, overlap):
                chunk_id = f"{parsed['pmcid']}_chunk_{chunk_idx}"

                existing = self.collection.get(ids=[chunk_id])
                if existing["ids"]:
                    continue

                pending_documents.append(chunk_text)
                pending_metadatas.append({
                    "pmcid": parsed["pmcid"],
                    "doi": parsed["doi"] or "",
                    "title": parsed["title"],
                    "year": parsed["year"] or 0,
                    "section": section_name,
                    "chunk_index": chunk_idx,
                    "chunk_id": chunk_id,
                })
                pending_ids.append(chunk_id)

            if idx % 10 == 0 or idx == len(xml_files):
                print(f"  [1/3 파싱] {idx}/{len(xml_files)}편 처리, 현재까지 청크 {len(pending_documents)}개")

        if parse_failed:
            preview = parse_failed[:5]
            print(f"[VectorStore] 파싱 실패 {len(parse_failed)}건: {preview}"
                  f"{' ...' if len(parse_failed) > 5 else ''}")

        if not pending_documents:
            print("[VectorStore] 새로 추가할 청크가 없습니다 (이미 전부 인덱싱됨, 또는 파싱 실패).")
            return

        print(f"[VectorStore] 파싱 완료. 총 청크 수: {len(pending_documents)}")

        # ---------- 2단계: 배치 임베딩 ----------
        print(f"[VectorStore] [2/3 임베딩] 시작 (batch_size=32)...")
        all_embeddings = self.embedder.encode(
            pending_documents,
            batch_size=32,
            show_progress_bar=True,
        ).tolist()
        print(f"[VectorStore] 임베딩 완료.")

        # ---------- 3단계: ChromaDB 배치 적재 ----------
        batch_size = 100
        total = len(pending_documents)
        for i in range(0, total, batch_size):
            self.collection.add(
                documents=pending_documents[i:i + batch_size],
                embeddings=all_embeddings[i:i + batch_size],
                metadatas=pending_metadatas[i:i + batch_size],
                ids=pending_ids[i:i + batch_size],
            )
            done = min(i + batch_size, total)
            print(f"  [3/3 적재] {done}/{total} 청크 저장 완료")

        n_papers = len(xml_files) - len(parse_failed)
        print(f"[VectorStore] 최종 완료: {total}개 청크, {n_papers}편 논문 인덱싱됨.")

    def search(
        self,
        query: str,
        n_results: int = 5,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
    ) -> List[Dict]:
        """쿼리와 유사한 논문 청크 검색"""
        if self.collection.count() == 0:
            print("[VectorStore] 컬렉션이 비어있습니다. add_papers_from_dir()를 먼저 실행하세요.")
            return []

        query_embedding = self.embedder.encode(query).tolist()

        where = {}
        if year_min or year_max:
            conditions = []
            if year_min:
                conditions.append({"year": {"$gte": year_min}})
            if year_max:
                conditions.append({"year": {"$lte": year_max}})
            where = conditions[0] if len(conditions) == 1 else {"$and": conditions}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self.collection.count()),
            where=where if where else None,
            include=["documents", "metadatas", "distances"],
        )

        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append({
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "similarity": 1 - results["distances"][0][i],
            })
        return formatted

    def get_relevant_context(self, query: str, n_results: int = 3) -> str:
        """RAG용 컨텍스트 문자열 반환"""
        results = self.search(query, n_results=n_results)
        if not results:
            return "관련 논문을 찾을 수 없습니다."

        context_parts = []
        for i, r in enumerate(results, 1):
            meta = r["metadata"]
            context_parts.append(
                f"[논문 {i}] {meta['title']} ({meta['year']}) - [{meta['section']}] "
                f"- 유사도: {r['similarity']:.3f}\n{r['content']}"
            )
        return "\n\n".join(context_parts)

    def get_stats(self) -> Dict:
        """Vector Store 통계"""
        count = self.collection.count()
        return {
            "collection": self.collection_name,
            "total_chunks": count,
            "embedding_model": EMBEDDING_MODEL,
        }

    def _chunk_paper(self, parsed: Dict, chunk_size: int, overlap: int):
        """초록은 통째로 1청크, 본문은 섹션 단위로 나눈 뒤 단어 수 기준 재분할"""
        idx = 0

        if parsed["abstract"]:
            yield parsed["abstract"], "abstract", idx
            idx += 1

        for sec in parsed["sections"]:
            sec_name = sec["title"] or "body"
            for piece in self._chunk_text(sec["text"], chunk_size, overlap):
                yield piece, sec_name, idx
                idx += 1

    @staticmethod
    def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
        """텍스트를 중첩 청크로 분할 (단어 기준)"""
        words = text.split()
        if len(words) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunks.append(" ".join(words[start:end]))
            start += chunk_size - overlap
        return chunks


if __name__ == "__main__":
    print("=== PMC Vector Store 테스트 ===\n")
    store = PMCVectorStore()
    store.add_papers_from_dir()

    print(f"\nStats: {store.get_stats()}")

    query = "What are common risk factors for chronic disease in patients?"
    print(f"\n검색 쿼리: '{query}'")
    results = store.search(query, n_results=3)
    for r in results:
        meta = r["metadata"]
        print(f"  - [{meta['section']}] {meta['title'][:60]}... (sim={r['similarity']:.3f})")
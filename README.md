# Medical_Ready_Agent
의료 데이터 자가 정제 에이전트 개발

## PMC 데이터 파이프라인 (data/collect_pmc.py, rag/build_vectordb.py)

### 이미 만들어진 결과물 사용
별도로 코드를 돌릴 필요 없이,구글 드라이브에서 두 폴더를 받아 프로젝트 루트의 동일 경로에 압축 해제 -> 바로 검색까지 가능. (구글드라이브는 추후에,,,)
- data/raw/pmc/ (선정된 PMC 논문 250편 XML)
- rag/pmc_vectordb/ (임베딩이 끝난 ChromaDB)

### 파이프라인을 처음부터 재현하거나 데이터를 추가해야한다면,,
1. NCBI PMC OA 벌크 데이터를 받아야 함(수 GB, 로컬 디스크 필요)
   https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_bulk/oa_comm/xml/
   여기서 oa_comm_xml.PMC000xxxxxx.baseline.[날짜].tar.gz 와
   같은 이름의 .filelist.csv 를 받아 프로젝트 루트에 둡니다.
2. python data/collect_pmc.py 실행
   → PubMed 검색 → 클러스터링 → 층화추출 → tar에서 250편 추출
   → data/raw/pmc/ 에 결과 저장
3. python rag/build_vectordb.py 실행
   → XML 파싱 → 청킹 → 배치 임베딩 → rag/pmc_vectordb/ 에 저장
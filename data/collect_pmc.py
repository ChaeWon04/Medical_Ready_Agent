import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer
import tarfile
from lxml import etree

# 1) filelist 구조 확인
filelist_path = "oa_comm_xml.PMC000xxxxxx.baseline.2026-01-23.filelist.csv"
df_filelist = pd.read_csv(filelist_path)
print(df_filelist.columns.tolist())
print(df_filelist.head())
print(f"전체 논문 수: {len(df_filelist)}")

tar_path = "oa_comm_xml.PMC000xxxxxx.baseline.2026-01-23.tar.gz"

def sample_member_names(df_filelist, n=3000, seed=42):
    sampled = df_filelist.sample(n=min(n, len(df_filelist)), random_state=seed)
    return set(sampled["Article File"])  # 컬럼명은 1단계 출력 확인 후 매칭

target_names = sample_member_names(df_filelist, n=3000)

def extract_light_metadata(tar_path, target_names):
    rows = []
    with tarfile.open(tar_path, "r") as tar:
        for member in tar:
            if member.name not in target_names:
                continue
            f = tar.extractfile(member)
            if f is None:
                continue
            try:
                root = etree.fromstring(f.read())
            except Exception:
                continue
            title_nodes = root.xpath(".//article-title")
            title = "".join(title_nodes[0].itertext()).strip() if title_nodes else ""
            abs_nodes = root.xpath(".//abstract")
            abstract = " ".join("".join(n.itertext()).strip() for n in abs_nodes)
            pmcid_nodes = root.xpath(".//article-id[@pub-id-type='pmcid']/text()")
            pmcid = pmcid_nodes[0] if pmcid_nodes else None
            if abstract:  # 초록 없는 논문은 클러스터링 대상에서 제외
                rows.append({
                    "member_name": member.name,
                    "pmcid": pmcid,
                    "title": title,
                    "abstract": abstract
                })
    return pd.DataFrame(rows)

light_df = extract_light_metadata(tar_path, target_names)
print(f"초록 추출 결과: {len(light_df)} / {len(target_names)}")

#클러스터링 & 카테고리 라벨링
def auto_cluster_and_label(df, n_clusters=10, seed=42):
    model = SentenceTransformer("pritamdeka/S-PubMedBert-MS-MARCO")
    embeddings = model.encode(df["abstract"].tolist(), show_progress_bar=True)

    kmeans = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10)
    df = df.copy()
    df["cluster"] = kmeans.fit_predict(embeddings)

    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000, ngram_range=(1, 2))
    cluster_docs = df.groupby("cluster")["abstract"].apply(lambda x: " ".join(x))
    tfidf_matrix = vectorizer.fit_transform(cluster_docs)
    feature_names = vectorizer.get_feature_names_out()

    cluster_labels = {}
    for idx, cluster_id in enumerate(cluster_docs.index):
        row = tfidf_matrix[idx].toarray().flatten()
        top_indices = row.argsort()[-5:][::-1]
        cluster_labels[cluster_id] = ", ".join(feature_names[i] for i in top_indices)

    df["cluster_label"] = df["cluster"].map(cluster_labels)
    return df

labeled_df = auto_cluster_and_label(light_df, n_clusters=10)
print(labeled_df[["cluster", "cluster_label"]].drop_duplicates().sort_values("cluster"))
# %%
print(labeled_df["cluster"].value_counts().sort_index())
# %% 카테고리별 비례 추출 후 전체 본문 추출
def stratified_sample(df, n_total=250, seed=42):
    proportions = df["cluster"].value_counts(normalize=True)
    samples = []
    for cluster_id, prop in proportions.items():
        n_take = max(1, round(prop * n_total))
        sub = df[df["cluster"] == cluster_id]
        samples.append(sub.sample(n=min(n_take, len(sub)), random_state=seed))
    return pd.concat(samples)

final_df = stratified_sample(labeled_df, n_total=250)

# 최종 선정된 논문의 전체 XML을 tar에서 추출
from pathlib import Path

def extract_selected_articles(tar_path, member_names, out_dir="./pmc_xml_selected"):
    out = Path(out_dir)
    out.mkdir(exist_ok=True)
    member_names = set(member_names)
    extracted = 0
    with tarfile.open(tar_path, "r") as tar:
        for member in tar:
            if member.name in member_names:
                tar.extract(member, path=out)
                extracted += 1
                if extracted == len(member_names):
                    break
    print(f"{extracted}/{len(member_names)}편 추출 완료 → {out_dir}")

extract_selected_articles(tar_path, final_df["member_name"].tolist())
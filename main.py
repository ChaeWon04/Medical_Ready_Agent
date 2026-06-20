import json
from dotenv import load_dotenv
from config import OUTPUT_DIR, DATA_SOURCE
import agents.agent1_parser as agent1
from graph.pipeline import run_pipeline

load_dotenv()


def main():
    print(f"[Medical_Ready_Agent] 데이터 소스: {DATA_SOURCE}")

    records = agent1.run(limit=10)
    print(f"Agent 1 완료: {len(records)}개 레코드 파싱")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for i, record in enumerate(records):
        print(f"  처리 중 {i+1}/{len(records)}: {record.patient_id}")
        processed = run_pipeline(record)
        results.append(processed.model_dump())

    out_path = OUTPUT_DIR / f"{DATA_SOURCE}_output.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    flagged = [r for r in results if r.get("flagged")]
    print(f"\n완료: {len(results)}개 → {out_path}")
    if flagged:
        print(f"검토 필요: {len(flagged)}개 레코드 플래그됨")


if __name__ == "__main__":
    main()

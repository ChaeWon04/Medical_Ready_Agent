import textstat
from schemas.ai_ready_schema import AIReadyRecord

_ENCOUNTER_KEYWORDS = {
    "emergency": ["emergency", "er", "urgent", "acute"],
    "inpatient": ["inpatient", "admission", "hospital", "icu"],
    "outpatient": ["outpatient", "clinic", "visit", "checkup"],
}


def _classify_encounter(record: AIReadyRecord) -> str:
    if record.encounter_type:
        return record.encounter_type
    text = " ".join(record.diagnoses + record.symptoms).lower()
    for enc_type, keywords in _ENCOUNTER_KEYWORDS.items():
        if any(k in text for k in keywords):
            return enc_type
    return "outpatient"


def _readability(record: AIReadyRecord) -> float:
    text = " ".join(
        record.diagnoses + record.symptoms + [record.chief_complaint or ""]
    ).strip()
    return textstat.flesch_reading_ease(text) if text else 0.0


def run(record: AIReadyRecord) -> AIReadyRecord:
    record.encounter_type = _classify_encounter(record)
    record.readability_score = _readability(record)
    return record

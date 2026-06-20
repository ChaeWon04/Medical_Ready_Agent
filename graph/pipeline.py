from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from agents.agent1_parser import Agent1Parser
from agents.agent2_reflexion import Agent2Reflexion
from agents.agent3_annotator import Agent3Annotator
from schemas.ai_ready_schema import AIReadyRecord
import json
from config import OUTPUT_DIR

agent1 = Agent1Parser()
agent2 = Agent2Reflexion()
agent3 = Agent3Annotator()


class PipelineState(TypedDict):
    source: str
    raw_input: dict
    record: Optional[dict]
    error: Optional[str]


def parse_node(state: PipelineState) -> PipelineState:
    try:
        source = state["source"]
        raw = state["raw_input"]

        if source == "synthea":
            record = agent1.parse_synthea(patient_id=raw["patient_id"])
        elif source == "mimic_iv":
            if "note_text" in raw:
                record = agent1.parse_mimic_note(
                    note_text=raw["note_text"],
                    subject_id=raw["subject_id"],
                    hadm_id=raw.get("hadm_id", ""),
                )
            else:
                record = agent1.parse_mimic_structured(
                    subject_id=raw["subject_id"],
                    hadm_id=raw["hadm_id"],
                    diagnoses_df=raw["diagnoses_df"],
                    prescriptions_df=raw["prescriptions_df"],
                )
        elif source == "eicu":
            if "note_text" in raw:
                record = agent1.parse_eicu_note(
                    note_text=raw["note_text"],
                    patient_stay_id=raw["patient_stay_id"],
                )
            else:
                record = agent1.parse_eicu_structured(
                    patient_stay_id=raw["patient_stay_id"],
                    diagnosis_df=raw["diagnosis_df"],
                    medication_df=raw["medication_df"],
                    lab_df=raw["lab_df"],
                )
        else:
            return {**state, "error": f"알 수 없는 소스: {source}"}

        return {**state, "record": json.loads(record.model_dump_json()), "error": None}

    except Exception as e:
        return {**state, "error": str(e)}


def reflexion_node(state: PipelineState) -> PipelineState:
    if state.get("error") or not state.get("record"):
        return state
    try:
        record = AIReadyRecord(**state["record"])
        record = agent2.run(record)
        return {**state, "record": json.loads(record.model_dump_json())}
    except Exception as e:
        return {**state, "error": str(e)}


def annotate_node(state: PipelineState) -> PipelineState:
    if state.get("error") or not state.get("record"):
        return state
    try:
        record = AIReadyRecord(**state["record"])
        record = agent3.annotate(record)
        return {**state, "record": json.loads(record.model_dump_json())}
    except Exception as e:
        return {**state, "error": str(e)}


def save_node(state: PipelineState) -> PipelineState:
    if state.get("error") or not state.get("record"):
        return state
    try:
        record_dict = state["record"]
        record_id = record_dict.get("record_id", "unknown")
        out_path = OUTPUT_DIR / f"{record_id}.json"
        out_path.write_text(json.dumps(record_dict, indent=2, ensure_ascii=False))
    except Exception as e:
        return {**state, "error": str(e)}
    return state


def should_continue(state: PipelineState) -> str:
    return "end" if state.get("error") else "continue"


def build_pipeline():
    graph = StateGraph(PipelineState)
    graph.add_node("parse", parse_node)
    graph.add_node("reflexion", reflexion_node)
    graph.add_node("annotate", annotate_node)
    graph.add_node("save", save_node)
    graph.set_entry_point("parse")
    graph.add_conditional_edges("parse", should_continue, {"continue": "reflexion", "end": END})
    graph.add_conditional_edges("reflexion", should_continue, {"continue": "annotate", "end": END})
    graph.add_conditional_edges("annotate", should_continue, {"continue": "save", "end": END})
    graph.add_edge("save", END)
    return graph.compile()


pipeline = build_pipeline()

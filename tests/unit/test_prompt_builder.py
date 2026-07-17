from app.rag.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from app.rag.retriever import RetrievedChunk


def _chunk(text="Boot space is 433 litres.", page=12, section="Dimensions", car="Hyundai Creta"):
    return RetrievedChunk(
        chunk_id="c1",
        text=text,
        metadata={"page_number": page, "section": section, "car_name": car, "brochure_id": "b1"},
        score=0.9,
    )


def test_system_prompt_forbids_outside_knowledge():
    assert "ONLY" in SYSTEM_PROMPT
    assert "I couldn't find this information in the uploaded brochure." in SYSTEM_PROMPT


def test_user_prompt_includes_context_and_question():
    prompt = build_user_prompt("What is the boot space?", [_chunk()])
    assert "boot space" in prompt.lower()
    assert "433 litres" in prompt
    assert "Page: 12" in prompt


def test_user_prompt_includes_history_when_provided():
    prompt = build_user_prompt("And the mileage?", [_chunk()], history="user: hi\nassistant: hello")
    assert "Previous conversation" in prompt

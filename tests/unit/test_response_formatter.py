from app.rag.response_formatter import NOT_FOUND_MESSAGE, format_response
from app.rag.retriever import RetrievedChunk


def _chunk(chunk_id="c1", page=5, section="Safety", brochure_id="b1"):
    return RetrievedChunk(
        chunk_id=chunk_id,
        text="Six airbags are standard.",
        metadata={"page_number": page, "section": section, "brochure_id": brochure_id},
        score=0.8,
    )


def test_format_response_returns_sources_for_grounded_answer():
    answer, sources = format_response("Six airbags are standard (Page 5).", [_chunk()], {"b1": "Creta"})
    assert "airbags" in answer
    assert len(sources) == 1
    assert sources[0].brochure_name == "Creta"
    assert sources[0].page == 5


def test_format_response_suppresses_sources_when_not_found():
    answer, sources = format_response(NOT_FOUND_MESSAGE, [_chunk()], {"b1": "Creta"})
    assert answer == NOT_FOUND_MESSAGE
    assert sources == []


def test_format_response_deduplicates_same_page_sources():
    chunks = [_chunk(chunk_id="c1"), _chunk(chunk_id="c2")]  # same page/section/brochure
    _, sources = format_response("Answer text.", chunks, {"b1": "Creta"})
    assert len(sources) == 1


def test_format_response_defaults_empty_answer_to_not_found():
    answer, sources = format_response("   ", [_chunk()], {"b1": "Creta"})
    assert answer == NOT_FOUND_MESSAGE
    assert sources == []

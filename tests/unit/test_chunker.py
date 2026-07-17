from app.chunking.chunker import SemanticChunker
from app.parser.base import ParsedBlock


def test_chunker_respects_max_tokens_and_produces_overlap():
    blocks = [
        ParsedBlock(text="Safety", page_number=1, block_type="heading"),
        ParsedBlock(text=" ".join(["airbag"] * 100), page_number=1),
        ParsedBlock(text=" ".join(["seatbelt"] * 100), page_number=1),
        ParsedBlock(text=" ".join(["abs"] * 100), page_number=2),
    ]

    chunker = SemanticChunker(max_tokens=150, overlap_tokens=20)
    chunks = chunker.chunk(blocks)

    assert len(chunks) >= 2
    for c in chunks:
        assert c.section == "Safety"
        assert c.text.strip()


def test_chunker_handles_empty_input():
    chunker = SemanticChunker()
    assert chunker.chunk([]) == []


def test_chunker_carries_page_number():
    blocks = [
        ParsedBlock(text="Engine specs are listed here.", page_number=5),
    ]
    chunks = SemanticChunker().chunk(blocks)
    assert chunks[0].page_number == 5

import shutil
import tempfile

import pytest

from app.vectorstore.faiss_store import FaissVectorStore
from app.vectorstore.base import VectorRecord


@pytest.fixture
def store():
    tmp_dir = tempfile.mkdtemp()
    s = FaissVectorStore(index_path=f"{tmp_dir}/index.faiss", dimension=4)
    yield s
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_add_and_search(store):
    store.add(
        [
            VectorRecord(id="a", vector=[1, 0, 0, 0], metadata={"car_name": "Creta"}),
            VectorRecord(id="b", vector=[0, 1, 0, 0], metadata={"car_name": "Venue"}),
        ]
    )
    results = store.search([1, 0, 0, 0], top_k=1)
    assert results[0].id == "a"


def test_metadata_filtering(store):
    store.add(
        [
            VectorRecord(id="a", vector=[1, 0, 0, 0], metadata={"car_name": "Creta"}),
            VectorRecord(id="b", vector=[0.9, 0.1, 0, 0], metadata={"car_name": "Venue"}),
        ]
    )
    results = store.search([1, 0, 0, 0], top_k=5, filters={"car_name": "Venue"})
    assert len(results) == 1
    assert results[0].id == "b"


def test_delete(store):
    store.add([VectorRecord(id="a", vector=[1, 0, 0, 0], metadata={})])
    store.delete(["a"])
    assert store.search([1, 0, 0, 0], top_k=5) == []


def test_persistence_across_instances():
    tmp_dir = tempfile.mkdtemp()
    try:
        path = f"{tmp_dir}/index.faiss"
        s1 = FaissVectorStore(index_path=path, dimension=4)
        s1.add([VectorRecord(id="a", vector=[1, 0, 0, 0], metadata={"car_name": "Creta"})])

        s2 = FaissVectorStore(index_path=path, dimension=4)
        results = s2.search([1, 0, 0, 0], top_k=1)
        assert results[0].id == "a"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

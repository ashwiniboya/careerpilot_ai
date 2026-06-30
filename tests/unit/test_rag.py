import os
import pytest
from rag.document_parser import DocumentParser, RecursiveCharacterTextSplitter

def test_document_parser_text(tmp_path):
    # Create temp text file
    file_path = tmp_path / "resume_mock.md"
    content = "# Alice Candidate\nSkills: Python, SQL\n\nExperience:\n- Software Engineer at Google"
    file_path.write_text(content, encoding="utf-8")

    parsed_text = DocumentParser.parse_file(str(file_path))
    assert "Alice Candidate" in parsed_text
    assert "Software Engineer at Google" in parsed_text


def test_recursive_character_splitter():
    splitter = RecursiveCharacterTextSplitter(chunk_size=50, chunk_overlap=10)
    text = "This is a longer paragraph that we want to split into smaller chunks so that it fits nicely inside the context window of our vector database."
    
    chunks = splitter.split_text(text)
    assert len(chunks) > 1
    # Verify that each chunk is bounded in length roughly around chunk_size
    for chunk in chunks:
        assert len(chunk) <= 65  # allow small buffer for word boundary


def test_vector_store_add_and_search(temp_vector_store):
    user_id = 99
    texts = [
        "Python is a versatile programming language used in machine learning.",
        "React is a frontend javascript library built by Meta.",
        "Docker allows developers to package applications into container systems."
    ]
    metadatas = [
        {"user_id": user_id, "doc_type": "note", "title": "python"},
        {"user_id": user_id, "doc_type": "note", "title": "react"},
        {"user_id": user_id, "doc_type": "reference", "title": "docker"}
    ]
    
    # Add documents
    temp_vector_store.add_documents(texts, metadatas)
    
    # Query for Python
    results = temp_vector_store.search("How to write python code?", user_id=user_id, limit=2)
    assert len(results) >= 1
    assert "Python" in results[0]["text"]
    assert results[0]["metadata"]["user_id"] == user_id
    
    # Query with doc_type filter
    ref_results = temp_vector_store.search("Docker containers", user_id=user_id, limit=1, doc_type="reference")
    assert len(ref_results) == 1
    assert "Docker" in ref_results[0]["text"]
    assert ref_results[0]["metadata"]["doc_type"] == "reference"
    
    # Query for different user (should return nothing due to filter)
    other_results = temp_vector_store.search("Python ML", user_id=100)
    assert len(other_results) == 0


def test_vector_store_delete(temp_vector_store):
    user_id = 42
    texts = ["Some secure personal document for user 42."]
    metadatas = [{"user_id": user_id, "doc_type": "private"}]
    
    temp_vector_store.add_documents(texts, metadatas)
    
    # Verify exists
    results = temp_vector_store.search("secure personal document", user_id=user_id)
    assert len(results) == 1
    
    # Delete
    temp_vector_store.delete_user_documents(user_id)
    
    # Verify deleted
    post_delete = temp_vector_store.search("secure personal document", user_id=user_id)
    assert len(post_delete) == 0

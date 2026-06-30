import os
import sys
from unittest.mock import MagicMock

# Mock grpc and opentelemetry grpc exporters to bypass DLL load blocks on restricted Windows environments
sys.modules['grpc'] = MagicMock()
sys.modules['grpc._cython'] = MagicMock()
sys.modules['grpc._cython.cygrpc'] = MagicMock()
sys.modules['opentelemetry.exporter.otlp.proto.grpc.trace_exporter'] = MagicMock()

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import Base
import database.models as models

# Setup in-memory database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provides a transactional database session for a single test function."""
    connection = test_engine.connect()
    transaction = connection.begin()
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def temp_vector_store(tmp_path):
    """Provides a clean temporary ChromaDB vector store path."""
    from rag.vector_store import VectorStore
    store = VectorStore(db_path=str(tmp_path / "test_vector_db"), collection_name="test_collection")
    yield store

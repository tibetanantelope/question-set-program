import asyncio
import os
from functools import partial

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import Document
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.vector_stores.chroma import ChromaVectorStore

from pathlib import Path

from backend.env import load_backend_env

from backend.agents.agent.get_llm import get_embedding_model
from backend.middleware.logging import get_logger

logger = get_logger(__name__)

load_backend_env()

COLLECTION_NAME = os.getenv('CHROMA_COLLECTION', 'vector_store_collection')
PERSIST_DIR = os.getenv('CHROMA_PERSIST_DIR', str(Path(__file__).resolve().parents[2] / 'chroma_db'))


from backend.core.single_tool import singleMeta


class VectorStoreManager(metaclass=singleMeta):
    def __init__(self):
        os.makedirs(PERSIST_DIR, exist_ok=True)

        # 鏄惧紡鎸佹湁 embedding 妯″瀷瀹炰緥锛圖ashScope 灏佽锛?
        self.embed_model = get_embedding_model()

        # 鍒濆鍖?Chroma 鍚戦噺瀛樺偍
        self.vector_store = ChromaVectorStore.from_params(
            collection_name=COLLECTION_NAME,
            persist_dir=PERSIST_DIR
        )
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

        # 缂撳瓨 index锛屾暣涓敓鍛藉懆鏈熷鐢紝閬垮厤姣忔鎿嶄綔閲嶅缓
        # 鏄惧紡缁戝畾 embed_model锛屼笉渚濊禆鍏ㄥ眬 Settings
        self._index = VectorStoreIndex.from_vector_store(
            self.vector_store,
            storage_context=self.storage_context,
            embed_model=self.embed_model,
        )

    async def add_document(self, text: str, metadata: dict = None) -> bool:
        """Add a document to the vector store."""
        try:
            if metadata is None:
                metadata = {}
            document = Document(text=text, metadata=metadata)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, partial(self._index.insert, document))
            return True
        except Exception as e:
            logger.error("Error adding document: %s", e, exc_info=True)
            return False

    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the vector store."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, partial(self.vector_store.delete, doc_id))
            return True
        except Exception as e:
            logger.error("Error deleting document: %s", e, exc_info=True)
            return False

    async def update_document(self, doc_id: str, text: str, metadata: dict = None) -> bool:
        """Update a document in the vector store."""
        if not await self.delete_document(doc_id):
            return False
        if metadata is None:
            metadata = {}
        document = Document(text=text, metadata=metadata, doc_id=doc_id)
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, partial(self._index.insert, document))
            return True
        except Exception as e:
            logger.error("Error updating document: %s", e, exc_info=True)
            return False

    async def query(self, query_text: str, user_id: int = None, top_k: int = 5):
        """Query the vector store, optionally filtered by user_id."""
        filters = None
        if user_id is not None:
            filters = MetadataFilters(
                filters=[ExactMatchFilter(key="user_id", value=user_id)]
            )

        query_engine = self._index.as_query_engine(
            similarity_top_k=top_k,
            filters=filters,
            embed_model=self.embed_model,
        )
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, partial(query_engine.query, query_text)
        )
        return response

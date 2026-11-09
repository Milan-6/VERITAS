import logging
import os
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient, models
from app.core.config import settings
from app.services.embeddings import dense_embedder, sparse_vectorizer, BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class QdrantVectorStore:
    def __init__(
        self,
        collection_name: str = settings.QDRANT_COLLECTION,
        embedder: Optional[BaseEmbeddingProvider] = None,
        client: Optional[QdrantClient] = None,
    ):
        self.collection_name = collection_name
        self.embedder = embedder or dense_embedder
        self.client = client or self._init_client()
        self._ensure_collection()

    def _init_client(self) -> QdrantClient:
        """
        Connects to Qdrant server (e.g. Docker localhost:6333 or cloud URL),
        falling back to local persistent storage path if remote server is unreachable.
        """
        if settings.QDRANT_URL:
            try:
                logger.info(f"Connecting to Qdrant at {settings.QDRANT_URL}")
                return QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY, timeout=5.0)
            except Exception as e:
                logger.warning(f"Could not connect to Qdrant URL {settings.QDRANT_URL}: {e}")

        if settings.QDRANT_HOST:
            try:
                c = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=2.0)
                c.get_collections()
                logger.info(f"Connected to Qdrant server at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
                return c
            except Exception:
                logger.info("Remote Qdrant server unreachable. Falling back to local embedded Qdrant.")

        # Default: local embedded Qdrant storage engine
        local_path = settings.QDRANT_LOCAL_PATH
        os.makedirs(local_path, exist_ok=True)
        return QdrantClient(path=local_path)

    def _ensure_collection(self):
        """Creates collection with dense and sparse vector configurations if not existing."""
        try:
            collections = [c.name for c in self.client.get_collections().collections]
            if self.collection_name not in collections:
                logger.info(f"Creating Qdrant collection '{self.collection_name}'")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "dense": models.VectorParams(
                            size=self.embedder.dimension,
                            distance=models.Distance.COSINE,
                        )
                    },
                    sparse_vectors_config={
                        "sparse": models.SparseVectorParams()
                    },
                )

                # Create payload indexes for strict tenant and document isolation
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name="tenant_id",
                        field_schema=models.PayloadSchemaType.KEYWORD,
                    )
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name="document_id",
                        field_schema=models.PayloadSchemaType.KEYWORD,
                    )
                except Exception as idx_err:
                    logger.debug(f"Payload index creation note: {idx_err}")
        except Exception as e:
            logger.error(f"Error ensuring Qdrant collection {self.collection_name}: {e}")

    def index_chunks(
        self,
        tenant_id: str,
        document_id: str,
        document_title: str,
        chunks: List[Any],
    ) -> List[str]:
        """
        Embeds and indexes a list of semantic chunks into Qdrant with dense and sparse vectors.
        Returns list of generated Qdrant point IDs.
        """
        if not chunks:
            return []

        points: List[models.PointStruct] = []
        point_ids: List[str] = []

        # Batch embed dense vectors
        texts_to_embed = [getattr(c, "embedded_text", c.content_text) for c in chunks]
        dense_vectors = self.embedder.embed_batch(texts_to_embed)

        for i, chunk in enumerate(chunks):
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)

            content_text = getattr(chunk, "content_text", "")
            embedded_text = getattr(chunk, "embedded_text", content_text)
            chunk_id = getattr(chunk, "chunk_id", f"chk_{document_id}_{i}")
            page_number = getattr(chunk, "page_number", 1)
            section_title = getattr(chunk, "section_title", "General")
            subsection = getattr(chunk, "subsection", None)
            token_count = getattr(chunk, "token_count", 0)

            # Compute sparse BM25 vector
            sparse_vec = sparse_vectorizer.vectorize(embedded_text)
            dense_vec = dense_vectors[i]

            payload = {
                "tenant_id": tenant_id,
                "document_id": document_id,
                "document_title": document_title,
                "chunk_id": chunk_id,
                "page_number": page_number,
                "section_title": section_title,
                "subsection": subsection,
                "content_text": content_text,
                "embedded_text": embedded_text,
                "token_count": token_count,
            }

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector={
                        "dense": dense_vec,
                        "sparse": sparse_vec,
                    },
                    payload=payload,
                )
            )

        # Upsert into Qdrant in batches of 100
        batch_size = 100
        for b_idx in range(0, len(points), batch_size):
            batch = points[b_idx : b_idx + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
            )

        logger.info(f"Successfully indexed {len(points)} chunks into Qdrant for doc {document_id}")
        return point_ids

    def delete_document_vectors(self, document_id: str) -> bool:
        """
        Physically removes all vectors and points matching `document_id` from Qdrant.
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
            logger.info(f"Deleted vectors for document {document_id} from Qdrant")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document vectors from Qdrant: {e}")
            return False


vector_store = QdrantVectorStore()

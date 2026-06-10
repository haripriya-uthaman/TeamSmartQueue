import logging
import os
from sentence_transformers import SentenceTransformer
import chromadb
from app.core.config import settings
from app.schemas.ticket import DuplicateResult

logger = logging.getLogger(__name__)


class DuplicateService:
    """
    DuplicateService manages ticket duplicate detection by storing and searching
    embeddings using ChromaDB and the BAAI/bge-small-en-v1.5 sentence-transformers model.
    """
    def __init__(self) -> None:
        self._model = None
        self._client = None
        self._collection = None

    @property
    def model(self) -> SentenceTransformer:
        """
        Lazily initialize the sentence-transformers embedding model.
        """
        if self._model is None:
            logger.info("Initializing SentenceTransformer model: BAAI/bge-small-en-v1.5...")
            # Note: sentence-transformers will download and cache this locally
            self._model = SentenceTransformer('BAAI/bge-small-en-v1.5')
            logger.info("SentenceTransformer model loaded successfully.")
        return self._model

    @property
    def client(self) -> chromadb.api.client.Client:
        """
        Lazily initialize the Chroma DB client.
        """
        if self._client is None:
            os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
            self._client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
            logger.info("Chroma persistent client initialized at: %s", settings.CHROMA_DB_PATH)
        return self._client

    @property
    def collection(self):
        """
        Lazily get or create the Chroma collection for tickets with cosine space.
        """
        if self._collection is None:
            # We use cosine distance space to calculate cosine similarity score as: 1.0 - cosine_distance
            self._collection = self.client.get_or_create_collection(
                name="tickets",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Chroma collection 'tickets' ready.")
        return self._collection

    def add_ticket(self, ticket_id: str, title: str, description: str, metadata: dict = None) -> None:
        """
        Generates and indexes the embedding for a ticket.
        """
        text_to_embed = f"Title: {title}\nDescription: {description}"
        logger.info("Generating embedding for ticket ID: %s", ticket_id)
        
        try:
            embedding = self.model.encode(text_to_embed).tolist()
            
            meta = metadata or {}
            meta["title"] = title
            
            self.collection.add(
                ids=[ticket_id],
                embeddings=[embedding],
                documents=[text_to_embed],
                metadatas=[meta]
            )
            logger.info("Successfully added ticket ID '%s' to duplicate detection store.", ticket_id)
        except Exception as e:
            logger.error("Failed to add ticket '%s' to duplicate detection store: %s", ticket_id, str(e), exc_info=True)
            raise e

    def find_duplicate(self, title: str, description: str, threshold: float = 0.85) -> DuplicateResult:
        """
        Finds the top similar ticket in the database.
        
        Returns:
            DuplicateResult: The duplication check results.
        """
        text_to_embed = f"Title: {title}\nDescription: {description}"
        logger.info("Searching for duplicate tickets. Threshold: %.2f", threshold)
        
        try:
            # If collection is empty, return not duplicate
            count = self.collection.count()
            if count == 0:
                logger.info("No tickets in the database. Skipping search.")
                return DuplicateResult(is_duplicate=False)
                
            embedding = self.model.encode(text_to_embed).tolist()
            
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=1
            )
            
            if not results or not results["ids"] or not results["ids"][0]:
                logger.info("No matching tickets returned from ChromaDB.")
                return DuplicateResult(is_duplicate=False)
                
            duplicate_id = results["ids"][0][0]
            distance = results["distances"][0][0]
            
            # Cosine similarity calculation
            similarity_score = 1.0 - distance
            
            is_duplicate = similarity_score >= threshold
            
            explanation = (
                f"Similarity score is {similarity_score:.4f} (threshold: {threshold:.4f}) "
                f"matching ticket ID '{duplicate_id}'."
            ) if is_duplicate else f"No duplicate found above similarity threshold {threshold}. Nearest match score: {similarity_score:.4f}."
            
            logger.info("Search result: is_duplicate=%s, score=%.4f", is_duplicate, similarity_score)
            return DuplicateResult(
                is_duplicate=is_duplicate,
                duplicate_ticket_id=duplicate_id if is_duplicate else None,
                similarity_score=similarity_score,
                matching_explanation=explanation
            )
        except Exception as e:
            logger.error("Error occurred while searching for duplicates: %s", str(e), exc_info=True)
            raise e


# Export a singleton instance
duplicate_service = DuplicateService()

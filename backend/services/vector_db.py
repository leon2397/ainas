"""
Vector Database Service
Using ChromaDB for similarity search and deduplication
"""

import os
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import chromadb

from database.db import Database


# ChromaDB 1.x compatible client initialization
def _create_chroma_client(persist_dir: str):
    """Create ChromaDB client with the best available API for the installed version."""
    persist_path = Path(persist_dir)
    persist_path.mkdir(parents=True, exist_ok=True)

    # ChromaDB 1.x: PersistentClient(path=...) is the recommended API.
    # chromadb.Client + Settings() is deprecated but still functional.
    # We use PersistentClient for forward-compatibility.
    try:
        return chromadb.PersistentClient(path=str(persist_path))
    except TypeError:
        # Fallback for older ChromaDB 0.x API signature
        from chromadb.config import Settings
        return chromadb.Client(Settings(
            persist_directory=str(persist_path),
            anonymized_telemetry=False
        ))


class VectorDB:
    """
    Vector database for similarity search.

    Uses ChromaDB for:
    - Feature vector storage
    - Similarity-based deduplication
    - Content-based image search
    """

    COLLECTION_NAME = "media_features"

    def __init__(self, db: Database, persist_dir: str = "./data/chroma"):
        self.db = db
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = _create_chroma_client(str(self.persist_dir))

        # Get or create collection (get_collection raises if not exists)
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """Get or create the media collection (safe, no raise if missing)."""
        try:
            return self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "Media file feature vectors"}
            )
        except Exception:
            # Fallback for ChromaDB 0.x API
            try:
                return self.client.create_collection(
                    name=self.COLLECTION_NAME,
                    metadata={"description": "Media file feature vectors"}
                )
            except Exception:
                # Already exists (race condition)
                return self.client.get_collection(self.COLLECTION_NAME)

    async def add_features(
        self,
        file_id: int,
        features: List[float],
        metadata: Dict = None
    ) -> str:
        """
        Add feature vector for a file.

        Args:
            file_id: Database file ID
            features: Feature vector
            metadata: Additional metadata (file_path, tags, etc.)

        Returns:
            Vector ID in ChromaDB
        """
        if isinstance(features, list):
            features = np.array(features)

        meta = dict(metadata) if metadata else {}
        meta['file_id'] = file_id
        vector_id = f"file_{file_id}"

        try:
            self.collection.add(
                ids=[vector_id],
                embeddings=[features.tolist()],
                metadatas=[meta]
            )
            return vector_id
        except Exception as e:
            logger.info(f"Add features error: {e}")
            return None

    async def find_similar(
        self,
        features: List[float],
        limit: int = 5,
        threshold: float = 0.8
    ) -> List[Dict]:
        """
        Find similar files based on feature vector.

        Args:
            features: Query feature vector
            limit: Maximum results
            threshold: Similarity threshold (0-1)

        Returns:
            List of similar files with similarity scores
        """
        if isinstance(features, list):
            features = np.array(features)

        try:
            results = self.collection.query(
                query_embeddings=[features.tolist()],
                n_results=limit
            )

            similar = []
            if results and results.get('ids'):
                distances = results['distances'][0]
                ids = results['ids'][0]
                metadatas = results['metadatas'][0]

                for i, dist in enumerate(distances):
                    # Convert L2 distance to similarity
                    similarity = 1.0 / (1.0 + float(dist))

                    if similarity >= threshold:
                        similar.append({
                            'file_id': metadatas[i].get('file_id'),
                            'file_path': metadatas[i].get('file_path'),
                            'similarity': float(similarity),
                            'distance': float(dist)
                        })

            return similar

        except Exception as e:
            logger.info(f"Find similar error: {e}")
            return []

    async def find_duplicates(
        self,
        file_id: int,
        features: List[float],
        threshold: float = 0.85
    ) -> List[Dict]:
        """
        Find duplicate files for a given file.

        Args:
            file_id: File to check
            features: Feature vector
            threshold: Similarity threshold

        Returns:
            List of duplicate files
        """
        similar = await self.find_similar(features, limit=10, threshold=threshold)
        return [s for s in similar if s.get('file_id') != file_id]

    async def sync_from_database(self):
        """
        Sync feature vectors from SQLite database to ChromaDB.

        Used for:
        - Initial sync
        - Recovery
        - Repair
        """
        logger.info("Syncing feature vectors from database to ChromaDB...")

        files = await self.db.fetchall(
            """SELECT id, file_path, file_name, tags, feature_vector
               FROM media_files
               WHERE feature_vector IS NOT NULL"""
        )

        import json
        from loguru import logger
        added = 0
        for file_info in files:
            try:
                feature_bytes = file_info.get('feature_vector')
                if feature_bytes:
                    features = np.frombuffer(feature_bytes, dtype=np.float32)

                    tags_str = file_info.get('tags', '[]')
                    try:
                        tags = json.loads(tags_str) if isinstance(tags_str, str) else tags_str
                    except Exception:
                        tags = []

                    await self.add_features(
                        file_id=file_info['id'],
                        features=features,
                        metadata={
                            'file_path': file_info['file_path'],
                            'file_name': file_info['file_name'],
                            'tags': json.dumps(tags) if tags else ''
                        }
                    )
                    added += 1

            except Exception as e:
                logger.info(f"Sync error for file {file_info['id']}: {e}")

        logger.info(f"Synced {added} feature vectors")
        return {'synced': added}

    async def remove_features(self, file_id: int):
        """Remove feature vector for a file."""
        try:
            vector_id = f"file_{file_id}"
            self.collection.delete(ids=[vector_id])
            return True
        except Exception as e:
            logger.info(f"Remove features error: {e}")
            return False

    async def get_collection_stats(self) -> Dict:
        """Get collection statistics."""
        try:
            return {
                'total_vectors': self.collection.count(),
                'persist_directory': str(self.persist_dir)
            }
        except Exception as e:
            return {'error': str(e)}

    async def search_by_tags(
        self,
        tags: List[str],
        limit: int = 50
    ) -> List[Dict]:
        """
        Search files by tags using ChromaDB metadata filtering.

        Args:
            tags: List of tags to search
            limit: Maximum results

        Returns:
            List of matching files
        """
        try:
            results = self.collection.get(
                where_document={"$contains": " ".join(tags)}
            )

            files = []
            if results and results.get('ids'):
                for i, vector_id in enumerate(results['ids']):
                    file_id = results['metadatas'][i].get('file_id')
                    if file_id:
                        files.append({
                            'file_id': file_id,
                            'file_path': results['metadatas'][i].get('file_path'),
                            'tags': results['metadatas'][i].get('tags', '')
                        })

            return files[:limit]

        except Exception as e:
            logger.info(f"Search by tags error: {e}")
            return []


# Global vector DB instance
vector_db: Optional[VectorDB] = None


async def get_vector_db(db: Database) -> VectorDB:
    """Get or create vector DB instance."""
    global vector_db
    if vector_db is None:
        vector_db = VectorDB(db)
    return vector_db

"""
Main ingestion script for processing Japanese markdown documents into LanceDB.
Optimized for Yukio Japanese tutor with proper encoding and metadata extraction.
"""

import os
import asyncio
import logging
import json
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4
import argparse

from dotenv import load_dotenv

from .chunker import ChunkingConfig, create_chunker, DocumentChunk
from .embedder import create_embedder

# Import agent utilities
try:
    from ..agent.db_utils import db_manager
except ImportError:
    # For direct execution or testing
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from agent.db_utils import db_manager

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class JapaneseIngestionConfig:
    """Configuration for Japanese content ingestion."""
    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        max_chunk_size: int = 1500,
        use_semantic_chunking: bool = True
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_chunk_size = max_chunk_size
        self.use_semantic_chunking = use_semantic_chunking


class DocumentIngestionPipeline:
    """
    Pipeline for ingesting Japanese documents into LanceDB.
    Optimized for Japanese textbooks, vocabulary, and grammar content.
    """
    
    def __init__(
        self,
        config: JapaneseIngestionConfig,
        documents_folder: str = "data/japanese/markdown",
        clean_before_ingest: bool = False
    ):
        """
        Initialize ingestion pipeline.
        
        Args:
            config: Ingestion configuration
            documents_folder: Folder containing markdown documents
            clean_before_ingest: Whether to clean existing data before ingestion
        """
        self.config = config
        self.documents_folder = documents_folder
        self.clean_before_ingest = clean_before_ingest
        
        # Initialize components
        self.chunker_config = ChunkingConfig(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            max_chunk_size=config.max_chunk_size,
            use_semantic_splitting=config.use_semantic_chunking
        )
        
        self.chunker = create_chunker(self.chunker_config)
        self.embedder = create_embedder()
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connections."""
        if self._initialized:
            return
        
        logger.info("Initializing Japanese ingestion pipeline...")
        
        # Initialize LanceDB
        db_manager.initialize()
        
        self._initialized = True
        logger.info("Pipeline initialized successfully")
    
    async def close(self):
        """Close database connections."""
        if self._initialized:
            db_manager.close()
            self._initialized = False
    
    async def ingest_documents(
        self,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Ingest all Japanese documents from the documents folder.
        
        Args:
            progress_callback: Optional callback for progress updates
        
        Returns:
            List of ingestion results
        """
        if not self._initialized:
            await self.initialize()
        
        # Clean existing data if requested
        if self.clean_before_ingest:
            self._clean_database()
        
        # Find all markdown files
        markdown_files = self._find_markdown_files()
        
        if not markdown_files:
            logger.warning(f"No markdown files found in {self.documents_folder}")
            return []
        
        logger.info(f"Found {len(markdown_files)} Japanese markdown files to process")
        
        results = []
        
        for i, file_path in enumerate(markdown_files):
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing file {i+1}/{len(markdown_files)}: {os.path.basename(file_path)}")
                logger.info(f"{'='*60}")
                
                result = await self._ingest_single_document(file_path)
                results.append(result)
                
                if progress_callback:
                    progress_callback(i + 1, len(markdown_files))
                
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}", exc_info=True)
                results.append({
                    "document_id": "",
                    "title": os.path.basename(file_path),
                    "chunks_created": 0,
                    "processing_time_ms": 0,
                    "errors": [str(e)]
                })
        
        # Log summary
        total_chunks = sum(r.get("chunks_created", 0) for r in results)
        total_errors = sum(len(r.get("errors", [])) for r in results)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"INGESTION COMPLETE")
        logger.info(f"Documents: {len(results)}, Chunks: {total_chunks}, Errors: {total_errors}")
        logger.info(f"{'='*60}\n")
        
        return results
    
    async def _ingest_single_document(self, file_path: str) -> Dict[str, Any]:
        """
        Ingest a single Japanese document.
        
        Args:
            file_path: Path to the document file
        
        Returns:
            Ingestion result dictionary
        """
        start_time = datetime.now()
        errors = []
        
        try:
            # Read document
            document_content = self._read_document(file_path)
            document_title = self._extract_title(document_content, file_path)
            document_source = os.path.relpath(file_path, self.documents_folder)
            
            # Extract Japanese-specific metadata
            document_metadata = self._extract_japanese_metadata(document_content, file_path)
            
            logger.info(f"📚 Title: {document_title}")
            logger.info(f"📄 Source: {document_source}")
            logger.info(f"🏷️  Metadata: {document_metadata}")
            
            # Chunk the document
            logger.info("✂️  Chunking document...")
            chunks = await self.chunker.chunk_document(
                content=document_content,
                title=document_title,
                source=document_source,
                metadata=document_metadata
            )
            
            if not chunks:
                error_msg = "No chunks created"
                logger.warning(f"⚠️  {error_msg}")
                return {
                    "document_id": "",
                    "title": document_title,
                    "chunks_created": 0,
                    "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                    "errors": [error_msg]
                }
            
            logger.info(f"✅ Created {len(chunks)} chunks")
            
            # Generate embeddings
            logger.info("🔢 Generating embeddings...")
            embedded_chunks = await self.embedder.embed_chunks(chunks)
            logger.info(f"✅ Generated embeddings for {len(embedded_chunks)} chunks")
            
            # Save to LanceDB
            logger.info("💾 Saving to LanceDB...")
            document_id = self._save_to_lancedb(
                document_title,
                document_source,
                embedded_chunks,
                document_metadata
            )
            
            logger.info(f"✅ Saved to LanceDB with ID: {document_id}")
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "document_id": document_id,
                "title": document_title,
                "source": document_source,
                "chunks_created": len(chunks),
                "processing_time_ms": processing_time,
                "has_japanese": document_metadata.get("has_japanese", True),
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"❌ Error ingesting document: {e}", exc_info=True)
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "document_id": "",
                "title": os.path.basename(file_path),
                "chunks_created": 0,
                "processing_time_ms": processing_time,
                "errors": [str(e)]
            }
    
    def _find_markdown_files(self) -> List[str]:
        """Find all markdown files in the documents folder."""
        if not os.path.exists(self.documents_folder):
            logger.error(f"Documents folder not found: {self.documents_folder}")
            return []
        
        patterns = ["*.md", "*.markdown", "*.txt"]
        files = []
        
        for pattern in patterns:
            files.extend(glob.glob(os.path.join(self.documents_folder, "**", pattern), recursive=True))
        
        return sorted(files)
    
    def _read_document(self, file_path: str) -> str:
        """Read document content from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    def _extract_title(self, content: str, file_path: str) -> str:
        """Extract title from document content or filename."""
        # Try to find markdown title
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        
        # Fallback to filename
        return os.path.splitext(os.path.basename(file_path))[0]
    
    def _extract_japanese_metadata(self, content: str, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from Japanese document content.
        Includes Japanese-specific analysis like character types and JLPT hints.
        """
        import re
        
        metadata = {
            "file_path": file_path,
            "file_size": len(content),
            "ingestion_date": datetime.now().isoformat()
        }
        
        # Detect Japanese characters
        hiragana = len(re.findall(r'[\u3040-\u309F]', content))
        katakana = len(re.findall(r'[\u30A0-\u30FF]', content))
        kanji = len(re.findall(r'[\u4E00-\u9FFF]', content))
        
        metadata['has_japanese'] = (hiragana + katakana + kanji) > 0
        metadata['character_counts'] = {
            "hiragana": hiragana,
            "katakana": katakana,
            "kanji": kanji
        }
        
        # Try to detect JLPT level from filename or content
        jlpt_pattern = r'N[1-5]|JLPT\s*[1-5]'
        jlpt_match = re.search(jlpt_pattern, content[:500], re.IGNORECASE) or \
                     re.search(jlpt_pattern, file_path, re.IGNORECASE)
        
        if jlpt_match:
            metadata['jlpt_level'] = jlpt_match.group(0).upper()
        
        # Detect content type from title or filename
        filename_lower = os.path.basename(file_path).lower()
        if 'vocab' in filename_lower or '単語' in content[:200]:
            metadata['content_type'] = 'vocabulary'
        elif 'grammar' in filename_lower or '文法' in content[:200]:
            metadata['content_type'] = 'grammar'
        elif 'kanji' in filename_lower or '漢字' in content[:200]:
            metadata['content_type'] = 'kanji'
        elif 'conversation' in filename_lower or 'dialog' in filename_lower or '会話' in content[:200]:
            metadata['content_type'] = 'dialogue'
        else:
            metadata['content_type'] = 'lesson'
        
        # Basic stats
        lines = content.split('\n')
        metadata['line_count'] = len(lines)
        metadata['word_count'] = len(content.split())
        
        return metadata
    
    def _save_to_lancedb(
        self,
        title: str,
        source: str,
        chunks: List[DocumentChunk],
        metadata: Dict[str, Any]
    ) -> str:
        """Save document chunks to LanceDB."""
        document_id = str(uuid4())
        
        # Prepare chunks for LanceDB
        lancedb_chunks = []
        for chunk in chunks:
            # Extract embedding
            embedding = chunk.embedding if hasattr(chunk, 'embedding') else []
            
            if not embedding:
                logger.warning(f"Chunk {chunk.index} has no embedding, skipping")
                continue
            
            # Combine metadata
            chunk_metadata = {
                **metadata,
                **chunk.metadata,
                "document_id": document_id,
                "document_title": title,
                "document_source": source,
            }
            
            lancedb_chunks.append({
                "content": chunk.content,
                "embedding": embedding,
                "chunk_index": chunk.index,
                "metadata": chunk_metadata
            })
        
        # Save to LanceDB
        if lancedb_chunks:
            db_manager.add_chunks(
                chunks=lancedb_chunks,
                document_id=document_id,
                document_title=title,
                document_source=source
            )
        
        return document_id
    
    def _clean_database(self):
        """Clean existing data from LanceDB."""
        logger.warning("⚠️  Cleaning existing data from LanceDB...")
        
        # Get table name and drop it
        table_name = db_manager.table_name
        if table_name in db_manager.db.table_names():
            db_manager.db.drop_table(table_name)
            logger.info(f"✅ Cleared table: {table_name}")
        else:
            logger.info(f"ℹ️  Table {table_name} doesn't exist, nothing to clean")


async def main():
    """Main function for running Japanese document ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest Japanese documents into LanceDB for Yukio tutor"
    )
    parser.add_argument(
        "--documents", "-d",
        default="data/japanese/markdown",
        help="Japanese documents folder path"
    )
    parser.add_argument(
        "--clean", "-c",
        action="store_true",
        help="Clean existing data before ingestion"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=800,
        help="Chunk size for splitting documents (optimized for Japanese)"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=150,
        help="Chunk overlap size"
    )
    parser.add_argument(
        "--no-semantic",
        action="store_true",
        help="Disable semantic chunking"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Print banner
    print("\n" + "="*60)
    print("🏯 YUKIO - Japanese Document Ingestion")
    print("="*60)
    print(f"📁 Documents folder: {args.documents}")
    print(f"✂️  Chunk size: {args.chunk_size}")
    print(f"🔄 Semantic chunking: {not args.no_semantic}")
    print(f"🧹 Clean before ingest: {args.clean}")
    print("="*60 + "\n")
    
    # Create ingestion configuration
    config = JapaneseIngestionConfig(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        max_chunk_size=args.chunk_size * 2,
        use_semantic_chunking=not args.no_semantic
    )
    
    # Create and run pipeline
    pipeline = DocumentIngestionPipeline(
        config=config,
        documents_folder=args.documents,
        clean_before_ingest=args.clean
    )
    
    def progress_callback(current: int, total: int):
        pct = (current / total) * 100
        print(f"\n📊 Progress: {current}/{total} ({pct:.1f}%)")
    
    try:
        start_time = datetime.now()
        
        results = await pipeline.ingest_documents(progress_callback)
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Print summary
        print("\n" + "="*60)
        print("📊 INGESTION SUMMARY")
        print("="*60)
        print(f"📚 Documents processed: {len(results)}")
        print(f"📄 Total chunks created: {sum(r.get('chunks_created', 0) for r in results)}")
        print(f"⏱️  Total processing time: {total_time:.2f} seconds")
        print(f"❌ Total errors: {sum(len(r.get('errors', [])) for r in results)}")
        
        # Show database stats
        stats = db_manager.get_stats()
        print(f"\n💾 LanceDB Stats:")
        print(f"   Total chunks in DB: {stats['total_chunks']}")
        print(f"   Total documents: {stats['total_documents']}")
        print(f"   DB path: {stats['db_path']}")
        
        print("\n" + "="*60)
        print("📖 Document Results:")
        print("="*60)
        
        # Print individual results
        for i, result in enumerate(results, 1):
            status = "✅" if not result.get('errors') else "❌"
            title = result.get('title', 'Unknown')
            chunks = result.get('chunks_created', 0)
            has_jp = "🇯🇵" if result.get('has_japanese', False) else "🔤"
            
            print(f"{status} {has_jp} [{i}] {title}")
            print(f"    Chunks: {chunks}, Time: {result.get('processing_time_ms', 0)/1000:.2f}s")
            
            if result.get('errors'):
                for error in result['errors']:
                    print(f"    ⚠️  Error: {error}")
        
        print("\n" + "="*60)
        print("✅ Ingestion complete!")
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Ingestion interrupted by user")
    except Exception as e:
        logger.error(f"❌ Ingestion failed: {e}", exc_info=True)
        raise
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
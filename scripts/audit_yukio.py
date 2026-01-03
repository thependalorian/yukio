#!/usr/bin/env python3
"""
Comprehensive audit script for Yukio Japanese Tutor.
Checks all components, integrations, and runs tests.
"""

import os
import sys
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AuditResult:
    """Stores audit results."""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""
        self.details: Dict[str, Any] = {}
    
    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} - {self.name}: {self.message}"


class YukioAuditor:
    """Comprehensive auditor for Yukio system."""
    
    def __init__(self):
        self.results: List[AuditResult] = []
        self.base_path = Path(__file__).parent.parent
    
    def add_result(self, result: AuditResult):
        """Add audit result."""
        self.results.append(result)
        print(result)
    
    async def audit_environment(self):
        """Audit environment setup."""
        print("\n" + "="*60)
        print("🔍 AUDIT 1: Environment Configuration")
        print("="*60)
        
        result = AuditResult("Environment Variables")
        
        required_vars = [
            "LLM_PROVIDER",
            "LLM_BASE_URL",
            "LLM_API_KEY",
            "LLM_CHOICE",
            "EMBEDDING_PROVIDER",
            "EMBEDDING_BASE_URL",
            "EMBEDDING_API_KEY",
            "EMBEDDING_MODEL",
            "EMBEDDING_DIMENSIONS",
            "LANCEDB_PATH",
            "LANCEDB_TABLE_NAME",
        ]
        
        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            result.message = f"Missing variables: {', '.join(missing)}"
            result.details = {"missing": missing}
        else:
            result.passed = True
            result.message = "All required environment variables are set"
            result.details = {
                "llm_provider": os.getenv("LLM_PROVIDER"),
                "llm_model": os.getenv("LLM_CHOICE"),
                "embedding_model": os.getenv("EMBEDDING_MODEL"),
                "embedding_dimensions": os.getenv("EMBEDDING_DIMENSIONS"),
            }
        
        self.add_result(result)
    
    async def audit_ollama(self):
        """Audit Ollama installation and models."""
        print("\n" + "="*60)
        print("🔍 AUDIT 2: Ollama Setup")
        print("="*60)
        
        # Check Ollama installation
        result1 = AuditResult("Ollama Installation")
        try:
            import subprocess
            result = subprocess.run(
                ["which", "ollama"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                result1.passed = True
                result1.message = f"Ollama found at: {result.stdout.strip()}"
            else:
                result1.message = "Ollama not found in PATH"
        except Exception as e:
            result1.message = f"Error checking Ollama: {e}"
        self.add_result(result1)
        
        # Check Ollama service
        result2 = AuditResult("Ollama Service")
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                required_models = [
                    os.getenv("LLM_CHOICE", "qwen2.5:14b-instruct"),
                    os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
                ]
                
                # Check if models exist (with or without :latest suffix)
                missing_models = []
                for req_model in required_models:
                    # Check exact match or with :latest suffix
                    found = False
                    for model_name in model_names:
                        # Remove :latest suffix for comparison
                        base_name = model_name.split(":")[0] if ":" in model_name else model_name
                        req_base = req_model.split(":")[0] if ":" in req_model else req_model
                        if base_name == req_base or model_name == req_model:
                            found = True
                            break
                    if not found:
                        missing_models.append(req_model)
                
                if missing_models:
                    result2.message = f"Missing models: {', '.join(missing_models)}"
                    result2.details = {
                        "available": model_names,
                        "required": required_models,
                        "missing": missing_models
                    }
                else:
                    result2.passed = True
                    result2.message = "All required models are available"
                    result2.details = {
                        "available_models": model_names,
                        "required_models": required_models
                    }
            else:
                result2.message = f"Ollama service returned status {response.status_code}"
        except requests.exceptions.ConnectionError:
            result2.message = "Ollama service is not running (connection refused)"
        except Exception as e:
            result2.message = f"Error checking Ollama service: {e}"
        self.add_result(result2)
    
    async def audit_dependencies(self):
        """Audit Python dependencies."""
        print("\n" + "="*60)
        print("🔍 AUDIT 3: Python Dependencies")
        print("="*60)
        
        required_packages = [
            ("pydantic_ai", "pydantic_ai"),
            ("lancedb", "lancedb"),
            ("openai", "openai"),
            ("python-dotenv", "dotenv"),
            ("fastapi", "fastapi"),
            ("uvicorn", "uvicorn"),
            ("requests", "requests"),
            ("aiohttp", "aiohttp"),
        ]
        
        result = AuditResult("Python Dependencies")
        missing = []
        
        for package_name, import_name in required_packages:
            try:
                __import__(import_name)
            except ImportError:
                missing.append(package_name)
        
        if missing:
            result.message = f"Missing packages: {', '.join(missing)}"
            result.details = {"missing": missing}
        else:
            result.passed = True
            result.message = "All required packages are installed"
            result.details = {"packages": required_packages}
        
        self.add_result(result)
    
    async def audit_database(self):
        """Audit LanceDB setup."""
        print("\n" + "="*60)
        print("🔍 AUDIT 4: LanceDB Database")
        print("="*60)
        
        result = AuditResult("LanceDB Setup")
        
        try:
            from agent.db_utils import db_manager
            
            # Initialize database
            db_manager.initialize()
            
            # Get stats
            stats = db_manager.get_stats()
            
            result.passed = True
            result.message = f"Database initialized successfully"
            result.details = {
                "total_chunks": stats.get("total_chunks", 0),
                "total_documents": stats.get("total_documents", 0),
                "db_path": stats.get("db_path", ""),
                "tables": stats.get("tables", [])
            }
            
            if stats.get("total_chunks", 0) == 0:
                result.message += " (no data ingested yet)"
        except Exception as e:
            result.message = f"Database error: {e}"
            result.details = {"error": str(e)}
        
        self.add_result(result)
    
    async def audit_data_files(self):
        """Audit data files."""
        print("\n" + "="*60)
        print("🔍 AUDIT 5: Data Files")
        print("="*60)
        
        result = AuditResult("Markdown Files")
        
        markdown_path = self.base_path / "data" / "japanese" / "markdown"
        
        if not markdown_path.exists():
            result.message = f"Markdown directory not found: {markdown_path}"
        else:
            markdown_files = list(markdown_path.glob("*.md"))
            # Exclude backup files
            markdown_files = [f for f in markdown_files if not f.name.endswith(".backup")]
            
            if not markdown_files:
                result.message = "No markdown files found (excluding backups)"
            else:
                result.passed = True
                result.message = f"Found {len(markdown_files)} markdown files"
                result.details = {
                    "count": len(markdown_files),
                    "files": [f.name for f in markdown_files[:5]],  # First 5
                    "total_size_mb": sum(f.stat().st_size for f in markdown_files) / (1024 * 1024)
                }
        
        self.add_result(result)
    
    async def audit_ingestion_pipeline(self):
        """Test ingestion pipeline components."""
        print("\n" + "="*60)
        print("🔍 AUDIT 6: Ingestion Pipeline")
        print("="*60)
        
        # Test embedder
        result1 = AuditResult("Embedder")
        try:
            from ingestion.embedder import create_embedder
            
            embedder = create_embedder()
            test_text = "こんにちは。日本語のテストです。"
            embedding = await embedder.generate_embedding(test_text)
            
            result1.passed = True
            result1.message = f"Embedder working (dimension: {len(embedding)})"
            result1.details = {
                "model": embedder.model,
                "dimension": len(embedding)
            }
        except Exception as e:
            result1.message = f"Embedder error: {e}"
            result1.details = {"error": str(e)}
        self.add_result(result1)
        
        # Test chunker
        result2 = AuditResult("Chunker")
        try:
            from ingestion.chunker import ChunkingConfig, create_chunker
            
            config = ChunkingConfig(
                chunk_size=800,
                chunk_overlap=150,
                use_semantic_splitting=False
            )
            chunker = create_chunker(config)
            
            test_text = """
            こんにちは。これは日本語のテストです。
            日本語は美しい言語です。文法が複雑ですが、楽しいです。
            漢字、ひらがな、カタカナの三つの文字体系があります。
            """
            
            # Use chunk_document method (may be async or sync)
            if asyncio.iscoroutinefunction(chunker.chunk_document):
                chunks = await chunker.chunk_document(
                    content=test_text,
                    title="Test Document",
                    source="test",
                    metadata={}
                )
            else:
                chunks = chunker.chunk_document(
                    content=test_text,
                    title="Test Document",
                    source="test",
                    metadata={}
                )
            
            result2.passed = True
            result2.message = f"Chunker working ({len(chunks)} chunks created)"
            result2.details = {
                "chunk_count": len(chunks),
                "avg_chunk_size": sum(len(c.content) for c in chunks) / len(chunks) if chunks else 0
            }
        except Exception as e:
            result2.message = f"Chunker error: {e}"
            result2.details = {"error": str(e)}
        self.add_result(result2)
    
    async def audit_agent(self):
        """Audit agent setup."""
        print("\n" + "="*60)
        print("🔍 AUDIT 7: AI Agent")
        print("="*60)
        
        result = AuditResult("Agent Initialization")
        
        try:
            from agent.agent import rag_agent
            from agent.providers import get_llm_model
            
            # Try to get model
            model = get_llm_model()
            
            result.passed = True
            result.message = "Agent initialized successfully"
            result.details = {
                "model": str(model),
            }
        except Exception as e:
            result.message = f"Agent initialization error: {e}"
            result.details = {"error": str(e)}
        
        self.add_result(result)
    
    async def audit_api(self):
        """Audit API setup."""
        print("\n" + "="*60)
        print("🔍 AUDIT 8: FastAPI")
        print("="*60)
        
        result = AuditResult("API Module")
        
        try:
            from agent.api import app
            
            result.passed = True
            result.message = "FastAPI app can be imported"
            result.details = {
                "title": app.title,
                "version": app.version
            }
        except Exception as e:
            result.message = f"API import error: {e}"
            result.details = {"error": str(e)}
        
        self.add_result(result)
    
    async def run_all_audits(self):
        """Run all audit checks."""
        print("\n" + "="*60)
        print("🏯 YUKIO COMPREHENSIVE AUDIT")
        print("="*60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        await self.audit_environment()
        await self.audit_ollama()
        await self.audit_dependencies()
        await self.audit_database()
        await self.audit_data_files()
        await self.audit_ingestion_pipeline()
        await self.audit_agent()
        await self.audit_api()
        
        # Summary
        print("\n" + "="*60)
        print("📊 AUDIT SUMMARY")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        print(f"Total Checks: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print("\n❌ Failed Checks:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.name}: {result.message}")
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details
                }
                for r in self.results
            ]
        }


async def main():
    """Main entry point."""
    auditor = YukioAuditor()
    summary = await auditor.run_all_audits()
    
    # Save results
    output_file = Path(__file__).parent.parent / "audit_results.json"
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"\n📄 Full results saved to: {output_file}")
    
    # Exit code based on results
    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())


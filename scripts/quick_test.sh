#!/bin/bash
# Quick test script for Yukio ingestion system

echo "🏯 YUKIO - Quick Ingestion Test"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Ollama is running
echo "1️⃣  Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama is running${NC}"
else
    echo -e "${RED}❌ Ollama is not running${NC}"
    echo -e "${YELLOW}   Run: ollama serve${NC}"
    exit 1
fi

# Check if nomic-embed-text is available
echo ""
echo "2️⃣  Checking embedding model..."
if ollama list | grep -q "nomic-embed-text"; then
    echo -e "${GREEN}✅ nomic-embed-text is available${NC}"
else
    echo -e "${RED}❌ nomic-embed-text not found${NC}"
    echo -e "${YELLOW}   Run: ollama pull nomic-embed-text${NC}"
    exit 1
fi

# Check if markdown files exist
echo ""
echo "3️⃣  Checking for Japanese markdown files..."
if [ -d "data/japanese/markdown" ] && [ "$(ls -A data/japanese/markdown/*.md 2>/dev/null)" ]; then
    FILE_COUNT=$(ls -1 data/japanese/markdown/*.md 2>/dev/null | wc -l)
    echo -e "${GREEN}✅ Found $FILE_COUNT markdown files${NC}"
    ls data/japanese/markdown/*.md | head -5 | while read file; do
        echo "   - $(basename "$file")"
    done
    
    # Check if files have been cleaned
    echo ""
    echo "   💡 Tip: Clean markdown files before ingestion:"
    echo -e "   ${YELLOW}python scripts/clean_markdown.py --dry-run${NC}"
else
    echo -e "${RED}❌ No markdown files found in data/japanese/markdown${NC}"
    echo -e "${YELLOW}   Run: python scripts/convert_pdfs.py${NC}"
    exit 1
fi

# Run test script
echo ""
echo "4️⃣  Running system tests..."
python3 scripts/test_ingestion.py

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================"
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "Ready to run ingestion:"
    echo -e "${YELLOW}  python -m ingestion.ingest${NC}"
    echo ""
else
    echo ""
    echo "======================================"
    echo -e "${RED}❌ Some tests failed${NC}"
    echo "Please fix the issues above"
fi

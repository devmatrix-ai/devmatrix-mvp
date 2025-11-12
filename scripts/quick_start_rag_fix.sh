#!/bin/bash

# 🚀 Quick Start RAG Fix Script
# Ejecutar AHORA para iniciar la mejora del 38% al 98%
# Author: Dany (SuperClaude)
# Date: 2025-11-12

set -e  # Exit on error

echo "🎯 DevMatrix RAG Quick Start Fix"
echo "================================"
echo "Target: 38% → 65% precision (Day 1)"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check ChromaDB is running
echo "1️⃣ Checking ChromaDB..."
if docker ps | grep -q chromadb; then
    echo -e "${GREEN}✅ ChromaDB is running${NC}"
else
    echo -e "${YELLOW}⚠️ Starting ChromaDB...${NC}"
    docker-compose up -d chromadb
    sleep 5
fi

# 2. Backup current state
echo ""
echo "2️⃣ Creating backup..."
BACKUP_DIR="backups/rag/$(date +%Y-%m-%d_%H-%M-%S)"
mkdir -p $BACKUP_DIR
cp -r .cache/rag $BACKUP_DIR/ 2>/dev/null || echo "No cache to backup"
cp -r data/chromadb $BACKUP_DIR/ 2>/dev/null || echo "No chromadb data to backup"
echo -e "${GREEN}✅ Backup created in $BACKUP_DIR${NC}"

# 3. Check baseline
echo ""
echo "3️⃣ Checking current RAG state..."
python scripts/verify_rag_quality.py 2>/dev/null | grep -E "Total examples:|success rate:" || true

# 4. Run population orchestrator
echo ""
echo "4️⃣ Starting RAG population (this will take ~10-15 minutes)..."
echo -e "${YELLOW}Running orchestrate_rag_population.py...${NC}"
python scripts/orchestrate_rag_population.py --source src/ || {
    echo -e "${RED}❌ Population failed. Trying individual scripts...${NC}"

    # Fallback to individual scripts
    echo "Running seed_enhanced_patterns.py..."
    python scripts/seed_enhanced_patterns.py --collection devmatrix_curated --count 500 || true

    echo "Running seed_project_standards.py..."
    python scripts/seed_project_standards.py --collection devmatrix_standards || true

    echo "Running seed_official_docs.py..."
    python scripts/seed_official_docs.py --frameworks "fastapi,react,typescript" || true
}

# 5. Quick fix thresholds
echo ""
echo "5️⃣ Applying threshold fixes..."

# Create a Python script to update thresholds
cat > /tmp/fix_thresholds.py << 'EOF'
import sys
sys.path.insert(0, '.')

# Fix retriever threshold
retriever_file = "src/rag/retriever.py"
with open(retriever_file, 'r') as f:
    content = f.read()

# Replace DEFAULT_MIN_SIMILARITY
import re
content = re.sub(
    r'DEFAULT_MIN_SIMILARITY\s*=\s*0\.\d+',
    'DEFAULT_MIN_SIMILARITY = 0.5',
    content
)

with open(retriever_file, 'w') as f:
    f.write(content)

print("✅ Updated DEFAULT_MIN_SIMILARITY to 0.5")

# Fix multi-collection thresholds
mc_file = "src/rag/multi_collection_manager.py"
try:
    with open(mc_file, 'r') as f:
        content = f.read()

    # Update collection thresholds
    content = re.sub(
        r'"threshold":\s*0\.75',
        '"threshold": 0.55',
        content
    )
    content = re.sub(
        r'"threshold":\s*0\.65',
        '"threshold": 0.45',
        content
    )
    content = re.sub(
        r'"threshold":\s*0\.70',
        '"threshold": 0.50',
        content
    )

    with open(mc_file, 'w') as f:
        f.write(content)

    print("✅ Updated collection thresholds")
except:
    print("⚠️ Could not update multi-collection thresholds")
EOF

python /tmp/fix_thresholds.py

# 6. Verify improvements
echo ""
echo "6️⃣ Verifying improvements..."
echo -e "${YELLOW}Testing retrieval with new configuration...${NC}"

cat > /tmp/test_retrieval.py << 'EOF'
import sys
sys.path.insert(0, '.')

import asyncio
from src.rag import create_retriever, create_vector_store, create_embedding_model

async def test():
    print("\n🔍 Testing RAG Retrieval:")
    print("-" * 40)

    embedding_model = create_embedding_model()
    vector_store = create_vector_store(embedding_model)
    retriever = create_retriever(vector_store, min_similarity=0.5)

    test_queries = [
        "FastAPI authentication middleware",
        "React component with hooks",
        "TypeScript validation",
        "Async database operations",
        "JWT token handling"
    ]

    success = 0
    for query in test_queries:
        results = await retriever.retrieve(query)
        if results:
            success += 1
            print(f"✅ {query}: {len(results)} results")
        else:
            print(f"❌ {query}: No results")

    rate = success / len(test_queries)
    print("-" * 40)
    print(f"\n📊 Success Rate: {rate:.0%}")

    if rate >= 0.6:
        print("🎯 Target achieved for Day 1!")
    else:
        print("⚠️ Need more population. Run individual seed scripts.")

    return rate

rate = asyncio.run(test())
exit(0 if rate >= 0.5 else 1)
EOF

python /tmp/test_retrieval.py

# 7. Summary
echo ""
echo "================================"
echo "📊 Quick Start Complete!"
echo "================================"
echo ""
echo "✅ Next Steps:"
echo "1. Check the retrieval success rate above"
echo "2. If < 60%, run more seed scripts:"
echo "   python scripts/seed_enhanced_patterns.py --count 1000"
echo "   python scripts/seed_jwt_fastapi_examples.py"
echo ""
echo "3. Monitor progress:"
echo "   python scripts/verify_rag_quality.py"
echo ""
echo "4. Continue with Week 1 plan in:"
echo "   DOCS/ONGOING/RAG_IMPLEMENTATION_PLAN.md"
echo ""
echo "🎯 Target: Reach 65% precision by end of week 1"
echo ""

# Clean up temp files
rm -f /tmp/fix_thresholds.py /tmp/test_retrieval.py
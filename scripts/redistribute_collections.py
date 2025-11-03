#!/usr/bin/env python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import create_embedding_model
from src.rag.vector_store import VectorStore
from src.observability import get_logger

logger = get_logger("redistribute_collections")

def determine_collection(metadata):
    if not metadata:
        return "curated"
    source = str(metadata.get("source", "")).lower()
    category = str(metadata.get("category", "")).lower()
    if "standard" in source or "standard" in category or "contrib" in source:
        return "standards"
    elif "project" in source:
        return "project"
    else:
        return "curated"

def migrate():
    print("\n" + "="*80)
    print("COLLECTION REDISTRIBUTION")
    print("="*80)
    
    try:
        embedding_model = create_embedding_model()
        
        original_store = VectorStore(embedding_model, collection_name="devmatrix_code_examples")
        curated_store = VectorStore(embedding_model, collection_name="devmatrix_curated")
        project_store = VectorStore(embedding_model, collection_name="devmatrix_project_code")
        standards_store = VectorStore(embedding_model, collection_name="devmatrix_standards")
        
        logger.info("Fetching examples...")
        all_data = original_store.collection.get(include=['documents', 'metadatas'])
        
        if not all_data or not all_data.get('ids'):
            logger.warning("No examples found!")
            return False
        
        ids = all_data['ids']
        documents = all_data['documents']
        metadatas = all_data['metadatas']
        total = len(ids)
        logger.info(f"Found {total} examples")
        
        # Categorize
        data = {"curated": [], "project": [], "standards": []}
        
        print(f"\n📊 Categorizing {total} examples...")
        for i, (id_, doc, meta) in enumerate(zip(ids, documents, metadatas), 1):
            cat = determine_collection(meta)
            data[cat].append((doc, meta, id_))
            if i % 500 == 0:
                print(f"  {i}/{total}...")
        
        # Add to new collections
        print("\n✅ Adding to new collections...")
        
        if data["curated"]:
            codes = [c[0] for c in data["curated"]]
            metas = [c[1] for c in data["curated"]]
            ids_list = [c[2] for c in data["curated"]]
            curated_store.add_batch(codes=codes, metadatas=metas, example_ids=ids_list)
            print(f"  ✓ {len(codes)} → devmatrix_curated")
        
        if data["project"]:
            codes = [c[0] for c in data["project"]]
            metas = [c[1] for c in data["project"]]
            ids_list = [c[2] for c in data["project"]]
            project_store.add_batch(codes=codes, metadatas=metas, example_ids=ids_list)
            print(f"  ✓ {len(codes)} → devmatrix_project_code")
        
        if data["standards"]:
            codes = [c[0] for c in data["standards"]]
            metas = [c[1] for c in data["standards"]]
            ids_list = [c[2] for c in data["standards"]]
            standards_store.add_batch(codes=codes, metadatas=metas, example_ids=ids_list)
            print(f"  ✓ {len(codes)} → devmatrix_standards")
        
        # Verify
        print("\n📈 Verification...")
        c_final = curated_store.collection.count()
        p_final = project_store.collection.count()
        s_final = standards_store.collection.count()
        total_migrated = c_final + p_final + s_final
        
        print(f"  devmatrix_curated: {c_final}")
        print(f"  devmatrix_project_code: {p_final}")
        print(f"  devmatrix_standards: {s_final}")
        print(f"  ─────────────────────────────")
        print(f"  Total: {total_migrated}")
        
        if total_migrated == total:
            print(f"\n✅ SUCCESS: Migrated {total} examples!")
            return True
        else:
            print(f"\n⚠️  WARNING: Expected {total}, got {total_migrated}")
            return False
    
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)

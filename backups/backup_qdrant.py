#!/usr/bin/env python3
"""
Qdrant Hot Backup Script
Exports all collections to JSON without stopping the database
"""
import json
from datetime import datetime
from pathlib import Path

from qdrant_client import QdrantClient


def backup_qdrant():
    """Create a full backup of Qdrant collections"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("/home/kwar/code/agentic-ai/backups")

    client = QdrantClient(host='localhost', port=6333)

    print(f"🔄 Starting Qdrant backup...")

    # Get all collections
    collections = client.get_collections().collections
    print(f"📦 Found {len(collections)} collections")

    backup_data = {
        'metadata': {
            'timestamp': timestamp,
            'backup_date': datetime.now().isoformat(),
            'total_collections': len(collections),
        },
        'collections': {}
    }

    for collection in collections:
        collection_name = collection.name
        print(f"\n📂 Backing up collection: {collection_name}")

        # Get collection info
        collection_info = client.get_collection(collection_name)

        # Export all points
        points = []
        offset = None
        batch_size = 100
        total_exported = 0

        while True:
            result, next_offset = client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=True
            )

            if not result:
                break

            for point in result:
                points.append({
                    'id': str(point.id),
                    'vector': point.vector,
                    'payload': point.payload
                })

            total_exported += len(result)
            if total_exported % 1000 == 0:
                print(f"  ⏳ Exported {total_exported} points...")

            offset = next_offset
            if offset is None:
                break

        print(f"  ✅ Exported {len(points)} points from {collection_name}")

        backup_data['collections'][collection_name] = {
            'info': {
                'vectors_count': collection_info.vectors_count,
                'points_count': collection_info.points_count,
                'config': {
                    'params': {
                        'vectors': {
                            'size': collection_info.config.params.vectors.size,
                            'distance': collection_info.config.params.vectors.distance.value
                        }
                    }
                }
            },
            'points': points
        }

    # Write to file
    backup_file = backup_dir / f"qdrant_full_backup_{timestamp}.json"
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2, default=str)

    file_size = backup_file.stat().st_size / (1024 * 1024)  # MB

    print(f"\n✅ Qdrant backup completed successfully!")
    print(f"📁 File: {backup_file}")
    print(f"💾 Size: {file_size:.2f} MB")

    total_points = sum(len(col['points']) for col in backup_data['collections'].values())
    print(f"📊 Total points: {total_points}")

    for col_name, col_data in backup_data['collections'].items():
        print(f"  - {col_name}: {len(col_data['points'])} points")

    return backup_file


if __name__ == "__main__":
    backup_file = backup_qdrant()
    print(f"\n🎉 Backup guardado en: {backup_file}")

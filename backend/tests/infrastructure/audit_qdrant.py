import asyncio
import logging
import uuid
import time
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http import exceptions

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("qdrant_audit")

# Configurações do Ambiente
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333
AUDIT_COLLECTION = f"audit_temp_{int(time.time())}"

async def run_audit():
    client = AsyncQdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    log.info(f"Iniciando Auditoria: Cliente v1.17 vs Servidor v1.12")
    log.info(f"Coleção de Auditoria: {AUDIT_COLLECTION}")

    try:
        # 1. TESTE DE CONECTIVIDADE (REST/gRPC)
        log.info("--- Fase 1: Conectividade ---")
        collections = await client.get_collections()
        log.info(f"Conectividade OK. Coleções existentes: {len(collections.collections)}")
        
        # 2. TESTE DE CRIAÇÃO (SCHEMA DRIFT)
        log.info("--- Fase 2: Criação de Coleção Híbrida ---")
        await client.create_collection(
            collection_name=AUDIT_COLLECTION,
            vectors_config={
                "dense": models.VectorParams(size=4, distance=models.Distance.COSINE)
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=False)
                )
            }
        )
        log.info("Criação de coleção: SUCCESS")

        # 3. TESTE DE UPSERT (SILENT DATA CORRUPTION PROBE)
        log.info("--- Fase 3: Upsert & SDC Probe ---")
        test_points = [
            models.PointStruct(
                id=1,
                vector={
                    "dense": [0.1, 0.2, 0.3, 0.4],
                    "sparse": models.SparseVector(indices=[10, 100, 1000], values=[0.5, 0.3, 0.9])
                },
                payload={"tag": "audit", "meta": {"nested": True, "val": 42}}
            ),
            models.PointStruct(
                id=2,
                vector={
                    "dense": [0.9, 0.8, 0.7, 0.6],
                    "sparse": models.SparseVector(indices=[], values=[]) # Edge case: empty sparse
                },
                payload={"tag": "audit", "meta": {"nested": False}}
            )
        ]
        await client.upsert(collection_name=AUDIT_COLLECTION, points=test_points, wait=True)
        log.info("Upsert híbrico: SUCCESS")

        # 4. TESTE DE BUSCA VIA UQA (SUBSTITUIÇÃO DO SEARCH Legacy)
        log.info("--- Fase 4: Busca via Universal Query API (Substituindo Search) ---")
        uqa_search = await client.query_points(
            collection_name=AUDIT_COLLECTION,
            query=[0.1, 0.2, 0.3, 0.4],
            using="dense",
            limit=1
        )
        if uqa_search and len(uqa_search.points) > 0 and uqa_search.points[0].id == 1:
            log.info("Busca UQA (Replacement): SUCCESS")
        else:
            log.error(f"Busca UQA (Replacement): FAILED (Result: {uqa_search})")

        # 5. TESTE DE BUSCA COM PREFETCH (FILTRO INTEGRADO)
        log.info("--- Fase 5: UQA with Prefetch & Filter ---")
        try:
            uqa_search = await client.query_points(
                collection_name=AUDIT_COLLECTION,
                query=[0.1, 0.2, 0.3, 0.4],
                using="dense",
                limit=1
            )
            log.info("UQA Simple Search: SUCCESS")
        except Exception as e:
            log.error(f"UQA Simple Search: FAILED (Incompatibilidade provável): {e}")

        # 6. TESTE DE FUSION (RRF / Prefetch) - GARGALO CRÍTICO
        log.info("--- Fase 6: Fusion RRF & Prefetch ---")
        try:
            fusion_search = await client.query_points(
                collection_name=AUDIT_COLLECTION,
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                prefetch=[
                    models.Prefetch(query=[0.1, 0.2, 0.3, 0.4], using="dense", limit=2),
                    models.Prefetch(
                        query=models.SparseVector(indices=[10], values=[1.0]),
                        using="sparse",
                        limit=2
                    )
                ],
                limit=2
            )
            log.info("Fusion RRF: SUCCESS")
        except Exception as e:
            log.error(f"Fusion RRF: FAILED (Check gRPC Protocol Drift): {e}")

        # 7. TESTE DE FILTROS ANINHADOS (OPTIMIZER STRESS)
        log.info("--- Fase 7: Complex Filters Stress ---")
        try:
            filter_search = await client.query_points(
                collection_name=AUDIT_COLLECTION,
                query=[0.1, 0.2, 0.3, 0.4],
                using="dense",
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(key="tag", match=models.MatchValue(value="audit")),
                        models.Filter(
                            should=[
                                models.FieldCondition(key="meta.val", match=models.MatchValue(value=42)),
                                models.FieldCondition(key="meta.nested", match=models.MatchValue(value=True))
                            ]
                        )
                    ]
                ),
                limit=1
            )
            log.info("Nested Filters (UQA): SUCCESS")
        except Exception as e:
            log.error(f"Nested Filters (UQA): FAILED: {e}")

        # 8. VERIFICAÇÃO DE SDC (ESTADO DO SERVIDOR)
        log.info("--- Fase 8: SDC Verification ---")
        point = await client.retrieve(collection_name=AUDIT_COLLECTION, ids=[1], with_vectors=True)
        if point:
            v_sparse = point[0].vector.get("sparse")
            if v_sparse and v_sparse.indices == [10, 100, 1000]:
                log.info("SDC Check (Sparse Indices): PASSED")
            else:
                log.error(f"SDC Check (Sparse Indices): FAILED bit-drift detected! indices={v_sparse.indices if v_sparse else 'None'}")
        
    except Exception as e:
        log.critical(f"Erro fatal na auditoria: {e}", exc_info=True)
    finally:
        # Cleanup
        try:
            await client.delete_collection(AUDIT_COLLECTION)
            log.info(f"Limpeza concluída: {AUDIT_COLLECTION} removida.")
        except Exception as e:
            log.warning(f"Falha ao limpar coleção {AUDIT_COLLECTION}: {e}")

if __name__ == "__main__":
    asyncio.run(run_audit())

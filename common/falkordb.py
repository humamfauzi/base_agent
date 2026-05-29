from __future__ import annotations

from typing import Any


class FalkorDBToolkit:
    def __init__(
        self,
        host: str,
        port: int = 6379,
        graph_name: str = "default",
        password: str | None = None,
        username: str | None = None,
    ):
        try:
            from falkordb import FalkorDB
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "The falkordb package is required. Install it with `uv add FalkorDB`."
            ) from exc

        self.host = host
        self.port = port
        self.graph_name = graph_name
        self._client = FalkorDB(
            host=host,
            port=port,
            password=password,
            username=username,
        )
        self._graph = self._client.select_graph(graph_name)

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        if isinstance(value, list):
            return [FalkorDBToolkit._serialize_value(item) for item in value]

        if isinstance(value, tuple):
            return [FalkorDBToolkit._serialize_value(item) for item in value]

        if isinstance(value, dict):
            return {
                key: FalkorDBToolkit._serialize_value(item)
                for key, item in value.items()
            }

        if hasattr(value, "labels") and hasattr(value, "properties"):
            return {
                "id": getattr(value, "id", None),
                "labels": list(value.labels),
                "properties": dict(value.properties),
            }

        if hasattr(value, "src_node") and hasattr(value, "dest_node"):
            return {
                "id": getattr(value, "id", None),
                "relationship": getattr(value, "relation", None),
                "src_node": FalkorDBToolkit._serialize_value(value.src_node),
                "dest_node": FalkorDBToolkit._serialize_value(value.dest_node),
                "properties": dict(getattr(value, "properties", {})),
            }

        if hasattr(value, "nodes") and hasattr(value, "edges"):
            return {
                "nodes": FalkorDBToolkit._serialize_value(list(value.nodes())),
                "edges": FalkorDBToolkit._serialize_value(list(value.edges())),
            }

        return value

    @staticmethod
    def _normalize_query_result(result: Any) -> dict[str, Any]:
        headers = [column[1] for column in result.header]
        rows = [
            [FalkorDBToolkit._serialize_value(value) for value in row]
            for row in result.result_set
        ]

        return {
            "graph": None,
            "header": headers,
            "rows": rows,
            "stats": {
                "cached_execution": result.cached_execution,
                "labels_added": result.labels_added,
                "labels_removed": result.labels_removed,
                "nodes_created": result.nodes_created,
                "nodes_deleted": result.nodes_deleted,
                "properties_set": result.properties_set,
                "properties_removed": result.properties_removed,
                "relationships_created": result.relationships_created,
                "relationships_deleted": result.relationships_deleted,
                "indices_created": result.indices_created,
                "indices_deleted": result.indices_deleted,
                "run_time_ms": result.run_time_ms,
            },
        }

    def store(self, query: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self._graph.query(q=query, params=params)
        normalized = self._normalize_query_result(result)
        normalized["graph"] = self.graph_name
        return normalized

    def retrieve(self, query: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self._graph.ro_query(q=query, params=params)
        normalized = self._normalize_query_result(result)
        normalized["graph"] = self.graph_name
        return normalized

    def close(self) -> None:
        self._client.close()
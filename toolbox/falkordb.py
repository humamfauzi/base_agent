import json
from typing import Any, List

from common.falkordb import FalkorDBToolkit
from structs.tool import (
    Tool,
    Type,
    Function,
    Parameters,
    ParameterType,
    Properties,
    InputType,
)


def _parse_params(params: str | None) -> dict[str, Any] | None:
    if params is None:
        return None

    if isinstance(params, dict):
        return params

    parsed = json.loads(params)
    if not isinstance(parsed, dict):
        raise ValueError("params must be a JSON object string")

    return parsed


class Store:
    def __init__(self, toolkit: FalkorDBToolkit):
        self.toolkit = toolkit

    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="store_in_falkordb",
                description="Execute a write Cypher query against the configured FalkorDB graph. Use this for CREATE, MERGE, SET, DELETE, and other mutating graph operations.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "query": Properties(
                            type=InputType.String,
                            description="The Cypher write query to execute.",
                        ),
                        "params": Properties(
                            type=InputType.String,
                            description="Optional JSON object string containing Cypher query parameters.",
                        ),
                    },
                    required=["query"],
                ),
            ),
        )

    def execute(self, query: str, params: str | None = None):
        return self.toolkit.store(query=query, params=_parse_params(params))


class Retrieve:
    def __init__(self, toolkit: FalkorDBToolkit):
        self.toolkit = toolkit

    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="retrieve_from_falkordb",
                description="Execute a read-only Cypher query against the configured FalkorDB graph and return normalized rows and query statistics.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "query": Properties(
                            type=InputType.String,
                            description="The Cypher read query to execute.",
                        ),
                        "params": Properties(
                            type=InputType.String,
                            description="Optional JSON object string containing Cypher query parameters.",
                        ),
                    },
                    required=["query"],
                ),
            ),
        )

    def execute(self, query: str, params: str | None = None):
        return self.toolkit.retrieve(query=query, params=_parse_params(params))


class FalkorDB:
    def __init__(
        self,
        host: str,
        port: int = 6379,
        graph_name: str = "default",
        password: str | None = None,
        username: str | None = None,
    ):
        self.toolkit = FalkorDBToolkit(
            host=host,
            port=port,
            graph_name=graph_name,
            password=password,
            username=username,
        )
        self.store = Store(self.toolkit)
        self.retrieve = Retrieve(self.toolkit)

    def get_all_tools(self) -> List[Tool]:
        return [
            self.store.get_tool_manifest(),
            self.retrieve.get_tool_manifest(),
        ]

    def tool_map(self):
        return {
            "store_in_falkordb": self.store.execute,
            "retrieve_from_falkordb": self.retrieve.execute,
        }
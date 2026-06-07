import json
from collections import defaultdict
from typing import List
from common.worker import spawn_workers
from structs.tool import (
    Tool,
    Type,
    Function,
    Parameters,
    ParameterType,
    Properties,
    InputType,
)
from toolbox.file_manager import FileManager
from toolbox.falkordb import FalkorDB as ToolFalkorDB
from toolbox.semantic import Semantic as ToolSemantic, SupportedProvider


class Parser:
    def __init__(self, api_key):
        self.api_key = api_key
        self.semtools = ToolSemantic(SupportedProvider.DEEPSEEK, self.api_key)
        self.falkordb_tools = ToolFalkorDB(host="localhost", port=6379, graph_name="default")
        self.file_manager = FileManager()
        pass

    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="parser",
                description="Given a file path and max token, it will chunk the file to the max token and loop to parse it one by one",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "file_path": Properties(
                            type=InputType.String,
                            description="the file path to parse relationships from",
                        ),
                        "max_tokens": Properties(
                            type=InputType.Integer,
                            description="the maximum number of tokens to process at a time",
                        )
                    },
                    required=["file_path", "max_tokens"],
                ),
            ),
        )

    def execute(self, file_path: str, max_tokens: int = 1000):
        """
        retrieve the text and parse the relationships between entities
        """
        file_tools = self.file_manager.tool_map()
        semantic_tools = self.semtools.tool_map()
        read_plan = file_tools["get_total_divisions"](
            file_path=file_path,
            max_tokens=max_tokens,
        )

        parsed_divisions = 0
        extracted_relationships = 0
        created_relationships = 0

        def fn(division):
            nonlocal parsed_divisions, extracted_relationships, created_relationships
            content = file_tools["read_file"](**division)
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="ignore")
            translated_content = semantic_tools["translator"](
                fromm="id",
                to="en",
                content=content
            )

            relationships = semantic_tools["relationship_extraction"](translated_content)

            extracted_relationships += len(relationships)
            created_relationships += self._store_relationships(relationships)
            parsed_divisions += 1


        spawn_workers(12, read_plan, fn)

        return {
            "status": "success",
            "message": f"Parsed relationships from {file_path} and stored in FalkorDB.",
            "parsed_divisions": parsed_divisions,
            "extracted_relationships": extracted_relationships,
            "created_relationships": created_relationships,
        }

    def _store_relationships(self, relationships):
        if not relationships:
            return 0

        grouped_relationships = defaultdict(list)
        for relationship in relationships:
            if not isinstance(relationship, dict):
                continue

            entity1 = relationship.get("entity1")
            entity2 = relationship.get("entity2")
            relationship_type = relationship.get("relationship")
            if not entity1 or not entity2 or not relationship_type:
                continue

            escaped_relationship_type = str(relationship_type).replace("`", "``").strip()
            if not escaped_relationship_type:
                continue

            grouped_relationships[escaped_relationship_type].append(
                {
                    "entity1": str(entity1),
                    "entity2": str(entity2),
                }
            )

        if not grouped_relationships:
            return 0

        relationships_created_total = 0
        for relationship_type, relationship_batch in grouped_relationships.items():
            store_query = f"""
                UNWIND $relationships AS rel
                MERGE (source:Entity {{name: rel.entity1}})
                MERGE (target:Entity {{name: rel.entity2}})
                MERGE (source)-[:`{relationship_type}`]->(target)
            """

            store_result = self.falkordb_tools.tool_map()["store_in_falkordb"](
                query=store_query,
                params=json.dumps({"relationships": relationship_batch}),
            )

            if isinstance(store_result, dict):
                stats = store_result.get("stats", {})
                if isinstance(stats, dict):
                    relationships_created = stats.get("relationships_created")
                    if isinstance(relationships_created, int):
                        relationships_created_total += relationships_created
                        continue

            relationships_created_total += len(relationship_batch)

        return relationships_created_total


class ParseRelationship:
    def __init__(self, api_key):
        self.parser = Parser(api_key=api_key)

    def get_all_tools(self) -> List[Tool]:
        return [
            self.parser.get_tool_manifest(),
        ]

    def tool_map(self):
        return {
            "parser": self.parser.execute
        }
from typing import List
from common.llm import LLMToolkit
from structs.tool import (
    Tool,
    Type,
    Function,
    Parameters,
    ParameterType,
    Properties,
    InputType,
)


class RelationshipExtraction:
    def __init__(self, toolkit: LLMToolkit):
        self.toolkit = toolkit

    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="relationship_extraction",
                description="Extract relationships between entities mentioned in the user query. Return a list of relationships, where each relationship is represented as a dictionary with 'entity1', 'entity2', and 'relationship' keys.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "content": Properties(
                            type=InputType.String,
                            description="The user query from which to extract relationships.",
                        )
                    },
                    required=["content"],
                ),
            ),
        )

    def execute(self, content: str):
        return self.toolkit.relationship_extraction(content)


class ParagraphExtractor:
    def __init__(self, toolkit: LLMToolkit):
        self.toolkit = toolkit

    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="paragraph_extractor",
                description="Extract paragraphs from the user query. Return a list of paragraphs, where each paragraph is a string.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "content": Properties(
                            type=InputType.String,
                            description="The user query from which to extract paragraphs.",
                        )
                    },
                    required=["content"],
                ),
            ),
        )

    def execute(self, content: str):
        return self.toolkit.paragraph_extractor(content)


class Semantic:
    def __init__(self, provider, api_key):
        from common.llm import SupportedProvider
        
        if provider not in SupportedProvider:
            raise ValueError(f"Unsupported provider: {provider}")
        self.toolkit = LLMToolkit(provider, api_key)
        self.relationship_extraction = RelationshipExtraction(self.toolkit)
        self.paragraph_extractor = ParagraphExtractor(self.toolkit)

    def get_all_tools(self) -> List[Tool]:
        return [
            self.relationship_extraction.get_tool_manifest(),
            self.paragraph_extractor.get_tool_manifest(),
        ]

    def tool_map(self):
        return {
            "relationship_extraction": self.relationship_extraction.execute,
            "paragraph_extractor": self.paragraph_extractor.execute,
        }

import json
from typing import List
from common.llm import LLMToolkit
from structs.chat import ChatResponse
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
        response = self.toolkit.relationship_extraction(content)
        return self._compose_relationships(response)

    @staticmethod
    def _compose_relationships(response):
        if hasattr(response, "json"):
            response_json = response.json()
        elif isinstance(response, dict):
            response_json = response
        elif isinstance(response, list):
            return [item for item in response if isinstance(item, dict)]
        else:
            return []

        if not isinstance(response_json, dict):
            return []

        choices = response_json.get("choices", [])
        if not choices:
            return []

        message = choices[0].get("message", {})
        content = message.get("content", "")
        if not isinstance(content, str):
            return []

        cleaned_content = content.strip()
        if cleaned_content.startswith("```"):
            cleaned_lines = cleaned_content.splitlines()
            if len(cleaned_lines) >= 2:
                cleaned_content = "\n".join(cleaned_lines[1:-1])

        try:
            parsed = json.loads(cleaned_content)
        except json.JSONDecodeError:
            return []

        if isinstance(parsed, dict):
            parsed = parsed.get("relationships", [])

        if not isinstance(parsed, list):
            return []

        relationships = []
        for item in parsed:
            if not isinstance(item, dict):
                continue

            entity1 = item.get("entity1")
            entity2 = item.get("entity2")
            relationship = item.get("relationship")

            if entity1 is None or entity2 is None or relationship is None:
                continue

            relationships.append(
                {
                    "entity1": str(entity1),
                    "entity2": str(entity2),
                    "relationship": str(relationship),
                }
            )

        return relationships


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

class Untangler:
    def __init__(self, toolkit: LLMToolkit):
        self.toolkit = toolkit

    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="untangler",
                description="Some text here maybe jumbled e.g. missing characters, doesnt have spaces, numbered in weird place. Untangle the text and return the corrected version. Use markdown format",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "content": Properties(
                            type=InputType.String,
                            description="The string user query to untangle.",
                        )
                    },
                    required=["content"],
                ),
            ),
        )

    def execute(self, content: str):
        return self.toolkit.untangler(content)

class Translator:
    def __init__(self, toolkit: LLMToolkit):
        self.toolkit = toolkit

    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="translator",
                description="Translate the given text from one language to another. The user query will specify the source language, target language, and the text to be translated. Return the translated text.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "from": Properties(
                            type=InputType.String,
                            description="The source language of the text to be translated.",
                        ),
                        "to": Properties(
                            type=InputType.String,
                            description="The target language to which the text should be translated.",
                        ),
                        "content": Properties(
                            type=InputType.String,
                            description="The user query specifying the source language, target language, and the text to be translated.",
                        )
                    },
                    required=["from", "to", "content"],
                ),
            ),
        )

    def execute(self, fromm:str, to: str, content: str) -> str:
        result = self.toolkit.translate(fromm, to, content)
        response = ChatResponse.parse(result.json())
        return response.get_first_message().content


from common.llm import SupportedProvider
class Semantic:
    def __init__(self, provider, api_key):
        
        if provider not in SupportedProvider:
            raise ValueError(f"Unsupported provider: {provider}")
        self.toolkit = LLMToolkit(provider, api_key)
        self.relationship_extraction = RelationshipExtraction(self.toolkit)
        self.paragraph_extractor = ParagraphExtractor(self.toolkit)
        self.untangler = Untangler(self.toolkit)
        self.translator = Translator(self.toolkit)
    def get_all_tools(self) -> List[Tool]:
        return [
            self.relationship_extraction.get_tool_manifest(),
            self.paragraph_extractor.get_tool_manifest(),
            self.untangler.get_tool_manifest(),
            self.translator.get_tool_manifest(),
        ]

    def tool_map(self):
        return {
            "relationship_extraction": self.relationship_extraction.execute,
            "paragraph_extractor": self.paragraph_extractor.execute,
            "untangler": self.untangler.execute,
            "translator": self.translator.execute,
        }

from enum import Enum
import time
from common.http import make_http_request
from structs.chat import ChatRequest, Message, Role, ThinkingOption, ReasoningLevel, Model, ChatResponse, FinishReason


class SupportedProvider(Enum):
    DEEPSEEK = "deepseek"

class LLMToolkit:
    def __init__(self, provider: SupportedProvider, api_key: str):
        self.provider = provider
        if self.provider == SupportedProvider.DEEPSEEK:
            self.base_url = "https://api.deepseek.com"
            self.chat_completions_endpoint = f"{self.base_url}/chat/completions"
            self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def relationship_extraction(self, content: str):
        """
            Non contextual relationship extraction using LLM. This is a simple example of how to use LLM for relationship extraction, and can be further improved by providing more detailed instructions in the system prompt, or by using few-shot examples. 
        """
        system_content = """
            You are a helpful assistant that extracts relationships between entities mentioned in the user query. You should return a list of relationships, where each relationship is represented as a dictionary with 'entity1', 'entity2', and 'relationship' keys. 
            For example, if the user query is "Alice is Bob's sister and works at Acme Corp.", you should return: [{"entity1": "Alice", "entity2": "Bob", "relationship": "sister"}, {"entity1": "Alice", "entity2": "Acme Corp.", "relationship": "works at"}]
        """
        chat_request = ChatRequest(
          model=Model.DeepseekV4Flash,
          messages=[
            Message(role=Role.System, content=system_content),
            Message(role=Role.User, content=content),
          ],
          thinking=ThinkingOption(type="enabled"),
          reasoning_effort=ReasoningLevel.High,
          stream=False,
          tools=[]
        )
        start = time.time()
        result = make_http_request(
            method="POST",
            url=self.chat_completions_endpoint,
            headers=self.headers,
            data=chat_request.to_json())
        end = time.time()
        print(f"""Time taken for relationship extraction: {end - start:.2f} seconds""")
        return result

    def paragraph_extractor(self, content: str):
        """
            This is an example of using LLM to extract paragraphs from a given text. The system prompt instructs the LLM to return a list of paragraphs, where each paragraph is a string. The user content is the text from which we want to extract paragraphs. The LLM will return a list of paragraphs extracted from the input text.
        """
        system_content = """
            You are a helpful assistant that extracts paragraphs from the user query. You should return a list of paragraphs, where each paragraph is a string. A paragraph is defined as a group of sentences that are related to each other and discuss a single topic. 
        """
        chat_request = ChatRequest(
          model=Model.DeepseekV4Flash,
          messages=[
            Message(role=Role.System, content=system_content),
            Message(role=Role.User, content=content),
          ],
          thinking=ThinkingOption(type="enabled"),
          reasoning_effort=ReasoningLevel.Low,
          stream=False,
          tools=[]
        )

        start = time.time()
        result = make_http_request(
            method="POST",
            url=self.chat_completions_endpoint,
            headers=self.headers,
            data=chat_request.to_json())
        end = time.time()
        print(f"""Time taken for paragraph extraction: {end - start:.2f} seconds""")
        return result

    def untangler(self, content: str):
        """
            This is an example of using LLM to untangle complex sentences from a given text.
            The system prompt instructs the LLM to return a list of simpler sentences that convey the same meaning as the original complex sentence. 
            The user content is the complex sentence that we want to untangle. 
            The LLM will return a list of simpler sentences that are easier to understand.
        """
        system_content = """
            You are an expert text-restoration assistant. Your sole task is to repair text that has had its spacing corrupted, merged, or stripped out (often called "jumbled" or "untangled" text).

        """
        user_content = f"""
            Review the input text and insert spaces where they logically and grammatically belong to make it perfectly readable English.

            Strict Rules:
            1. Do NOT alter, add, or omit any words.
            2. Preserve all original punctuation (commas, periods, colons, parentheses, hyphens).
            3. Preserve original paragraph breaks if any exist.
            4. Correct ONLY the spacing errors. Do not attempt to "fix" slang, grammar, or author style.
            5. Output ONLY the repaired text. Do not include any introductory remarks, explanations, or markdown code blocks.
            6. Use markdown formatting for the output, ensuring that all sentences are properly spaced and formatted for readability.
            7. If the input text is not jumbled and is already perfectly readable, simply return it as is without any modifications.

            Input Text:
            Here is the text to untangle:
            {content}

            Please return the untangled text in markdown format, ensuring that all sentences are properly spaced and formatted for readability.
        """
        chat_request = ChatRequest(
          model=Model.DeepseekV4Flash,
          messages=[
            Message(role=Role.System, content=system_content),
            Message(role=Role.User, content=user_content),
          ],
          thinking=ThinkingOption(type="enabled"),
          reasoning_effort=ReasoningLevel.Medium,
          stream=False,
          tools=[]
        )

        start = time.time()
        result = make_http_request(
            method="POST",
            url=self.chat_completions_endpoint,
            headers=self.headers,
            data=chat_request.to_json())
        end = time.time()
        print(f"""Time taken for untangling: {end - start:.2f} seconds""")
        return result

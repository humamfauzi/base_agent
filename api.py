import os
import time
from typing import Any
from dotenv import load_dotenv
from structs.chat import ChatRequest, Message, Role, ThinkingOption, ReasoningLevel, Model, ChatResponse, FinishReason
from structs.tool import (Tool, 
    Type as ToolType, 
    Function as ToolFunction, 
    Parameters as ToolParameters, 
    ParameterType, 
    InputType, 
    Properties as ToolProperties
)
from common.http import make_http_request
from common.llm import SupportedProvider
from toolbox import SQLite, DocumentParser, FileManager, Semantic as ToolSemantic, FalkorDB as ToolFalkorDB
from toolbox.file_manager import ReadFolder
from performer.parse_relationship import ParseRelationship as ToolParseRelationship
import json

class DeepseekAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com"
        self.chat_completions_endpoint = f"{self.base_url}/chat/completions"
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    @staticmethod
    def _serialize_tool_result(tool_result: Any) -> str:
        if isinstance(tool_result, bytes):
            return tool_result.decode("utf-8", errors="replace")

        if isinstance(tool_result, (dict, list, tuple, bool, int, float)) or tool_result is None:
            return json.dumps(tool_result)

        return str(tool_result)
  
    def quick_start(self):
        chat_request = ChatRequest(
          model=Model.DeepseekV4Flash,
          messages=[
            Message(role=Role.System, content="You are a helpful assistant."),
            Message(role=Role.User, content="What congruent means?"),
          ],
          thinking=ThinkingOption(type="enabled"),
          reasoning_effort=ReasoningLevel.Low,
          stream=False,
          tools=[]
        )

        result = make_http_request(
            method="POST",
            url=self.chat_completions_endpoint,
            headers=self.headers,
            data=chat_request.to_json())
        return result

    def multi_round(self):
        chat_request = ChatRequest(
          model=Model.DeepseekV4Flash,
          messages=[
            Message(role=Role.System, content="You are a helpful assistant."),
            Message(role=Role.User, content="What is the capital of France?"),
          ],
          thinking=ThinkingOption(type="enabled"),
          reasoning_effort=ReasoningLevel.Low,
          stream=False,
          tools=[]
        )

        result = make_http_request(
            method="POST",
            url=self.chat_completions_endpoint,
            headers=self.headers,
            data=chat_request.to_json())
    
        chat_response = ChatResponse.parse(result.json())
        print("Assistant:", chat_response.get_first_message().content)

        follow_up_request = ChatRequest(
            model=Model.DeepseekV4Flash,
            messages=[
              Message(role=Role.System, content="You are a helpful assistant."),
              Message(role=Role.User, content="What is the capital of France?"),
              Message(role=Role.Assistant, content=chat_response.get_first_message().content),
              Message(role=Role.User, content="And what about Germany?"),
            ],
            thinking=ThinkingOption(type="enabled"),
            reasoning_effort=ReasoningLevel.Low,
            stream=False,
            tools=[]
        )
        follow_up_result = make_http_request(
            method="POST",
            url=self.chat_completions_endpoint,
            headers=self.headers,
            data=follow_up_request.to_json()
        )
        follow_up_response = ChatResponse.parse(follow_up_result.json())
        print("Assistant:", follow_up_response.get_first_message().content)

    def tool_call(self):
        tool = Tool(
            type=ToolType.Function,
            function=ToolFunction(
                name="get_weather",
                description="get weather from a location. User should supply the location first",
                parameters=ToolParameters(
                    type=ParameterType.Object,
                    properties={
                        "location": ToolProperties(
                            type=InputType.String,
                            description="The location to get the weather for"
                        )
                    },
                    required=["location"]
                )
            )
        )
        chat_request = ChatRequest(
          model=Model.DeepseekV4Flash,
          messages=[
            Message(role=Role.System, content="You are a helpful assistant."),
            Message(role=Role.User, content="What is the weather in Nice, France?"),
          ],
          thinking=ThinkingOption(type="enabled"),
          reasoning_effort=ReasoningLevel.Low,
          stream=False,
          tools=[tool]
        )

        result = make_http_request(
            method="POST",
            url=self.chat_completions_endpoint,
            headers=self.headers,
            data=chat_request.to_json())
        print("response", json.dumps(result.json()))
        response = ChatResponse.parse(result.json())
        if response.get_stopped_reason() != FinishReason.ToolCalls:
            print("not calling any tools")
            return

        print("response:", response.get_first_message().tool_calls)

    def sqlite_tool_call(self):
        tool_definitions = SQLite.get_all_tools()
        messages=[
          Message(role=Role.System, content="You are a helpful assistant."),
          Message(role=Role.User, content="Create a database called test_db. Create user table with name, email, created at and updated at columns. Insert several instances. Show me all users in database."),
        ]
        chat_request = ChatRequest(
          model=Model.DeepseekV4Flash,
          messages=messages,
          thinking=ThinkingOption(type="enabled"),
          reasoning_effort=ReasoningLevel.Low,
          stream=False,
          tools=tool_definitions
        )
        tool_map = SQLite.tool_map()

        result = make_http_request(
            method="POST",
            url=self.chat_completions_endpoint,
            headers=self.headers,
            data=chat_request.to_json())
        response = ChatResponse.parse(result.json())

        while response.get_stopped_reason() == FinishReason.ToolCalls:
            assistant_message = response.get_first_message()
            messages.append(assistant_message)
            for tool_call in response.get_first_message().tool_calls:
                tool_result = tool_map[tool_call.function.name](**tool_call.function.arguments)
                messages.append(Message(role=Role.Tool, content=self._serialize_tool_result(tool_result), tool_call_id=tool_call.id))
        
            chat_request = ChatRequest(
                model=Model.DeepseekV4Flash,
                messages=messages,
                thinking=ThinkingOption(type="enabled"),
                reasoning_effort=ReasoningLevel.Low,
                stream=False,
                tools=tool_definitions
            )

            result = make_http_request(
                method="POST",
                url=self.chat_completions_endpoint,
                headers=self.headers,
                data=chat_request.to_json())
            response = ChatResponse.parse(result.json())
        
        print("Stopped Reason:", response.get_stopped_reason())
        print("Final response:", response.get_first_message().content)

    def pdf_parser(self):
        tool_definitions = [
            *DocumentParser.get_all_tools(),
            ReadFolder().get_tool_manifest(),
        ]
        tool_maps = {**DocumentParser.tool_map(), "read_folder": ReadFolder.execute}
        messages=[
          Message(role=Role.System, content="You are a helpful assistant."),
          Message(role=Role.User, content="""
            - check the artifacts folder
            - ensure the existance of PDF file.
            - use the read_document tool to parse the whole PDF file.
            - DO NOT read the pdf file and pass it as a message. only pass the directory.
            - Check the document type first. If it is full of text, then use the read_document tool. If it is scanned document, then use the read_document_ocr tool.
            - The read_document tool already saves the full parsed output as a markdown file with the same name and a .md extension.
            - Return only the saved file path and a short summary. Do not read the markdown content and pass it as a message.
            - Only choose the one that hasnt been parsed before. If all files already parsed, end process
            """),
        ]

        chat_request = ChatRequest(
          model=Model.DeepseekV4Flash,
          messages=messages,
          thinking=ThinkingOption(type="enabled"),
          reasoning_effort=ReasoningLevel.Low,
          stream=False,
          tools=tool_definitions
        )

        result = make_http_request(
            method="POST",
            url=self.chat_completions_endpoint,
            headers=self.headers,
            data=chat_request.to_json())
        response = ChatResponse.parse(result.json())
        while response.get_stopped_reason() == FinishReason.ToolCalls:
            assistant_message = response.get_first_message()
            messages.append(assistant_message)

            print("Tool call", [tool_call.function.name for tool_call in response.get_first_message().tool_calls])
            for tool_call in response.get_first_message().tool_calls:
                tool_result = tool_maps[tool_call.function.name](**tool_call.function.arguments)
                messages.append(Message(role=Role.Tool, content=self._serialize_tool_result(tool_result), tool_call_id=tool_call.id))
        
            chat_request = ChatRequest(
                model=Model.DeepseekV4Flash,
                messages=messages,
                thinking=ThinkingOption(type="enabled"),
                reasoning_effort=ReasoningLevel.Low,
                stream=False,
                tools=tool_definitions
            )

            result = make_http_request(
                method="POST",
                url=self.chat_completions_endpoint,
                headers=self.headers,
                data=chat_request.to_json())
            response = ChatResponse.parse(result.json())
        
        print("Stopped Reason:", response.get_stopped_reason())
        print("Final response:", response.get_first_message().content)


    def untangle_rolling(self):
        semtools = ToolSemantic(SupportedProvider.DEEPSEEK, self.api_key)
        tool_definitions = [*semtools.get_all_tools(), *FileManager.get_all_tools()]
        tool_maps = {**semtools.tool_map(), **FileManager.tool_map()}
        primary_command = """
           - Read the artifacts/lobsterarticle.md 
           - Chunk the article into a segemnted bytes based on the token limit. You can use 1000 tokens as a chunk size for safety.
           - For each chunk, call the entangler tools with the chunk content as input.
           - Once untangled, save the content in a markdown file in the same directory with the name lobsterarticle_untangled.md. If the file already exists, append to it.
           - Keep doing this until you finish the whole article. Do not read the whole article at once, only chunk by chunk.
        """
        messages=[
          Message(role=Role.System, content="You are a helpful assistant."),
          Message(role=Role.User, content=primary_command),
        ]

        start = time.time()

        chat_request = ChatRequest(
          model=Model.DeepseekV4Flash,
          messages=messages,
          thinking=ThinkingOption(type="enabled"),
          reasoning_effort=ReasoningLevel.Low,
          stream=False,
          tools=tool_definitions
        )

        result = make_http_request(
            method="POST",
            url=self.chat_completions_endpoint,
            headers=self.headers,
            data=chat_request.to_json())
        end = time.time()
        print(f"""Time taken for first response: {end - start:.2f} seconds. Contains {len(messages)} messages.""")
        response = ChatResponse.parse(result.json())
        while response.get_stopped_reason() == FinishReason.ToolCalls:
            assistant_message = response.get_first_message()
            messages.append(assistant_message)
            for tool_call in response.get_first_message().tool_calls:
                print("Tool call", tool_call.function.name, "with arguments", tool_call.function.arguments)
                tool_result = tool_maps[tool_call.function.name](**tool_call.function.arguments)
                messages.append(Message(role=Role.Tool, content=self._serialize_tool_result(tool_result), tool_call_id=tool_call.id))
        
            chat_request = ChatRequest(
                model=Model.DeepseekV4Flash,
                messages=messages,
                thinking=ThinkingOption(type="enabled"),
                reasoning_effort=ReasoningLevel.Low,
                stream=False,
                tools=tool_definitions
            )

            result = make_http_request(
                method="POST",
                url=self.chat_completions_endpoint,
                headers=self.headers,
                data=chat_request.to_json())
            response = ChatResponse.parse(result.json())
            end = time.time()
            print(f"""Time taken for response: {end - start:.2f} seconds. Contains {len(messages)} messages.""")
        
        print("Stopped Reason:", response.get_stopped_reason())
        print("Final response:", response.get_first_message().content)
        end = time.time()
        print(f"""Time taken final for response: {end - start:.2f} seconds. Contains {len(messages)} messages.""")

    def extract_markdown(self):
        semtools = ToolSemantic(SupportedProvider.DEEPSEEK, self.api_key)
        falkordb = ToolFalkorDB( host="localhost", port=6379, graph_name="default")
        tool_definitions = [*semtools.get_all_tools(), *FileManager.get_all_tools(), *falkordb.get_all_tools()]
        tool_maps = {**semtools.tool_map(), **FileManager.tool_map(), **falkordb.tool_map()}
        primary_command = """
            - check the folder artifacts and open bni_idx30. 
            - check the size of markdown file. If it is larger than 3000 tokens, read it in chunks. If not, read the whole content at once.
            - read the markdown content using 3000 tokens.
            - extract all paragraphs
            - establish a relation ship including
                - entities to entities
                - entities to number
                - entities to data
            - save the relationship in json format in the same folder under name relationship.json
            - save the extracted content in a graph database. you can use the falkordb for that.
            - once saved you can continue the roll.
            - keep the result message as small as possible but contain all necessary information
            - all relationship should be in lower case
        """
        messages=[
          Message(role=Role.System, content="You are a helpful financial assistant who posses expert knowledge in financial documents."),
          Message(role=Role.User, content=primary_command),
        ]

        start = time.time()

        chat_request = ChatRequest(
          model=Model.DeepseekV4Flash,
          messages=messages,
          thinking=ThinkingOption(type="enabled"),
          reasoning_effort=ReasoningLevel.Low,
          stream=False,
          tools=tool_definitions
        )

        result = make_http_request(
            method="POST",
            url=self.chat_completions_endpoint,
            headers=self.headers,
            data=chat_request.to_json())
        end = time.time()
        print(f"""Time taken for first response: {end - start} seconds. Contains {len(messages)} messages.""")
        response = ChatResponse.parse(result.json())
        while response.get_stopped_reason() == FinishReason.ToolCalls:
            assistant_message = response.get_first_message()
            messages.append(assistant_message)
            for tool_call in response.get_first_message().tool_calls:
                tool_result = tool_maps[tool_call.function.name](**tool_call.function.arguments)
                messages.append(Message(role=Role.Tool, content=self._serialize_tool_result(tool_result), tool_call_id=tool_call.id))
        
            chat_request = ChatRequest(
                model=Model.DeepseekV4Flash,
                messages=messages,
                thinking=ThinkingOption(type="enabled"),
                reasoning_effort=ReasoningLevel.Low,
                stream=False,
                tools=tool_definitions
            )

            result = make_http_request(
                method="POST",
                url=self.chat_completions_endpoint,
                headers=self.headers,
                data=chat_request.to_json())
            response = ChatResponse.parse(result.json())
            end = time.time()
            print({
                "time": f"{end - start:.2f} seconds",
                "message_count": len(messages),
                "tool_calls": [(tool_call.function.name, tool_call.function.arguments) for tool_call in response.get_first_message().tool_calls],
                "last_message": response.get_first_message().content
            })
        
        print("Stopped Reason:", response.get_stopped_reason())
        print("Final response:", response.get_first_message().content)
        end = time.time()
        print(f"""Time taken final for response: {end - start} seconds. Contains {len(messages)} messages.""")

    def performer_rolling_read(self):
        trp = ToolParseRelationship(self.api_key)
        tool_definitions = [*trp.get_all_tools(), *FileManager.get_all_tools()]
        tool_maps = {**trp.tool_map(), **FileManager.tool_map()}
        primary_command = """
            - read the fund md file inside artifacts folder
            - set the token limit to 3000 tokens. 
            - call the parser and wait for the result
            - report the result
        """
        messages=[
          Message(role=Role.System, content="You are archivist who is responsible for reading and extracting information from documents."),
          Message(role=Role.User, content=primary_command),
        ]

        start = time.time()
        chat_request = ChatRequest(
          model=Model.DeepseekV4Flash,
          messages=messages,
          thinking=ThinkingOption(type="enabled"),
          reasoning_effort=ReasoningLevel.Low,
          stream=False,
          tools=tool_definitions
        )

        result = make_http_request(
            method="POST",
            url=self.chat_completions_endpoint,
            headers=self.headers,
            data=chat_request.to_json())
        end = time.time()
        end = time.time()
        print(f"""Time taken for first response: {end - start} seconds. Contains {len(messages)} messages.""")
        response = ChatResponse.parse(result.json())
        while response.get_stopped_reason() == FinishReason.ToolCalls:
            assistant_message = response.get_first_message()
            messages.append(assistant_message)
            for tool_call in response.get_first_message().tool_calls:
                tool_result = tool_maps[tool_call.function.name](**tool_call.function.arguments)
                messages.append(Message(role=Role.Tool, content=self._serialize_tool_result(tool_result), tool_call_id=tool_call.id))
        
            chat_request = ChatRequest(
                model=Model.DeepseekV4Flash,
                messages=messages,
                thinking=ThinkingOption(type="enabled"),
                reasoning_effort=ReasoningLevel.Low,
                stream=False,
                tools=tool_definitions
            )

            result = make_http_request(
                method="POST",
                url=self.chat_completions_endpoint,
                headers=self.headers,
                data=chat_request.to_json())
            response = ChatResponse.parse(result.json())
            end = time.time()
            print({
                "time": f"{end - start:.2f} seconds",
                "message_count": len(messages),
                "tool_calls": [(tool_call.function.name, tool_call.function.arguments) for tool_call in response.get_first_message().tool_calls],
                "last_message": response.get_first_message().content
            })
        
        print("Stopped Reason:", response.get_stopped_reason())
        print("Final response:", response.get_first_message().content)
        end = time.time()
        print(f"""Time taken final for response: {end - start} seconds. Contains {len(messages)} messages.""")


if __name__ == "__main__":
    # Example usage
    load_dotenv()
    # print("Quickcheck", os.getenv("API_KEY")[:5])
    api = DeepseekAPI(os.getenv("DEEPSEEK_API"))
    api.performer_rolling_read()

    # quick_fn() 
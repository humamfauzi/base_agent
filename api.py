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
from toolbox import SQLite, DocumentParser, FileManager, Semantic as ToolSemantic, RelationshipExtraction, ParagraphExtractor
from toolbox.file_manager import ReadFolder
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

    def extract_markdown(self):
        semtools = ToolSemantic(SupportedProvider.DEEPSEEK, self.api_key)
        tool_definitions = [*semtools.get_all_tools(), *FileManager.get_all_tools()]
        tool_maps = {**semtools.tool_map(), **FileManager.tool_map()}
        primary_command = """
            - check the folder artifacts and read the markdown. 
            - Only read partially if the file is too long. 
            - Extract the paragraphs. 
            - Extract the relationships between entities mentioned in the markdown and extract the paragraphs. 
            - This includes the number and its units.
            - All relationship should be in one single word. 
            - Remove all relationship excess in parentheses. 
            - The final relationship should be in form of JSON. It has key of source, target and relationship.
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
            end = time.time()
            print(f"""Time taken for response: {end - start} seconds. Contains {len(messages)} messages.""")
        
        print("Stopped Reason:", response.get_stopped_reason())
        print("Final response:", response.get_first_message().content)
        end = time.time()
        print(f"""Time taken final for response: {end - start} seconds. Contains {len(messages)} messages.""")


def quick_fn():
    result = DocumentParser.tool_map()["read_document"]("artifacts/fund.pdf")
    with open("artifacts/fund.md", "w") as f:
        f.write(result)

if __name__ == "__main__":
    # Example usage
    load_dotenv()
    # print("Quickcheck", os.getenv("API_KEY")[:5])
    api = DeepseekAPI(os.getenv("DEEPSEEK_API"))
    api.pdf_parser()

    # quick_fn() 
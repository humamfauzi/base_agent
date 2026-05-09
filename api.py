import os
from dotenv import load_dotenv
from structs.chat import ChatRequest, Message, Role, ThinkingOption, ReasoningLevel, Model, ChatResponse, FinishReason
from structs.tool import Tool, Type as ToolType, Function as ToolFunction, Parameters as ToolParameters, ParameterType, InputType, Properties as ToolProperties
from common.http import make_http_request
import json

class DeepseekAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com"
        self.chat_completions_endpoint = f"{self.base_url}/chat/completions"
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
  
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

        # Now let's ask a follow-up question
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
            Message(role=Role.User, content="What is the weather in Nice,France?"),
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

if __name__ == "__main__":
    # Example usage
    load_dotenv()
    # api_key = normalize_api_key(os.getenv("DEEPSEEK_API"))
    api = DeepseekAPI(os.getenv("DEEPSEEK_API"))
    result = api.tool_call().json()

    
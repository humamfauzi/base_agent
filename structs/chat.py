from enum import Enum
from typing import List
from dataclasses import dataclass, field
from .tool import Tool, Call as TCall
import json

class Model(Enum):
  DeepseekV4Pro = "deepseek-v4-pro"
  DeepseekV4Flash = "deepseek-v4-flash"

  @staticmethod
  def from_str(model: str) -> "Model":
    for m in Model:
      if m.value == model:
        return m
    else:
      raise ValueError(f"Unknown model: {model}")

class Role(Enum):
    System = "system"
    User = "user"
    Assistant = "assistant"
    Tool = "tool"

    @staticmethod
    def from_str(label: str) -> "Role":
        for role in Role:
            if role.value == label:
                return role
        else:
            raise ValueError(f"Unknown role: {label}")

class ReasoningLevel(Enum):
  Low = "low"
  Medium = "medium"
  High = "high"

@dataclass
class Message:
    role: Role
    content: str
    tool_call_id: str = ""
    reasoning_content: str = ""
    tool_calls: List[TCall] = field(default_factory=list)

    @staticmethod
    def parse(json_data: dict) -> "Message":
        return Message(
            role=Role.from_str(json_data["role"]),
            content=json_data["content"],
            tool_call_id=json_data.get("tool_call_id", ""),
            reasoning_content=json_data.get("reasoning_content", ""),
            tool_calls=[TCall.parse(tool) for tool in json_data.get("tool_calls", [])]
        )

    def to_dict(self) -> dict:
        return {
            "role": self.role.value,
            "content": self.content,
            "tool_call_id": self.tool_call_id,
            "reasoning_content": self.reasoning_content,
            "tool_calls": [tool.to_dict() for tool in self.tool_calls]
        }

@dataclass
class ThinkingOption:
   type: str

@dataclass
class ChatRequest:
    model: Model
    messages: List[Message]
    thinking: ThinkingOption
    reasoning_effort: ReasoningLevel
    stream: bool
    tools: List[Tool]

    def to_json(self) -> str:
        return json.dumps({
            "model": self.model.value,
            "messages": [msg.to_dict() for msg in self.messages],
            "thinking": {"type": self.thinking.type},
            "reasoning_effort": self.reasoning_effort.value,
            "stream": self.stream,
            "tools": [tool.to_dict() for tool in self.tools],
        })


class Purpose(Enum):
    ChatCompletion = "chat.completion"
    @staticmethod
    def from_str(label: str):
        for purpose in Purpose:
            if purpose.value == label:
                return purpose
        else:
            raise ValueError(f"Unknown purpose: {label}")

class FinishReason(Enum):
    Stop = "stop"
    Length = "length"
    ContentFilter = "content_filter"
    ToolCalls = "tool_calls"

    @staticmethod
    def from_str(label: str):
        for reason in FinishReason:
            if reason.value == label:
                return reason
        else:
            raise ValueError(f"Unknown finish reason: {label}")

@dataclass
class ChatResponse:
    id: str
    object: str
    created: int
    model: str
    choices: List["Choice"]
    usage: "Usage"

    @staticmethod
    def parse(json_data: dict) -> "ChatResponse":
        return ChatResponse(
            id=json_data["id"],
            object=json_data["object"],
            created=json_data["created"],
            model=json_data["model"],
            choices=[Choice.parse(choice) for choice in json_data["choices"]],
            usage=Usage.parse(json_data["usage"])
        )
    
    def get_first_message(self) -> Message:
        if self.choices and len(self.choices) > 0:
            return self.choices[0].message
        else:
            raise ValueError("No choices available in the response")
    
    def get_stopped_reason(self) -> FinishReason:
        if self.choices and len(self.choices) > 0:
            return self.choices[0].finish_reason
        else:
            raise ValueError("No choices available in the response")

@dataclass
class Choice:
    index: int
    message: Message
    logprobs: dict
    finish_reason: FinishReason

    @staticmethod
    def parse(json_data: dict) -> "Choice":
        return Choice(
            index=json_data["index"],
            message=Message.parse(json_data["message"]),
            logprobs=json_data.get("logprobs"),
            finish_reason=FinishReason.from_str(json_data["finish_reason"])
        )

@dataclass
class PromptTokensDetails:
    cached_tokens: int

@dataclass
class CompletionTokensDetails:
    reasoning_tokens: int

@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_details: PromptTokensDetails
    completion_tokens_details: CompletionTokensDetails
    prompt_cache_hit_tokens: int
    prompt_cache_miss_tokens: int

    @staticmethod
    def parse(json_data: dict) -> "Usage":
        return Usage(
            prompt_tokens=json_data["prompt_tokens"],
            completion_tokens=json_data["completion_tokens"],
            total_tokens=json_data["total_tokens"],
            prompt_tokens_details=PromptTokensDetails(
                cached_tokens=json_data["prompt_tokens_details"]["cached_tokens"]
            ),
            completion_tokens_details=CompletionTokensDetails(
                reasoning_tokens=json_data["completion_tokens_details"]["reasoning_tokens"]
            ),
            prompt_cache_hit_tokens=json_data["prompt_cache_hit_tokens"],
            prompt_cache_miss_tokens=json_data["prompt_cache_miss_tokens"]
        )
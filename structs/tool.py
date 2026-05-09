from dataclasses import dataclass
from typing import List, Dict
from enum import Enum
import json

class Type(Enum):
    Function = "function"

class ParameterType(Enum):
    Object = "object"

class InputType(Enum):
    String = "string"

@dataclass
class Properties:
   type: InputType
   description: str

   def to_dict(self) -> dict:
       return {
           "type": self.type.value,
           "description": self.description
       }

@dataclass
class Parameters:
    type: ParameterType
    properties: Dict[str, Properties]
    required: List[str]

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "properties": { key: prop.to_dict() for key, prop in self.properties.items()},
            "required": self.required
        }

@dataclass
class Function:
    name: str
    description: str
    parameters: Parameters

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters.to_dict()
        }

@dataclass
class Tool:
    type: Type
    function: Function

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "function": self.function.to_dict()
        }

@dataclass
class FunctionCall:
    name: str
    arguments: dict

    @staticmethod
    def parse(map: dict) -> "FunctionCall":
        argument = map["arguments"]
        if type(argument) == str:
            argument = json.loads(argument)

        return FunctionCall(
            name=map["name"],
            arguments=argument,
        )

@dataclass
class Call:
    index: int
    id: str
    type: Type
    function: FunctionCall

    @staticmethod
    def parse(map: dict) -> "Call":
        return Call(
            index=map["index"],
            id=map["id"],
            type=Type(map["type"]),
            function=FunctionCall.parse(map["function"])
        )
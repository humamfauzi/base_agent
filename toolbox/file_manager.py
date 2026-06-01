import os
from typing import List
from structs.tool import (
    Tool,
    Type,
    Function,
    Parameters,
    ParameterType,
    Properties,
    InputType,
)


class SaveFile:
    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="save_file",
                description="Save content to a file at a specified path.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "file_path": Properties(
                            type=InputType.String,
                            description="The file path where the content should be saved.",
                        ),
                        "content": Properties(
                            type=InputType.String,
                            description="The content to save to the file.",
                        ),
                    },
                    required=["file_path", "content"],
                ),
            ),
        )
    
    @staticmethod
    def execute(file_path: str, content: str) -> str:
        with open(file_path, "w") as f:
            f.write(content)
        return f"Content saved to {file_path} successfully."

class SaveFileAppend:
    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="save_file_append",
                description="Append content to a file at a specified path. If the file does not exist, it will be created.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "file_path": Properties(
                            type=InputType.String,
                            description="The file path where the content should be appended.",
                        ),
                        "content": Properties(
                            type=InputType.String,
                            description="The content to append to the file.",
                        ),
                    },
                    required=["file_path", "content"],
                ),
            ),
        )
    
    @staticmethod
    def execute(file_path: str, content: str) -> str:
        with open(file_path, "a") as f:
            f.write(content)
        return f"Content appended to {file_path} successfully."


class ReadFolder:
    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="read_folder",
                description="List all files in a specified folder.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "folder_path": Properties(
                            type=InputType.String,
                            description="The path of the folder to read.",
                        )
                    },
                    required=["folder_path"],
                ),
            ),
        )
    
    @staticmethod
    def execute(folder_path: str) -> List[str]:
        if not os.path.exists(folder_path):
            raise ValueError("Folder does not exist")
        if not os.path.isdir(folder_path):
            raise ValueError("Provided path is not a folder")
        
        files = os.listdir(folder_path)
        return files


class ReadFile:
    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="read_file",
                description="Read the content of a file at a specified path. Also has option to specify max byte to read and offset to read from.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "file_path": Properties(
                            type=InputType.String,
                            description="The file path of the file to read.",
                        ),
                        "max_bytes": Properties(
                            type=InputType.Integer,
                            description="The maximum number of bytes to read from the file.",
                        ),
                        "offset": Properties(
                            type=InputType.Integer,
                            description="The byte offset from which to start reading.",
                        ),
                    },
                    required=["file_path"],
                ),
            ),
        )
    
    @staticmethod
    def execute(file_path: str, max_bytes: int = None, offset: int = 0 ) -> str:
        if not os.path.exists(file_path):
            raise ValueError("File does not exist")
        if not os.path.isfile(file_path):
            raise ValueError("Provided path is not a file")
        
        try:
            with open(file_path, "rb") as f:
                if offset:
                    f.seek(offset)
                if max_bytes:
                    content = f.read(max_bytes)
                else:
                    content = f.read()
            return content
        except Exception as e:
            raise ValueError(f"Error reading file: {str(e)} in file path {file_path}")

class TotalFilesBytes:
    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="total_files_bytes",
                description="Calculate the total size in bytes of a file.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "file_path": Properties(
                            type=InputType.String,
                            description="The path of the file to calculate total bytes for.",
                        )
                    },
                    required=["file_path"],
                ),
            ),
        )
    
    @staticmethod
    def execute(file_path: str) -> int:
        if not os.path.exists(file_path):
            raise ValueError("File does not exist")
        if not os.path.isfile(file_path):
            raise ValueError("Provided path is a folder")
        
        total_bytes = 0
        try:
            total_bytes = os.path.getsize(file_path)
        except Exception as e:
            raise ValueError(f"Error calculating file size: {str(e)} in file path {file_path}")
        
        return total_bytes


class FileManager:
    @staticmethod
    def get_all_tools() -> List[Tool]:
        return [
            SaveFile().get_tool_manifest(),
            SaveFileAppend().get_tool_manifest(),
            ReadFolder().get_tool_manifest(),
            ReadFile().get_tool_manifest(),
        ]

    @staticmethod
    def tool_map():
        return {
            "save_file": SaveFile.execute,
            "save_file_append": SaveFileAppend.execute,
            "read_folder": ReadFolder.execute,
            "read_file": ReadFile.execute,
        }

    @staticmethod
    def run_tool(tool_name, arguments):
        tool_mapping = FileManager.tool_map()
        if tool_name in tool_mapping:
            return tool_mapping[tool_name](**arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

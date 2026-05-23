# Collection of tools for the LLM API
# It can also execute on the server side, and can be used to execute code, run shell commands, etc.
import sqlite3
import subprocess
import json
import os
from typing import List
from common.llm import (
    SupportedProvider,
    LLMToolkit,
)

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
# Force use of the raw PDFium engine instead of the V4 layout engine
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

from structs.tool import (
    Tool,
    Type,
    Function,
    Parameters,
    ParameterType,
    Properties,
    InputType,
)

'''
#TODO:
1. Generalize exportable tool group. It should use same base class since it has same method.
    current tool group classes are SQLite, DocumentParser, FileManager.
'''

class ShowTables:
    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="show_tables",
                description="List all table names in a SQLite database.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "db_path": Properties(
                            type=InputType.String,
                            description="Path to the SQLite database file.",
                        )
                    },
                    required=["db_path"],
                ),
            ),
        )
    
    @staticmethod
    def execute(db_path: str) -> List[str]:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables

class CreateDatabase:
    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="create_database",
                description="Create a new SQLite database file.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "db_name": Properties(
                            type=InputType.String,
                            description="Database name without extension.",
                        )
                    },
                    required=["db_name"],
                ),
            ),
        )
    
    @staticmethod
    def execute(db_name: str) -> bool:
        db_path = f"{db_name}.db"
        subprocess.run(["sqlite3", db_path], input=b"", check=True)
        return True

    @staticmethod
    def success(db_name: str) -> str:
        return f"Database {db_name}.db created successfully."


class InsertIntoTable:
    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="insert_into_table",
                description="Insert one record into a SQLite table.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "db_path": Properties(
                            type=InputType.String,
                            description="Path to the SQLite database file.",
                        ),
                        "table_name": Properties(
                            type=InputType.String,
                            description="Target table name.",
                        ),
                        "data": Properties(
                            type=InputType.String,
                            description="JSON object string containing column/value pairs.",
                        ),
                    },
                    required=["db_path", "table_name", "data"],
                ),
            ),
        )
    
    @staticmethod
    def execute(db_path: str, table_name: str, data: str) -> bool:
        if type(data) == str:
            data = json.loads(data)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        values = list(data.values())
        cursor.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", values)
        conn.commit()
        conn.close()
        return True

class QueryTable:
    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="query_table",
                description="Execute a SQL query against a SQLite database.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "db_path": Properties(
                            type=InputType.String,
                            description="Path to the SQLite database file.",
                        ),
                        "query": Properties(
                            type=InputType.String,
                            description="SQL query to execute.",
                        ),
                    },
                    required=["db_path", "query"],
                ),
            ),
        )
    
    @staticmethod
    def execute(db_path: str, query: str) -> List[tuple]:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        return results

class SQLite:
    """
    Collection for interacting with SQLite databases. Can be used to execute SQL queries and return results.
    All should be a static method; it behaves like a collection of functions.
    """
    @staticmethod
    def get_all_tools() -> List[Tool]:
        return [
            ShowTables().get_tool_manifest(),
            CreateDatabase().get_tool_manifest(),
            InsertIntoTable().get_tool_manifest(),
            QueryTable().get_tool_manifest(),
        ]

    @staticmethod
    def tool_map():
        return {
            "show_tables": ShowTables.execute,
            "create_database": CreateDatabase.execute,
            "insert_into_table": InsertIntoTable.execute,
            "query_table": QueryTable.execute,
        }

    @staticmethod
    def run_tool(tool_name, arguments):
        tool_mapping = SQLite.tool_map()
        if tool_name in tool_mapping:
            return tool_mapping[tool_name](**arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")


from docling.document_converter import DocumentConverter

class ReadDocument:
    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="read_document",
                description="Read the content of a document given its file path.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "file_path": Properties(
                            type=InputType.String,
                            description="The file path of the document to read.",
                        )
                    },
                    required=["file_path"],
                ),
            ),
        )
    
    @staticmethod
    def execute(file_path: str) -> str:
        if not file_path:
            raise ValueError("file_path is required")

        if os.path.getsize(file_path) > 10 * 1024 * 1024:  # 10 MB size limit
            raise ValueError("File size exceeds the 10 MB limit")

        if not os.path.exists(file_path):
            raise ValueError("File does not exist")

        pipeline_options = PdfPipelineOptions()
        
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True
        pipeline_options.images_scale = 1.0
        
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=PyPdfiumDocumentBackend,
                )
            }
        )
        result = converter.convert(file_path)
        markdown_content = result.document.export_to_markdown()

        return markdown_content

class DocumentParser:
    @staticmethod
    def get_all_tools() -> List[Tool]:
        return [
            ReadDocument().get_tool_manifest(),
        ]

    @staticmethod
    def tool_map():
        return {
            "read_document": ReadDocument.execute,
        }

    @staticmethod
    def run_tool(tool_name, arguments):
        tool_mapping = DocumentParser.tool_map()
        if tool_name in tool_mapping:
            return tool_mapping[tool_name](**arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        

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

class FileManager:
    @staticmethod
    def get_all_tools() -> List[Tool]:
        return [
            SaveFile().get_tool_manifest(),
            ReadFolder().get_tool_manifest(),
            ReadFile().get_tool_manifest(),
        ]

    @staticmethod
    def tool_map():
        return {
            "save_file": SaveFile.execute,
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


class Semantic:
    def __init__(self, provider, api_key):
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
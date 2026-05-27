import os
from typing import List
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
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

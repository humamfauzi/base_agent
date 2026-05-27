import os
from typing import Any, List
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
                description="Parse an entire PDF document, save the full Markdown output to disk, and return only compact metadata about the saved file.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "file_path": Properties(
                            type=InputType.String,
                            description="The file path of the PDF document to parse.",
                        ),
                        "output_path": Properties(
                            type=InputType.String,
                            description="Optional output path for the saved Markdown file. Defaults to the source file path with a .md extension.",
                        ),
                    },
                    required=["file_path"],
                ),
            ),
        )
    
    @staticmethod
    def execute(file_path: str, output_path: str = "") -> dict[str, Any]:
        if not file_path:
            raise ValueError("file_path is required")

        if not os.path.exists(file_path):
            raise ValueError("File does not exist")

        if not os.path.isfile(file_path):
            raise ValueError("Provided path is not a file")

        if os.path.getsize(file_path) > 10 * 1024 * 1024:  # 10 MB size limit
            raise ValueError("File size exceeds the 10 MB limit")

        if not output_path:
            source_root, _ = os.path.splitext(file_path)
            output_path = f"{source_root}.md"

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

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
        with open(output_path, "w", encoding="utf-8") as markdown_file:
            markdown_file.write(markdown_content)

        return {
            "status": "saved",
            "source_path": file_path,
            "output_path": output_path,
            "markdown_characters": len(markdown_content),
            "markdown_bytes": os.path.getsize(output_path),
        }


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

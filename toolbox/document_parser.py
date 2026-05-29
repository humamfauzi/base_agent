import os
from pathlib import Path
from typing import Any, List
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument
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


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


def _validate_file_path(file_path: str) -> None:
    if not file_path:
        raise ValueError("file_path is required")

    if not os.path.exists(file_path):
        raise ValueError("File does not exist")

    if not os.path.isfile(file_path):
        raise ValueError("Provided path is not a file")

    if os.path.getsize(file_path) > MAX_FILE_SIZE_BYTES:
        raise ValueError("File size exceeds the 10 MB limit")


def _resolve_output_path(file_path: str, output_path: str) -> str:
    if output_path:
        return output_path

    source_root, _ = os.path.splitext(file_path)
    return f"{source_root}.md"


def _build_converter(*, do_ocr: bool) -> DocumentConverter:
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = do_ocr
    pipeline_options.do_table_structure = True
    pipeline_options.images_scale = 1.0

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
                backend=PyPdfiumDocumentBackend,
            )
        }
    )


def _analyze_pdf_text_layer(file_path: str) -> dict[str, Any]:
    input_document = InputDocument(
        path_or_stream=Path(file_path),
        format=InputFormat.PDF,
        backend=PyPdfiumDocumentBackend,
    )

    if not input_document.valid or not input_document._backend.is_valid():
        raise ValueError("Unable to open the PDF with Docling")

    backend = input_document._backend
    page_count = backend.page_count()
    pages_with_text_layer = 0
    total_text_cells = 0
    total_extracted_characters = 0

    try:
        for page_number in range(page_count):
            page_backend = backend.load_page(page_number)
            try:
                text_cells = list(page_backend.get_text_cells())
            finally:
                page_backend.unload()

            text_cell_count = len(text_cells)
            extracted_characters = sum(len((cell.text or "")) for cell in text_cells)

            if text_cell_count > 0 and extracted_characters > 0:
                pages_with_text_layer += 1

            total_text_cells += text_cell_count
            total_extracted_characters += extracted_characters
    finally:
        backend.unload()

    if page_count == 0:
        document_type = "empty"
    elif pages_with_text_layer == 0:
        document_type = "scanned"
    elif pages_with_text_layer == page_count:
        document_type = "text"
    else:
        document_type = "mixed"

    return {
        "status": "analyzed",
        "source_path": file_path,
        "document_type": document_type,
        "page_count": page_count,
        "pages_with_text_layer": pages_with_text_layer,
        "pages_without_text_layer": page_count - pages_with_text_layer,
        "total_text_cells": total_text_cells,
        "total_extracted_characters": total_extracted_characters,
        "should_use_ocr": document_type in {"scanned", "mixed"},
        "suggested_tool": "read_document_ocr"
        if document_type in {"scanned", "mixed"}
        else "read_document",
    }


def _convert_pdf_to_markdown(
    file_path: str,
    output_path: str,
    *,
    do_ocr: bool,
) -> dict[str, Any]:
    resolved_output_path = _resolve_output_path(file_path, output_path)
    output_dir = os.path.dirname(resolved_output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    converter = _build_converter(do_ocr=do_ocr)
    result = converter.convert(file_path)
    markdown_content = result.document.export_to_markdown()

    with open(resolved_output_path, "w", encoding="utf-8") as markdown_file:
        markdown_file.write(markdown_content)

    return {
        "status": "saved",
        "source_path": file_path,
        "output_path": resolved_output_path,
        "markdown_characters": len(markdown_content),
        "markdown_bytes": os.path.getsize(resolved_output_path),
    }


class DetectDocumentType:
    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="detect_document_type",
                description="Inspect a PDF using Docling's native text-layer extraction and report whether it looks like a text PDF, scanned PDF, mixed PDF, or empty PDF.",
                parameters=Parameters(
                    type=ParameterType.Object,
                    properties={
                        "file_path": Properties(
                            type=InputType.String,
                            description="The file path of the PDF document to inspect.",
                        ),
                    },
                    required=["file_path"],
                ),
            ),
        )

    @staticmethod
    def execute(file_path: str) -> dict[str, Any]:
        _validate_file_path(file_path)
        return _analyze_pdf_text_layer(file_path)


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
        _validate_file_path(file_path)
        return _convert_pdf_to_markdown(file_path, output_path, do_ocr=False)

class ReadDocumentOCR:
    def get_tool_manifest(self) -> Tool:
        return Tool(
            type=Type.Function,
            function=Function(
                name="read_document_ocr",
                description="Parse an entire PDF document using OCR, save the full Markdown output to disk, and return only compact metadata about the saved file.",
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
        _validate_file_path(file_path)
        return _convert_pdf_to_markdown(file_path, output_path, do_ocr=True)

class DocumentParser:
    @staticmethod
    def get_all_tools() -> List[Tool]:
        return [
            DetectDocumentType().get_tool_manifest(),
            ReadDocument().get_tool_manifest(),
            ReadDocumentOCR().get_tool_manifest(),
        ]

    @staticmethod
    def tool_map():
        return {
            "detect_document_type": DetectDocumentType.execute,
            "read_document": ReadDocument.execute,
            "read_document_ocr": ReadDocumentOCR.execute,
        }

    @staticmethod
    def run_tool(tool_name, arguments):
        tool_mapping = DocumentParser.tool_map()
        if tool_name in tool_mapping:
            return tool_mapping[tool_name](**arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

def analyze_custom_document(form_url: str, model_id: str, endpoint: str, key: str) -> dict:
    """
    Analyze a document from a URL using a custom model in Azure Document Intelligence.

    :param form_url: URL of the document to analyze
    :param model_id: The ID of the custom model
    :param endpoint: Azure Form Recognizer endpoint
    :param key: Azure Form Recognizer API key
    :return: Dictionary containing analysis results
    """

    document_intelligence_client = DocumentIntelligenceClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key)
    )

    poller = document_intelligence_client.begin_analyze_document(
        model_id,
        AnalyzeDocumentRequest(url_source=form_url)
    )
    result = poller.result()

    analysis_result = {
        "model_id": result.model_id,
        "documents": [],
        "pages": [],
        "tables": []
    }

    for document in result.documents:
        doc_info = {
            "doc_type": document.doc_type,
            "confidence": document.confidence,
            "fields": {}
        }
        for name, field in document.fields.items():
            doc_info["fields"][name] = {
                "type": field.type,
                "value": field.content,
                "confidence": field.confidence
            }
        analysis_result["documents"].append(doc_info)

    for page in result.pages:
        page_info = {
            "page_number": page.page_number,
            "lines": [line.content for line in page.lines],
            "words": [{"content": word.content, "confidence": word.confidence} for word in page.words],
            "selection_marks": [
                {"state": mark.state, "confidence": mark.confidence}
                for mark in page.selection_marks or []
            ]
        }
        analysis_result["pages"].append(page_info)

    for table in result.tables:
        table_info = {
            "bounding_regions": [{"page_number": region.page_number} for region in table.bounding_regions],
            "cells": [
                {
                    "row_index": cell.row_index,
                    "column_index": cell.column_index,
                    "content": cell.content
                }
                for cell in table.cells
            ]
        }
        analysis_result["tables"].append(table_info)

    return analysis_result

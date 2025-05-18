from flask import Flask, request, jsonify
from azure.storage.blob import BlobServiceClient, ContentSettings
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import os
import uuid

from azure.ai.documentintelligence.models import AddressValue
from flasgger import Swagger, swag_from

from AnalyzerFunction import analyze_invoice_from_url
from ImageGenerator import generate_magazine_images_from_story
from KYCAnalyzer import analyze_custom_document
from StockSuggest import suggest_stock_to_buy
from TransectionAnalysis import generate_weekly_spending_story
# JSON Encoder for AddressValue
from json import JSONEncoder

app = Flask(__name__)
swagger = Swagger(app)

load_dotenv()

AZURE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("CONTAINER_NAME")
CONTAINER_NAME2 = os.getenv("CONTAINER_NAME2")

MODEL_ID = os.getenv("MODEL_ID")
FORM_RECOGNIZER_ENDPOINT = os.getenv("FORM_RECOGNIZER_ENDPOINT")
API_KEY = os.getenv("API_KEY")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)
# Azure Blob Storage setup




class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, AddressValue):
            return obj.to_dict()
        return super().default(obj)


app.json_encoder = CustomJSONEncoder

@app.route('/weekly-story', methods=['POST'])
@swag_from({
    'tags': ['Story'],
    'consumes': ['application/json'],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'array',
                'items': {
                    'type': 'object'
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Weekly story generated from transactions',
            'schema': {
                'type': 'object',
                'properties': {
                    'story': {'type': 'string'}
                }
            }
        },
        400: {'description': 'Invalid input'}
    }
})
def generate_story():
    if not request.is_json:
        return jsonify({"error": "Request body must be a JSON array"}), 400

    data = request.get_json()

    if not isinstance(data, list):
        return jsonify({"error": "Expected a JSON array of transactions"}), 400

    try:
        story = generate_weekly_spending_story(data)
        image = generate_magazine_images_from_story(story)
        return jsonify({"story": story,"image": image})
    except Exception as e:
        return jsonify({"error": f"Failed to generate story: {str(e)}"}), 500

@app.route('/suggest-stock', methods=['POST'])
@swag_from({
    'tags': ['Stock Recommendation'],
    'consumes': ['application/json'],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'user_portfolio': {'type': 'object'},
                    'market_data': {'type': 'object'}
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Stock recommendation generated',
            'schema': {
                'type': 'object',
                'properties': {
                    'suggestion': {'type': 'string'}
                }
            }
        },
        400: {
            'description': 'Invalid input'
        }
    }
})
def get_stock_suggestion():
    if not request.is_json:
        return jsonify({"error": "Request must be in JSON format"}), 400

    data = request.get_json()

    # Validate required fields
    if 'user_portfolio' not in data or 'market_data' not in data:
        return jsonify({"error": "Missing required fields: user_portfolio and market_data"}), 400

    try:
        suggestion = suggest_stock_to_buy(data['user_portfolio'], data['market_data'])
        return jsonify({"suggestion": suggestion})
    except Exception as e:
        return jsonify({"error": f"Failed to generate stock suggestion: {str(e)}"}), 500

@app.route('/upload-invoice', methods=['POST'])
@swag_from({
    'tags': ['Invoice'],
    'consumes': ['multipart/form-data'],
    'parameters': [
        {
            'name': 'file',
            'in': 'formData',
            'type': 'file',
            'required': True,
            'description': 'Invoice image file to upload'
        }
    ],
    'responses': {
        200: {
            'description': 'Parsed invoice data',
            'schema': {
                'type': 'object',
                'properties': {
                    'invoice_url': {'type': 'string'},
                    'parsed_fields': {'type': 'object'}
                }
            }
        },
        400: {
            'description': 'Invalid input'
        }
    }
})
def upload_invoice():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Generate a unique filename
    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"

    try:
        blob_client = container_client.get_blob_client(filename)

        # Upload file stream to blob storage
        blob_client.upload_blob(
            file,
            overwrite=False,  # No need to overwrite since filename is unique
            content_settings=ContentSettings(content_type=file.content_type)
        )
    except Exception as e:
        return jsonify({"error": f"Failed to upload to Azure Blob Storage: {str(e)}"}), 500

    # Construct the public URL (assuming container access is Blob-level public)
    blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{filename}"
    print(blob_url)

    # Analyze invoice using existing function
    try:
        result = analyze_invoice_from_url(blob_url)
    except Exception as e:
        return jsonify({"error": f"Failed to analyze invoice: {str(e)}"}), 500

    return jsonify({
        "invoice_url": blob_url,
        "parsed_fields": result
    })

@app.route('/analyze-kyc-form', methods=['POST'])
@swag_from({
    'tags': ['KYC'],
    'consumes': ['multipart/form-data'],
    'parameters': [
        {
            'name': 'file',
            'in': 'formData',
            'type': 'file',
            'required': True,
            'description': 'KYC document to analyze'
        }
    ],
    'responses': {
        200: {
            'description': 'Analyzed KYC form data',
            'schema': {
                'type': 'object',
                'properties': {
                    'document_url': {'type': 'string'},
                    'analysis_result': {'type': 'object'}
                }
            }
        },
        400: {
            'description': 'Invalid input'
        }
    }
})
def analyze_kyc_form():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Generate a unique filename
    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"

    try:
        container_client_kyc = blob_service_client.get_container_client(CONTAINER_NAME2)
        blob_client = container_client_kyc.get_blob_client(filename)
        # Upload file to Azure Blob Storage
        blob_client.upload_blob(
            file,
            overwrite=False,
            content_settings=ContentSettings(content_type=file.content_type)
        )
    except Exception as e:
        return jsonify({"error": f"Failed to upload to Azure Blob Storage: {str(e)}"}), 500

    # Construct Blob URL (assuming blob-level public access)
    blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME2}/{filename}"
    print(blob_url)
    try:
        # Replace these with actual values or fetch dynamically if needed
        MODEL_ID = "kyc-form-analyzer"
        FORM_RECOGNIZER_ENDPOINT = "https://analyticaformanalyzer.cognitiveservices.azure.com/"
        API_KEY = "3nq7scnM6ibQbZ3hlNIM1C4rlXPfsHpLAvQO5S7j0XnsQl1cYo2CJQQJ99BEACYeBjFXJ3w3AAALACOGkwBu"

        analysis_result = analyze_custom_document(blob_url, MODEL_ID, FORM_RECOGNIZER_ENDPOINT, API_KEY)
    except Exception as e:
        return jsonify({"error": f"Failed to analyze document: {str(e)}"}), 500

    return jsonify({
        "document_url": blob_url,
        "analysis_result": analysis_result
    })

if __name__ == "__main__":
    app.run(debug=True)

import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

load_dotenv()

endpoint = os.getenv("FORM_ANALYZER_ENDPOINT")
key = os.getenv("FORM_ANALYZER_KEY")

document_intelligence_client = DocumentIntelligenceClient(
    endpoint=endpoint, credential=AzureKeyCredential(key)
)


def analyze_invoice_from_url(formUrl: str) -> dict:
    poller = document_intelligence_client.begin_analyze_document(
        "prebuilt-invoice", AnalyzeDocumentRequest(url_source=formUrl)
    )
    invoices = poller.result()

    results = []

    for invoice in invoices.documents:
        invoice_data = {}

        def get_field_value(field_name):
            field = invoice.fields.get(field_name)
            if not field:
                return None
            # Extract the value depending on the type (string, date, address, currency, number)
            if hasattr(field, 'value_string') and field.value_string is not None:
                return field.value_string
            if hasattr(field, 'value_date') and field.value_date is not None:
                return str(field.value_date)
            if hasattr(field, 'value_currency') and field.value_currency is not None:
                return field.value_currency.amount
            if hasattr(field, 'value_number') and field.value_number is not None:
                return field.value_number
            if hasattr(field, 'value_array') and field.value_array is not None:
                return field.value_array
            if hasattr(field, 'value_object') and field.value_object is not None:
                return field.value_object
            return None

        # Extract all the fields similarly to your code, storing in invoice_data
        invoice_data["VendorName"] = get_field_value("VendorName")
        invoice_data["CustomerName"] = get_field_value("CustomerName")
        invoice_data["CustomerId"] = get_field_value("CustomerId")
        invoice_data["InvoiceId"] = get_field_value("InvoiceId")
        invoice_data["InvoiceDate"] = get_field_value("InvoiceDate")
        invoice_data["InvoiceTotal"] = get_field_value("InvoiceTotal")
        invoice_data["DueDate"] = get_field_value("DueDate")
        invoice_data["PurchaseOrder"] = get_field_value("PurchaseOrder")

        # Process Items array
        items_field = invoice.fields.get("Items")
        if items_field:
            items_list = []
            for item in items_field.value_array:
                item_obj = item.value_object
                item_data = {}
                # Description
                desc = item_obj.get("Description")
                if desc:
                    item_data["Description"] = desc.value_string
                qty = item_obj.get("Quantity")
                if qty:
                    item_data["Quantity"] = qty.value_number
                unit = item_obj.get("Unit")
                if unit:
                    item_data["Unit"] = unit.value_string if hasattr(unit, "value_string") else unit.value_number
                unit_price = item_obj.get("UnitPrice")
                if unit_price:
                    item_data["UnitPrice"] = unit_price.value_currency.amount
                product_code = item_obj.get("ProductCode")
                if product_code:
                    item_data["ProductCode"] = product_code.value_string
                date = item_obj.get("Date")
                if date:
                    item_data["Date"] = str(date.value_date)
                tax = item_obj.get("Tax")
                if tax:
                    item_data["Tax"] = tax.value_string
                amount = item_obj.get("Amount")
                if amount:
                    item_data["Amount"] = amount.value_currency.amount
                items_list.append(item_data)
            invoice_data["Items"] = items_list

        invoice_data["SubTotal"] = get_field_value("SubTotal")
        invoice_data["TotalTax"] = get_field_value("TotalTax")
        invoice_data["PreviousUnpaidBalance"] = get_field_value("PreviousUnpaidBalance")
        invoice_data["AmountDue"] = get_field_value("AmountDue")
        invoice_data["ServiceStartDate"] = get_field_value("ServiceStartDate")
        invoice_data["ServiceEndDate"] = get_field_value("ServiceEndDate")

        results.append(invoice_data)

    return results

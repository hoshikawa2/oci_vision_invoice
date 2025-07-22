import time
import json
from pathlib import Path
from datetime import datetime

import oci
from langchain_community.chat_models.oci_generative_ai import ChatOCIGenAI
from langchain.schema import HumanMessage

# ====================
# 1. Load Configuration
# ====================
with open("./config", "r") as f:
    config_data = json.load(f)

NAMESPACE = config_data["namespace"]
INPUT_BUCKET = config_data["input_bucket"]
OUTPUT_BUCKET = config_data["output_bucket"]
PROFILE = config_data["oci_profile"]
COMPARTMENT_ID = config_data["compartment_id"]
LLM_ENDPOINT = config_data["llm_endpoint"]

# ====================
# 2. Initialize OCI Clients
# ====================
oci_config = oci.config.from_file("~/.oci/config", PROFILE)
object_storage = oci.object_storage.ObjectStorageClient(oci_config)
ai_vision_client = oci.ai_vision.AIServiceVisionClient(oci_config)

# ====================
# 3. Initialize LLM
# ====================
llm = ChatOCIGenAI(
    model_id="meta.llama-3.1-405b-instruct",
    service_endpoint=LLM_ENDPOINT,
    compartment_id=COMPARTMENT_ID,
    auth_profile=PROFILE,
    model_kwargs={"temperature": 0.7, "top_p": 0.75, "max_tokens": 2000},
)

# ====================
# 4. Few-shot Prompt Base
# ====================
few_shot_examples = [
    """
    Invoice text: 
        "EMITENTE": "Comercial ABC Ltda - Rua A, 123 - Belo Horizonte - MG"
        "NF": "NF102030"
        "DESTINATÁRIO": "Distribuidora XYZ - São Paulo - SP"
        "DADOS DOS PRODUTOS / SERVIÇOS": 
            "Cabo HDMI 2.0 2m, preto" | PRICE: 39.90 
            "Teclado Mecânico RGB ABNT2" | PRICE: 199.99 
            "Mouse Gamer 3200DPI" | PRICE: 89.50 

    Extracted fields (JSON format):
        {
          "nf": "NF102030",
          "customer": "Comercial ABC Ltda",
          "location": "MG",
          "items": [
            {"description": "Cabo HDMI 2.0 2m, preto", "price": 39.90},
            {"description": "Teclado Mecânico RGB ABNT2", "price": 199.99},
            {"description": "Mouse Gamer 3200DPI", "price": 89.50}
          ]
        }
    """
]

instruction = """
You are a fiscal data extractor.

Your goal is to:
- Extract the invoice number (field 'nf')
- Extract the customer name (field 'Nome / Razao Social')
- Extract the state (field 'UF') — ⚠️ use **only** the state of the EMITTER company, based on its name and address.
- Extract the list of products and prices (fields: 'Descricao do Produto / Servico' and 'Valor Unitario')
- Return a JSON structure as a response in a unique line:
        {
          "nf": "NF102030",
          "customer": "Comercial ABC Ltda",
          "location": "MG",
          "items": [
            {"description": "Cabo HDMI 2.0 2m, preto", "price": 39.90},
            {"description": "Teclado Mecânico RGB ABNT2", "price": 199.99},
            {"description": "Mouse Gamer 3200DPI", "price": 89.50}
          ]
        }
"""

# ====================
# 5. Bucket Monitoring and Processing
# ====================
processed_files = set()

def perform_ocr(file_name):
    print(f"📄 Performing OCR on: {file_name}")

    response = ai_vision_client.analyze_document(
        analyze_document_details=oci.ai_vision.models.AnalyzeDocumentDetails(
            features=[
                oci.ai_vision.models.DocumentTableDetectionFeature(
                    feature_type="TEXT_DETECTION")],
            document=oci.ai_vision.models.ObjectStorageDocumentDetails(
                source="OBJECT_STORAGE",
                namespace_name=NAMESPACE,
                bucket_name=INPUT_BUCKET,
                object_name=file_name),
            compartment_id=COMPARTMENT_ID,
            language="ENG",
            document_type="INVOICE")
    )

    print(response.data)

    return response.data

def extract_data_with_llm(ocr_result, file_name):
    # 🔍 Extrai texto OCR (usando a estrutura da resposta do OCI Vision)
    extracted_lines = []
    for page in getattr(ocr_result, 'pages', []):
        for line in getattr(page, 'lines', []):
            extracted_lines.append(line.text.strip())

    plain_text = "\n".join(extracted_lines)

    # 🧠 Monta o prompt com instrução, few-shot e texto OCR limpo
    prompt = instruction + "\n" + "\n".join(few_shot_examples) + f"\nInvoice text:\n{plain_text}\nExtracted fields (JSON format):"

    # 🔗 Chamada ao LLM
    response = llm([HumanMessage(content=prompt)])

    # 🧪 Tenta extrair JSON puro da resposta
    try:
        content = response.content.strip()
        first_brace = content.find("{")
        last_brace = content.rfind("}")
        json_string = content[first_brace:last_brace + 1]
        parsed_json = json.loads(json_string)
    except Exception as e:
        print(f"⚠️ Erro ao extrair JSON da resposta do LLM: {e}")
        parsed_json = {"raw_response": response.content}

    return {
        "file": file_name,
        "result": parsed_json,
        "timestamp": datetime.utcnow().isoformat()
    }

def save_output(result, file_name):
    output_name = Path(file_name).stem + ".json"
    object_storage.put_object(
        namespace_name=NAMESPACE,
        bucket_name=OUTPUT_BUCKET,
        object_name=output_name,
        put_object_body=json.dumps(result, ensure_ascii=False).encode("utf-8")
    )
    print(f"✅ Result saved as {output_name} in the output bucket.")

def monitor_bucket():
    print("📡 Monitoring input bucket...")
    while True:
        objects = object_storage.list_objects(
            namespace_name=NAMESPACE,
            bucket_name=INPUT_BUCKET
        ).data.objects

        for obj in objects:
            file_name = obj.name
            if file_name.endswith((".png", ".jpg", ".jpeg")) and file_name not in processed_files:
                try:
                    ocr_text = perform_ocr(file_name)
                    result = extract_data_with_llm(ocr_text, file_name)
                    save_output(result, file_name)
                    processed_files.add(file_name)
                except Exception as e:
                    print(f"❌ Error processing {file_name}: {e}")

        time.sleep(30)  # Wait 30 seconds before checking again

if __name__ == "__main__":
    monitor_bucket()
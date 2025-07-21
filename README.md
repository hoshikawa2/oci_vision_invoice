# 📄 Automatic Invoice Processing with OCI Vision and OCI Generative AI

## 🧠 Objective

This tutorial demonstrates how to implement an automated pipeline that monitors a bucket in Oracle Cloud Infrastructure (OCI) for incoming invoice images, extracts textual content using **OCI Vision**, and then applies **OCI Generative AI** (LLM) to extract structured fiscal data like invoice number, customer, and item list.

---

## 🚀 Use Cases

- Automating invoice ingestion from Object Storage.
- Extracting structured data from semi-structured scanned documents.
- Integrating OCR and LLM in real-time pipelines using OCI AI services.

---

## 🧱 Oracle Cloud Services Used

| Service                     | Purpose                                                                 |
|----------------------------|-------------------------------------------------------------------------|
| **OCI Vision**             | Performs OCR (Optical Character Recognition) on uploaded invoice images.|
| **OCI Generative AI**      | Extracts structured JSON data from raw OCR text using few-shot prompts. |
| **Object Storage**         | Stores input invoice images and output JSON results.                    |

---

## ⚙️ Prerequisites

1. An OCI account with access to:
    - Vision AI
    - Generative AI
    - Object Storage
2. A Python 3.10 at least
3. A bucket for input images (e.g., `input-bucket`) and another for output files (e.g., `output-bucket`).
4. A [config](./files/config) with:
   ```json
   {
     "oci_profile": "DEFAULT",
     "namespace": "your_namespace",
     "input_bucket": "input-bucket",
     "output_bucket": "output-bucket",
     "compartment_id": "ocid1.compartment.oc1..xxxx",
     "llm_endpoint": "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
   }
   ```

---

## 🛠️ How to Run

1. Execute the [requirements.txt](./files/requirements.txt) with:

     
    pip install -r requirements.txt 

2. Run the Python script [main.py](./files/main.py).
3. Upload invoice images (e.g., `.png`, `.jpg`) to your input bucket.
4. Wait for the image to be processed and the extracted JSON saved in the output bucket.

---

## 🧩 Code Walkthrough

### 1. Load Configuration

```python
with open("./config", "r") as f:
    config_data = json.load(f)
```

> Loads all required configuration values such as namespace, bucket names, compartment ID, and LLM endpoint.

---

### 2. Initialize OCI Clients

```python
oci_config = oci.config.from_file("~/.oci/config", PROFILE)
object_storage = oci.object_storage.ObjectStorageClient(oci_config)
ai_vision_client = oci.ai_vision.AIServiceVisionClient(oci_config)
```

> Sets up the OCI SDK clients to access Object Storage and AI Vision services.

---

### 3. Initialize LLM

```python
llm = ChatOCIGenAI(
    model_id="meta.llama-3.1-405b-instruct",
    service_endpoint=LLM_ENDPOINT,
    compartment_id=COMPARTMENT_ID,
    auth_profile=PROFILE,
    model_kwargs={"temperature": 0.7, "top_p": 0.75, "max_tokens": 2000},
)
```

> Initializes the OCI Generative AI model for natural language understanding and text-to-structure conversion.

---

### 4. Few-shot Prompt

```python
few_shot_examples = [ ... ]
instruction = """
You are a fiscal data extractor.
...
"""
```

> Uses few-shot learning by providing an example of expected output so the model learns how to extract structured fields like `number of invoice`, `customer`, `location`, and `items`.

---

### 5. OCR with OCI Vision

```python
def perform_ocr(file_name):
    ...
```

> This function:
> - Sends the image to OCI Vision.
> - Requests text detection.
> - Returns the extracted raw text.

---

### 6. Data Extraction with LLM

```python
def extract_data_with_llm(ocr_text, file_name):
    ...
```

> This function:
> - Combines instructions + few-shot example + OCR text.
> - Sends it to OCI Generative AI.
> - Receives structured JSON fields (as string).

---

### 7. Save Output to Object Storage

```python
def save_output(result, file_name):
    ...
```

> Uploads the structured result into the output bucket using the original filename (with `.json` extension).

---

### 8. Main Loop: Monitor and Process

```python
def monitor_bucket():
    ...
```

> Main routine that:
> - Monitors the input bucket every 30 seconds.
> - Detects new `.png`, `.jpg`, `.jpeg` files.
> - Runs OCR + LLM + Upload in sequence.
> - Keeps track of already processed files in memory.

---

### 9. Entry Point

```python
if __name__ == "__main__":
    monitor_bucket()
```

> Starts the bucket watcher and begins processing invoices automatically.

---

## ✅ Expected Output

For each uploaded invoice image:
- A corresponding `.json` file is generated with structured content like:

```json
{
  "file": "nota123.png",
  "result": "{ "nf": "NF102030", "customer": "Comercial ABC Ltda", ... }",
  "timestamp": "2025-07-21T12:34:56.789Z"
}
```

---

## 🧪 Testing Suggestions

- Use real or dummy invoices with legible product lines and emitente.
- Upload multiple images in sequence to see automated processing.
- Log into OCI Console > Object Storage to verify results in both buckets.

---

## 📌 Notes

- OCI Vision supports Portuguese OCR (`language="POR"` can be used instead of `"ENG"`).
- LLM prompt can be adjusted to extract other fields like `CNPJ`, `quantidade`, `data de emissão`, etc.
- Consider persisting `processed_files` with a database or file to make the process fault-tolerant.

---

## 📚 References

- [OCI Vision Documentation](https://docs.oracle.com/en-us/iaas/vision/)
- [OCI Generative AI Documentation](https://docs.oracle.com/en-us/iaas/generative-ai/)
- [LangChain OCI Integration](https://python.langchain.com/docs/integrations/chat/oci_gen_ai/)

## Acknowledgments

- **Author** - Cristiano Hoshikawa (Oracle LAD A-Team Solution Engineer)

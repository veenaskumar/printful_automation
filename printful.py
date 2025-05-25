import pandas as pd
import requests
from collections import defaultdict
from typing import Dict, List
import time

# === Place your Printful API key here ===
PRINTFUL_API_KEY = "8Enter your key"

HEADERS = {
    "Authorization": f"Bearer {PRINTFUL_API_KEY}",
    "Content-Type": "application/json",
}


def convert_drive_url(url: str) -> str:
    """
    Converts Google Drive sharing URLs to direct download URLs.
    """
    if "drive.google.com" in url and "file/d/" in url:
        file_id = url.split("/file/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url  # Return original if not matching pattern


def upload_image(image_url: str, retries: int = 3, backoff: int = 5) -> int:
    """
    Uploads image from URL to Printful and returns file ID.
    Retries on failure with exponential backoff.
    """
    direct_url = convert_drive_url(image_url)
    for attempt in range(1, retries + 1):
        try:
            print(f"Uploading image from {direct_url} (Attempt {attempt})")
            response = requests.post(
                "https://api.printful.com/files",
                headers=HEADERS,
                json={"url": direct_url},
            )
            response.raise_for_status()
            file_id = response.json()["result"]["id"]
            print(f"Uploaded image ID: {file_id}")
            return file_id
        except Exception as e:
            print(f"Upload failed on attempt {attempt}: {e}")
            if attempt < retries:
                print(f"Retrying in {backoff} seconds...")
                time.sleep(backoff)
            else:
                raise e


def create_product_from_template(
    template_id: int, variant_data: List[Dict], product_name: str
):
    """
    Creates a product with multiple variants from template.
    """
    sync_variants = []
    for variant in variant_data:
        files = [
            {"type": "front", "id": variant["front_file_id"]},
            {"type": "back", "id": variant["back_file_id"]},
        ]
        if variant.get("label_file_id"):
            files.append({"type": "inside_label", "id": variant["label_file_id"]})

        sync_variants.append(
            {
                "variant_id": variant["variant_id"],
                "retail_price": variant.get("retail_price", "29.99"),
                "files": files,
            }
        )

    payload = {
        "sync_product": {
            "name": "Test Product",
            "is_visible": True,
            "external_id": f"{product_name}-{template_id}",
        },
        "sync_variants": sync_variants,
        "title": product_name,
    }

    print(f"Creating product '{product_name}' with {len(sync_variants)} variant(s)...")
    response = requests.post(
        "https://api.printful.com/store/products", headers=HEADERS, json=payload
    )
    try:
        response.raise_for_status()
        product_id = response.json()["result"]["id"]
        print(f"✅ Product created: {product_name} (ID: {product_id})")
        return response.json()
    except Exception as e:
        print(f"Failed to create product '{product_name}': {e}")
        print(f"Response content: {response.text}")
        return None


def process_file(file_path: str):
    """
    Reads CSV or Excel, groups rows by product, uploads images, and creates products.
    """
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    elif file_path.endswith(".xlsx"):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format. Use .csv or .xlsx")

    # Group by product name and product ID to collect variants
    grouped = defaultdict(list)
    for _, row in df.iterrows():
        key = (row["PRODUCT NAME"], int(row["PRODUCT ID"]))
        grouped[key].append(row)

    for (product_name, template_id), rows in grouped.items():
        variant_data = []
        for row in rows:
            try:
                front_id = upload_image(row["FRONT DESIGN"])
                back_id = upload_image(row["BACK DESIGN"])
                label_url = row.get("INSIDE NECK LABEL URL", None)
                label_id = (
                    upload_image(label_url)
                    if label_url and pd.notna(label_url)
                    else None
                )

                variant_data.append(
                    {
                        "variant_id": int(row["Variant"]),
                        "front_file_id": front_id,
                        "back_file_id": back_id,
                        "label_file_id": label_id,
                        "retail_price": "29.99",
                    }
                )
            except Exception as e:
                print(
                    f"⚠️ Skipping variant in product '{product_name}' due to error: {e}"
                )
                continue

        if variant_data:
            create_product_from_template(template_id, variant_data, product_name)
        else:
            print(
                f"❌ Skipping product '{product_name}' because no valid variants could be prepared."
            )


if __name__ == "__main__":
    # Uncomment and replace with your actual file path
    process_file("./products1.csv")
    # process_file("products.xlsx")
    pass

import requests
import json
import os
from dotenv import load_dotenv

# Load API keys from the .env file
load_dotenv()

WC_KEY = os.getenv('WC_KEY')
WC_SECRET = os.getenv('WC_SECRET')
BASE_URL = "https://pathossub.com/wp-json/wc/v3"

# Relative path for saving the output file
OUTPUT_DIR = "data/raw"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "PATHOS_RAW_EVERYTHING.json")

def fetch_all_products():
    print("Starting data fetch from WooCommerce...")
    
    # Create directory if it does not exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    all_products = []
    
    # Request the first page just to read headers and get the total number of pages
    url = f"{BASE_URL}/products?per_page=100&page=1&status=any"
    response = requests.get(url, auth=(WC_KEY, WC_SECRET))
    
    if response.status_code != 200:
        print(f"API Error! Status code: {response.status_code}")
        print("Check if the keys in the .env file are correct.")
        return
        
    total_pages = int(response.headers.get('X-WP-TotalPages', 1))
    total_items = int(response.headers.get('X-WP-Total', 0))
    
    print(f"Found {total_items} products in total, across {total_pages} pages.")
    
    # Loop through and download all pages
    for page in range(1, total_pages + 1):
        print(f"Downloading Page {page} of {total_pages}...")
        
        page_url = f"{BASE_URL}/products?per_page=100&page={page}&status=any"
        res = requests.get(page_url, auth=(WC_KEY, WC_SECRET))
        
        if res.status_code == 200:
            page_data = res.json()
            all_products.extend(page_data)
            print(f"   Page {page} fetched {len(page_data)} records.")
        else:
            print(f"   Error on page {page}! Status code: {res.status_code}")

    print("\n" + "="*50)
    print(f"FINISHED! Successfully collected {len(all_products)} products/variants.")
    print("="*50)

    # Save data to the data/raw folder
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_products, f, ensure_ascii=False, indent=4)
        
    print(f"Data successfully saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    # Safety check: Ensure keys are loaded before proceeding
    if not WC_KEY or not WC_SECRET:
        print("Error: WooCommerce keys (WC_KEY / WC_SECRET) not found.")
        print("Please ensure your .env file is correctly configured in the root directory.")
    else:
        fetch_all_products()
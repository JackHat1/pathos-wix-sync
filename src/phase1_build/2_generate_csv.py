import pandas as pd
import requests
import base64
import os
import time
import json
from dotenv import load_dotenv

# Load API keys from the .env file
load_dotenv()

# ================= CONFIGURATION & KEYS =================
FREEIMAGE_KEY = os.getenv('FREEIMAGE_KEY')

INPUT_JSON = "data/raw/PATHOS_RAW_EVERYTHING.json"  
OUTPUT_CSV = "data/output/WIX_BASE_PRODUCTS.csv"    
CACHE_FILE = "data/images_cache/img_cache.json" 
# =======================================================

COLORS_MAP = {
    "grey": "#808080:Grey", "gray": "#808080:Grey", "black": "#000000:Black",
    "cream": "#FFFDD0:Cream", "red": "#FF0000:Red", "blue": "#0000FF:Blue",
    "green": "#008000:Green", "brown": "#8B4513:Brown", "white": "#FFFFFF:White",
    "carbon": "#333333:Carbon", "yellow": "#FFFF00:Yellow", "orange": "#FFA500:Orange",
    "pink": "#FFC0CB:Pink"
}

WIX_COLUMNS = [
    "handleId", "fieldType", "name", "description", "productImageUrl", "collection", "sku", 
    "ribbon", "price", "surcharge", "visible", "discountMode", "discountValue", "inventory", 
    "weight", "cost", "productOptionName1", "productOptionType1", "productOptionDescription1", 
    "productOptionName2", "productOptionType2", "productOptionDescription2", "additionalInfoTitle1", 
    "additionalInfoDescription1", "additionalInfoTitle2", "additionalInfoDescription2", "brand"
]

# Ensure necessary directories exist
os.makedirs("data/images_cache", exist_ok=True)
os.makedirs("data/output", exist_ok=True)

# Load Image Cache
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        try: 
            img_cache = json.load(f)
        except: 
            img_cache = {}
else:
    img_cache = {}

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(img_cache, f)

def format_color(c_val):
    c_lower = str(c_val).lower().strip()
    return COLORS_MAP.get(c_lower, f"#000000:{str(c_val).capitalize()}")

def download_and_upload(img_url, filename):
    if not img_url or str(img_url).lower() == 'nan': 
        return ""
    
    local_path = os.path.join("data/images_cache", filename)
    
    # 1. Check Cache
    if filename in img_cache:
        return img_cache[filename]
        
    # 2. Download locally if it does not exist
    if not os.path.exists(local_path):
        try:
            res = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if res.status_code == 200 and len(res.content) > 100:
                with open(local_path, 'wb') as f:
                    f.write(res.content)
            else:
                return ""
        except:
            return ""

    # 3. Upload to FreeImage Host
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        for attempt in range(3):
            try:
                print(f"      [FreeImage] Uploading: {filename} ...", end=" ", flush=True)
                with open(local_path, "rb") as f:
                    file_bytes = f.read()
                    if not file_bytes: 
                        return "" 
                    
                    img_data = base64.b64encode(file_bytes).decode('utf-8')
                    payload = {"key": FREEIMAGE_KEY, "source": img_data, "action": "upload", "format": "json"}
                    
                    res = requests.post("https://freeimage.host/api/1/upload", data=payload, timeout=25)
                    
                    if res.status_code == 200:
                        img_url_new = res.json()["image"]["url"]
                        img_cache[filename] = img_url_new
                        save_cache()
                        print("OK")
                        time.sleep(1.5) 
                        return img_url_new
            except Exception as e:
                print(f"Upload error. Attempt {attempt+1}/3...")
                time.sleep(5)
    return ""

def generate_csv():
    print("Starting CSV Generation and Image Upload Process...")
    
    if not FREEIMAGE_KEY:
        print("Error: FREEIMAGE_KEY not found in .env file!")
        return

    try:
        with open(INPUT_JSON, 'r', encoding='utf-8') as f:
            products = json.load(f)
    except FileNotFoundError:
        print(f"Error: {INPUT_JSON} not found. Did you run the fetch script first?")
        return

    wix_rows = []
    
    for idx, prod in enumerate(products, 1):
        parent_sku = str(prod.get('sku') or prod.get('id')).strip()
        name = prod.get('name', '')
        raw_desc = prod.get('description', '')
        parent_price = str(prod.get('price') or '0.0').replace(',', '.')

        print(f"\n[{idx}/{len(products)}] Processing: {name} (SKU: {parent_sku})")

        # --- Process Parent Product Images ---
        main_img = prod.get('main_image', '') or (prod.get('images', [{}])[0].get('src', '') if prod.get('images') else '')
        gallery_imgs = prod.get('gallery_images', [])
        
        wix_links = []
        if main_img:
            link = download_and_upload(main_img, f"{parent_sku}.webp")
            if link: wix_links.append(link)
        
        for i, g_img in enumerate(gallery_imgs):
            link = download_and_upload(g_img, f"{parent_sku}_{i+1}.webp")
            if link and link not in wix_links: 
                wix_links.append(link)

        # --- Analyze Variants ---
        variants = prod.get('variations', [])
        opt_names = []
        opt_values_map = {}
        variant_rows = []
        
        for var in variants:
            current_variant_options = {}
            for attr in var.get('attributes', []):
                a_name = "Size" if attr.get('name') == "Μέγεθος" else attr.get('name', '')
                a_val = attr.get('option', '')
                
                if a_name not in opt_names:
                    opt_names.append(a_name)
                    opt_values_map[a_name] = set()
                opt_values_map[a_name].add(a_val)
                
                if a_name.lower() == 'color':
                    a_val = format_color(a_val)
                current_variant_options[a_name] = a_val

            v_sku = str(var.get('sku', '')).strip()
            v_main_img = var.get('main_image', '')
            v_img_link = ""
            
            if v_main_img:
                v_img_link = download_and_upload(v_main_img, f"{v_sku}.webp")
                # Add variant image to main gallery if not exists
                if v_img_link and v_img_link not in wix_links:
                    wix_links.append(v_img_link)

            # Limit to 15 images per product (Wix constraint)
            wix_links = wix_links[:15]
            
            # If variant image was cut off by the limit, remove its link
            if v_img_link not in wix_links:
                v_img_link = ""

            v_row = {col: "" for col in WIX_COLUMNS}
            v_row["handleId"] = parent_sku
            v_row["fieldType"] = "Variant"
            v_row["sku"] = v_sku
            v_row["inventory"] = "InStock" if var.get('stock_status') == 'instock' else "OutOfStock"
            v_row["visible"] = "TRUE"
            v_row["productImageUrl"] = v_img_link

            if len(opt_names) > 0: 
                v_row["productOptionDescription1"] = current_variant_options.get(opt_names[0], "")
            if len(opt_names) > 1: 
                v_row["productOptionDescription2"] = current_variant_options.get(opt_names[1], "")

            variant_rows.append(v_row)

        # --- Generate Parent Product Row ---
        p_row = {col: "" for col in WIX_COLUMNS}
        p_row["handleId"] = parent_sku
        p_row["fieldType"] = "Product"
        p_row["name"] = name
        p_row["description"] = "<p>&nbsp;</p>"
        p_row["productImageUrl"] = ";".join(wix_links)
        p_row["sku"] = parent_sku
        p_row["price"] = parent_price
        p_row["visible"] = "TRUE"
        p_row["inventory"] = "InStock"
        p_row["brand"] = "Pathos"
        
        p_row["additionalInfoTitle1"] = "Description"
        p_row["additionalInfoDescription1"] = raw_desc 
        
        parent_opt_str = []
        for a_name in opt_names:
            vals = list(opt_values_map[a_name])
            if a_name.lower() == 'color': 
                vals = [format_color(v) for v in vals]
            parent_opt_str.append(";".join(vals))
            
        if len(opt_names) > 0:
            p_row["productOptionName1"] = opt_names[0]
            p_row["productOptionType1"] = "COLOR" if opt_names[0].lower() == "color" else "DROP_DOWN"
            p_row["productOptionDescription1"] = parent_opt_str[0]
        if len(opt_names) > 1:
            p_row["productOptionName2"] = opt_names[1]
            p_row["productOptionType2"] = "COLOR" if opt_names[1].lower() == "color" else "DROP_DOWN"
            p_row["productOptionDescription2"] = parent_opt_str[1]
            
        wix_rows.append(p_row)
        wix_rows.extend(variant_rows)

    df = pd.DataFrame(wix_rows, columns=WIX_COLUMNS)
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    
    print("-" * 50)
    print(f"PROCESS COMPLETED! File generated at: {OUTPUT_CSV}")

if __name__ == "__main__":
    generate_csv()
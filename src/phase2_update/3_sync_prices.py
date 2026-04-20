import pandas as pd
import json
import os

# ================= CONFIGURATION =================
INPUT_CSV = "data/output/WIX_BASE_PRODUCTS.csv"
INPUT_JSON = "data/raw/PATHOS_RAW_EVERYTHING.json"
INPUT_EXCEL = "data/raw/PRICELIST 2026.xlsx"
OUTPUT_CSV = "data/output/WIX_FINAL_2026.csv"

# --- PRICE SOURCE SWITCH ---
# Choose where the prices should come from:
# 'JSON'  -> Only gets prices from the WooCommerce website.
# 'EXCEL' -> Only gets prices from the 2026 Pricelist Excel file.
# 'BOTH'  -> Gets prices from JSON, but if the product exists in Excel, the Excel price overwrites it.
PRICE_SOURCE = 'BOTH'  
# =================================================

def main():
    print(f"Starting Price Sync... Mode selected: {PRICE_SOURCE}")

    excel_prices = {}
    json_prices = {}

    # 1. Load Prices from Excel (if selected)
    if PRICE_SOURCE in ['EXCEL', 'BOTH']:
        if os.path.exists(INPUT_EXCEL):
            try:
                # Read the Excel file
                df_excel = pd.read_excel(INPUT_EXCEL, dtype=str)
                for _, row in df_excel.iterrows():
                    sku = str(row.get('CODE', '')).strip()
                    price_eshop = str(row.get('Ε-SHOP', '')).replace(',', '.').strip()
                    
                    if sku and price_eshop and price_eshop.lower() != 'nan':
                        try:
                            excel_prices[sku] = float(price_eshop)
                        except ValueError:
                            pass
                print(f"Loaded {len(excel_prices)} prices from Excel.")
            except Exception as e:
                print(f"Error reading Excel file: {e}")
        else:
            print(f"Warning: Excel file not found at {INPUT_EXCEL}!")

    # 2. Load Prices from JSON (if selected)
    if PRICE_SOURCE in ['JSON', 'BOTH']:
        if os.path.exists(INPUT_JSON):
            with open(INPUT_JSON, 'r', encoding='utf-8') as f:
                pathos_data = json.load(f)
            for item in pathos_data:
                sku = str(item.get('sku', '')).strip()
                price = item.get('retail_price') or item.get('price')
                if sku and price is not None:
                    json_prices[sku] = float(str(price).replace(',', '.'))
                
                # Also read prices for variations
                for var in item.get('variations', []):
                    v_sku = str(var.get('sku', '')).strip()
                    v_price = var.get('retail_price') or var.get('price')
                    if v_sku and v_price is not None:
                        json_prices[v_sku] = float(str(v_price).replace(',', '.'))
            print(f"Loaded {len(json_prices)} prices from JSON.")
        else:
            print(f"Warning: JSON file not found at {INPUT_JSON}!")

    # 3. Combine prices based on the selected Mode
    if PRICE_SOURCE == 'BOTH':
        # Merge both dictionaries. If a key exists in both, Excel overwrites JSON.
        final_target_prices = {**json_prices, **excel_prices}
    elif PRICE_SOURCE == 'EXCEL':
        final_target_prices = excel_prices
    else:
        final_target_prices = json_prices

    print(f"Total unique prices ready to be applied: {len(final_target_prices)}")

    # 4. Load the Base CSV generated from Phase 1
    if not os.path.exists(INPUT_CSV):
        print(f"Error: CSV file not found at {INPUT_CSV}. Please run Phase 1 first.")
        return

    df = pd.read_csv(INPUT_CSV, dtype=str, on_bad_lines='skip')
    df['sku_str'] = df['sku'].astype(str).str.strip()

    # Map the correct prices to the dataframe
    df['target_price'] = df['sku_str'].map(final_target_prices)

    # 5. Find the Base Price for each Product (to calculate Surcharges later)
    base_prices = {}
    for _, row in df.iterrows():
        if row['fieldType'] == 'Product':
            handle = str(row['handleId'])
            if pd.notna(row['target_price']):
                base_prices[handle] = float(row['target_price'])
            else:
                try:
                    base_prices[handle] = float(row['price'])
                except:
                    base_prices[handle] = 0.0

    # 6. Wix Logic Application (Collections and Surcharges)
    def update_row(row):
        # --- Collection Logic ---
        current_collections = []
        if pd.notna(row['collection']):
            current_collections = [c.strip() for c in str(row['collection']).split(';') if c.strip()]
        
        # Add "ALL SPEARGUNS" category if applicable
        if "OPEN SPEARGUNS" in current_collections or "CLOSE SPEARGUNS" in current_collections:
            if "ALL SPEARGUNS" not in current_collections:
                current_collections.append("ALL SPEARGUNS")
        
        updated_collection = ";".join(current_collections)

        # --- Surcharge Logic ---
        handle = str(row['handleId'])
        f_type = str(row['fieldType'])
        target = row['target_price']
        base = base_prices.get(handle, 0.0)
        
        new_price = row['price'] if pd.notna(row['price']) else ''
        new_surcharge = row['surcharge'] if pd.notna(row['surcharge']) else ''
        
        if pd.notna(target):
            target = float(target)
            if f_type == 'Product':
                new_price = target
            elif f_type == 'Variant':
                diff = target - base
                new_price = '' # Wix requires blank price for variants
                new_surcharge = round(diff, 2) if diff != 0 else ''

        return pd.Series([updated_collection, new_price, new_surcharge])

    print("Calculating Wix Surcharges and updating collections...")
    df[['collection', 'price', 'surcharge']] = df.apply(update_row, axis=1)

    # 7. Wix requires the 'visible' column to be fully capitalized (TRUE / FALSE)
    if 'visible' in df.columns:
        df['visible'] = df['visible'].astype(str).str.upper()

    # Clean up and export
    df = df.drop(columns=['sku_str', 'target_price'])
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    
    print("-" * 50)
    print(f"PROCESS COMPLETED! The ultimate Wix file is ready at: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
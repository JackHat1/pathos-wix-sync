#  Pathos WooCommerce to Wix Migrator & Sync

A robust, two-phase Python pipeline designed to extract product data from a WooCommerce store, process images, and generate a fully formatted CSV ready for Wix Stores import. It also includes a syncing mechanism to update prices using either the live WooCommerce data or a local Excel pricelist.

##  Features

* **Automated API Extraction:** Fetches all products and variations via the WooCommerce REST API.
* **Image Processing & CDN:** Downloads images locally, caches them (`img_cache.json`), and re-uploads them to FreeImage to create Wix-compatible CDN links. Enforces the 15-image limit per product.
* **Wix Structuring:** Formats HandleIds, fieldTypes, options, and automatically calculates required `surcharge` values for product variants.
* **Dynamic Price Syncing:** Easily update your Wix catalog prices using either live WooCommerce data or a local `.xlsx` pricelist file.

##  Project Architecture

```text
pathos-wix-sync/
├── src/
│   ├── phase1_build/
│   │   ├── 1_fetch_woo_to_json.py    # Fetches raw data from WooCommerce
│   │   └── 2_generate_csv.py         # Generates the base Wix CSV & handles images
│   └── phase2_update/
│       └── 3_sync_prices.py          # Updates prices and calculates variant surcharges
├── data/
│   ├── raw/                          # Stores the fetched JSON and Excel pricelists
│   ├── images_cache/                 # Stores downloaded images and the cache JSON
│   └── output/                       # The final generated CSV files for Wix
├── .env                              # API Keys (Not tracked in Git)
├── .env.example                      # Template for API Keys
└── requirements.txt                  # Python dependencies
```

##  Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/pathos-wix-sync.git](https://github.com/YOUR_USERNAME/pathos-wix-sync.git)
   cd pathos-wix-sync
   ```

2. **Install dependencies:**
   ```bash
   python -m pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Copy the `.env.example` file and rename it to `.env`. Fill in your actual API keys:
   ```env
   WC_KEY=your_woocommerce_consumer_key
   WC_SECRET=your_woocommerce_consumer_secret
   FREEIMAGE_KEY=your_freeimage_api_key
   ```

##  Usage Guide

The pipeline is split into two distinct phases depending on your needs.

### Phase 1: Build the Catalog
Run this when you need to fetch fresh data from the website and process new images.

```bash
# 1. Fetch raw data from WooCommerce to data/raw/PATHOS_RAW_EVERYTHING.json
python src/phase1_build/1_fetch_woo_to_json.py

# 2. Upload images and generate the base CSV in data/output/WIX_BASE_PRODUCTS.csv
python src/phase1_build/2_generate_csv.py
```

### Phase 2: Sync Prices & Finalize
Run this to update prices and calculate Wix variant surcharges. You can configure where the prices come from by editing the `PRICE_SOURCE` variable at the top of `3_sync_prices.py` (`'JSON'`, `'EXCEL'`, or `'BOTH'`).

Ensure you have your pricelist (e.g., `PRICELIST 2026.xlsx`) inside the `data/raw/` folder if you are using the Excel mode.

```bash
# 3. Generate the final import-ready CSV in data/output/WIX_FINAL_2026.csv
python src/phase2_update/3_sync_prices.py
```

## ⚠️ Security Notice
Never commit your `.env` file or your raw pricing data to version control. The included `.gitignore` is configured to keep your API keys and `data/` directories safe.

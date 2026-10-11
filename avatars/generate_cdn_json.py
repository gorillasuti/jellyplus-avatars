import os
import json
import urllib.parse

# Public repository configuration
GITHUB_USER = "gorillasuti"
REPO_NAME = "jellyplus-images"
BRANCH = "main"

# Exclude repository/system directories and non-category folders
IGNORED_DIRS = {".git", ".github", ".vscode", "__pycache__", "node_modules"}

def generate_exact_catalog():
    # Use relative anchor to the current script file
    root_dir = os.path.dirname(os.path.realpath(__file__))
    
    cdn_base = f"https://cdn.jsdelivr.net/gh/{GITHUB_USER}/{REPO_NAME}@{BRANCH}/avatars"
    
    # Collect only valid category folders
    categories = sorted([
        d for d in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, d))
        and not d.startswith('.')
        and d not in IGNORED_DIRS
    ])

    folder_counts = {}
    catalog_entries = {}
    total_items = 0

    for category in categories:
        category_path = os.path.join(root_dir, category)
        images = []

        # Find only .webp images, ignoring hidden files
        files = sorted([
            f for f in os.listdir(category_path)
            if f.lower().endswith('.webp') and not f.startswith('.')
        ])
        
        for file in files:
            exact_name, _ = os.path.splitext(file)
            
            # URL-encode folder and file name for web/CDN safety
            safe_category = urllib.parse.quote(category)
            safe_file = urllib.parse.quote(file)
            
            images.append({
                "name": exact_name,
                "folder": category,
                "url": f"{cdn_base}/{safe_category}/{safe_file}"
            })

        if images:
            catalog_entries[category] = images
            folder_counts[category] = len(images)
            total_items += len(images)

    # Compose payload with metadata headers followed by folder arrays
    catalog = {
        "total_items": total_items,
        "folder_counts": folder_counts,
        "folders": list(catalog_entries.keys()),
        **catalog_entries
    }

    output_path = os.path.join(root_dir, 'avatars_cdn.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"[OK] avatars_cdn.json generated successfully ({total_items} items across {len(catalog_entries)} folders).")

if __name__ == "__main__":
    generate_exact_catalog()
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed

def convert_single_file(task):
    """
    Worker task: converts source PNG to target WebP using FFmpeg.
    """
    src_path, dest_path = task
    
    # FFmpeg WebP lossless command with maximum compression search
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", src_path,
        "-c:v", "libwebp",
        "-lossless", "1",
        "-compression_level", "8",
        dest_path
    ]
    
    try:
        res = subprocess.run(cmd)
        return res.returncode == 0
    except Exception:
        return False

def main():
    root_dir = os.path.dirname(os.path.realpath(__file__))
    tasks = []

    # Exclude system, hidden, and previously optimized output folders
    ignored_patterns = {'.git', '.github', '__pycache__', '.vscode'}

    for dirpath, dirs, filenames in os.walk(root_dir):
        # Prune search tree in-place
        dirs[:] = [
            d for d in dirs 
            if d not in ignored_patterns and not d.endswith("-optimized")
        ]
        
        # Skip the root folder itself if there are raw images floating in it
        if os.path.abspath(dirpath) == os.path.abspath(root_dir):
            continue

        png_files = [f for f in filenames if f.lower().endswith(".png")]
        if not png_files:
            continue

        # Determine relative directory path and target "-optimized" folder name
        rel_dir = os.path.relpath(dirpath, root_dir)
        first_segment = rel_dir.split(os.sep)[0]
        
        # Output root destination: "parent-optimized"
        optimized_parent_name = f"{first_segment}-optimized"
        
        # Preserve sub-directory structure inside the optimized folder if nested deeper
        sub_path = os.path.relpath(dirpath, os.path.join(root_dir, first_segment))
        if sub_path == ".":
            dest_folder = os.path.join(root_dir, optimized_parent_name)
        else:
            dest_folder = os.path.join(root_dir, optimized_parent_name, sub_path)

        os.makedirs(dest_folder, exist_ok=True)

        for filename in png_files:
            src_file = os.path.join(dirpath, filename)
            stem, _ = os.path.splitext(filename)
            dest_file = os.path.join(dest_folder, f"{stem}.webp")
            tasks.append((src_file, dest_file))

    total = len(tasks)
    if total == 0:
        print("[!] No PNG files found in subdirectories.")
        return

    print(f"Found {total} PNGs across subfolders.")
    print("Converting across all available CPU cores...")

    completed = 0
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(convert_single_file, task): task for task in tasks}
        for future in as_completed(futures):
            completed += 1
            if completed % 10 == 0 or completed == total:
                percent = (completed / total) * 100
                print(f"Progress: {completed}/{total} ({percent:.1f}%)")

    print("\n[OK] All folders processed and organized into their respective '-optimized' directories!")

if __name__ == "__main__":
    main()
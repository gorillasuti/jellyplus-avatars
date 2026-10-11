import os
import re
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed

EXTENSIONS = {'.gif', '.webp', '.jpg', '.jpeg', '.png', '.jfif', '.bmp'}

def sanitize_stem(stem):
    """
    Cleans ugly scraper hash signatures while leaving standard names like 'nagisa--2' intact.
    """
    cleaned = stem

    # 1. Strip raw hex-encoded URLs or Wattpad/Discord hashes (>= 16 hex chars)
    cleaned = re.sub(r'[-_]?[0-9a-fA-F]{16,}', '', cleaned)

    # 2. Strip Tumblr CDN hash segments: 'tumblr_[hex/alphanumeric]_[size]'
    cleaned = re.sub(r'[-_]?tumblr_[0-9a-zA-Z]+(_\d+)?', '', cleaned, flags=re.IGNORECASE)

    # 3. Strip trailing resolution suffixes (e.g. '_540', '_1280', '-400x400')
    cleaned = re.sub(r'[-_](\d{3,4}x\d{3,4}|\d{3,4})$', '', cleaned)

    # 4. Clean dangling hyphens or underscores left behind
    cleaned = re.sub(r'[-_]+$', '', cleaned).strip()

    # If the regex stripped away the entire filename, keep a safe shortened fallback
    if not cleaned or len(cleaned) < 2:
        cleaned = stem[:20].rstrip('-_')

    return cleaned

def get_unique_target_path(dirpath, raw_stem, ext='.webp'):
    """Generates a clean destination path, avoiding file overwrites."""
    clean_stem = sanitize_stem(raw_stem)
    target_path = os.path.join(dirpath, clean_stem + ext)
    
    counter = 1
    # Avoid collision with existing files that aren't the file itself
    while os.path.exists(target_path):
        target_path = os.path.join(dirpath, f"{clean_stem}-{counter}{ext}")
        counter += 1

    return target_path

def convert_image(file_path):
    folder = os.path.dirname(file_path)
    raw_stem, _ = os.path.splitext(os.path.basename(file_path))
    
    # Generate clean, unique destination name
    target_webp = get_unique_target_path(folder, raw_stem, ext='.webp')
    temp_out = os.path.join(folder, f"__tmp_{os.path.basename(file_path)}.webp")

    is_gif = file_path.lower().endswith('.gif')

    # Detect animated WebP / GIF
    probe = subprocess.run(
        ['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
         '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', file_path],
        capture_output=True, text=True
    )
    is_animated = is_gif or (probe.stdout.strip().isdigit() and int(probe.stdout.strip()) > 1)

    if is_animated:
        cmd = [
            'ffmpeg', '-y', '-v', 'error',
            '-t', '4',
            '-i', file_path,
            '-vf', "fps=12,crop=w='min(iw,ih)':h='min(iw,ih)',scale=300:300",
            '-c:v', 'libwebp',
            '-lossless', '0',
            '-quality', '62',
            '-compression_level', '6',
            '-loop', '0',
            '-auto-alt-ref', '1',
            '-map_metadata', '-1',
            temp_out
        ]
    else:
        cmd = [
            'ffmpeg', '-y', '-v', 'error',
            '-i', file_path,
            '-vf', "crop=w='min(iw,ih)':h='min(iw,ih)',scale=300:300",
            '-c:v', 'libwebp',
            '-lossless', '0',
            '-quality', '75',
            '-compression_level', '6',
            '-map_metadata', '-1',
            temp_out
        ]

    try:
        res = subprocess.run(cmd)
        if res.returncode == 0 and os.path.exists(temp_out) and os.path.getsize(temp_out) > 0:
            if os.path.abspath(file_path) != os.path.abspath(target_webp):
                if os.path.exists(file_path):
                    os.remove(file_path)
            os.replace(temp_out, target_webp)
            return True
        else:
            if os.path.exists(temp_out):
                os.remove(temp_out)
            return False
    except Exception:
        if os.path.exists(temp_out):
            os.remove(temp_out)
        return False

def main():
    root = os.path.dirname(os.path.realpath(__file__))
    images = []

    for dirpath, dirs, filenames in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {'.git', '.github', '__pycache__', '.vscode'}]
        for f in filenames:
            if f.startswith('__tmp_'):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in EXTENSIONS:
                images.append(os.path.join(dirpath, f))

    total = len(images)
    print(f"Starting conversion & name sanitization for {total} files...")

    done = 0
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(convert_image, img): img for img in images}
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0 or done == total:
                print(f"Processed: {done}/{total} ({(done/total)*100:.1f}%)")

    print("\n[OK] Processing and sanitization complete!")

if __name__ == '__main__':
    main()
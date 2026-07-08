import os
import io
from PIL import Image


def compress_jpeg_to_50kb(input_path, output_path, target_kb=50):
    if not os.path.exists(input_path):
        print(f"Error: Could not find file at {input_path}")
        return

    # 1. Open the source JPEG image
    img = Image.open(input_path)

    # Ensure it's in regular RGB color mode
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # 3. Dynamic Compression Loop (Varying resolution and quality together)
    max_dimension = 1200
    quality = 75
    target_bytes = target_kb * 1024

    while True:
        # Create a fresh copy and scale dimensions down proportionally
        img_copy = img.copy()
        img_copy.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        # Test save to memory buffer
        buffer = io.BytesIO()
        img_copy.save(
            buffer,
            "JPEG",
            quality=quality,
            optimize=True,
            subsampling='4:2:0'  # Squeezes data weight without sacrificing brightness sharpness
        )
        current_size = buffer.tell()

        # Check if the target file size budget is hit
        if current_size <= target_bytes or (quality <= 25 and max_dimension <= 600):
            with open(output_path, 'wb') as f:
                f.write(buffer.getvalue())
            break

        # Step down parameters dynamically based on remaining file weight
        if quality > 40:
            quality -= 5
        else:
            max_dimension -= 100
            quality = 55  # Reset quality floor for the smaller dimension footprint

    final_size_kb = os.path.getsize(output_path) / 1024
    print("\n" + "="*45)
    print(" JPEG-TO-JPEG COMPRESSION SUCCESSFUL ")
    print("="*45)
    print(f"Destination:  {output_path}")
    print(f"Final Size:   {final_size_kb:.2f} KB")
    print(f"Dimensions:   {img_copy.width}x{img_copy.height} px")
    print(f"Final Quality: {quality}%")
    print("="*45)

# --- Execute ---
# Provide your input JPEG path and desired output path
input_file = "my_photo.jpg"
output_file = "photo_50kb.jpeg"

compress_jpeg_to_50kb(input_file, output_file, target_kb=50)

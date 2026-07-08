# 1. Install the required libraries

import rawpy
from PIL import Image

def convert_dng_to_jpeg(dng_path, output_jpeg_path):
    # 2. Open the RAW DNG file
    with rawpy.imread(dng_path) as raw:
        # 3. Postprocess demosaics the raw Bayer matrix into clean RGB channels
        # half_size=True can be used if you want to speed up processing for previews
        rgb_array = raw.postprocess(use_camera_wb=True)

    # 4. Convert the resulting numpy array into a Pillow Image
    img = Image.fromarray(rgb_array)

    # 5. Save it out as a regular compressed file
    img.save(output_jpeg_path, "JPEG", quality=85)
    print(f"Successfully converted DNG to JPEG: {output_jpeg_path}")

# Example usage:
convert_dng_to_jpeg("", "")
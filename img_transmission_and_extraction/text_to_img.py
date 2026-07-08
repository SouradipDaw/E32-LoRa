#!/usr/bin/env python3
import sys
from PIL import Image
import io

def text_to_image(input_txt_path, output_jpeg_path):
    try:
        # 1. Read the Hex text instructions out of the received file
        with open(input_txt_path, "r") as text_file:
            hex_text_instructions = text_file.read().strip()
            
        if not hex_text_instructions:
            print("Error: The text file is empty.")
            return

        # 2. Convert Hex characters back into raw binary bytes
        jpeg_bytes = bytes.fromhex(hex_text_instructions)
        
        # 3. Verify the data is valid JPEG data before saving
        # (JPEG always starts with 'ffd8' and ends with 'ffd9')
        if not hex_text_instructions.startswith("ffd8"):
            print("⚠️ Warning: Text data does not begin with a valid JPEG header.")
            print("The file might be corrupted or missing its initial packets.")
        
        # 4. Write the binary data back to a new JPEG file
        with open(output_jpeg_path, "wb") as image_file:
            image_file.write(jpeg_bytes)
            
        print("--- Reconstruction Successful ---")
        print(f"Source Text:   {input_txt_path} ({len(hex_text_instructions)} characters)")
        print(f"Output Image:  {output_jpeg_path} ({len(jpeg_bytes)} bytes)")
        
        # Optional: Test open it to make sure the Pi can read it
        with Image.open(output_jpeg_path) as img:
            print(f"Image details: {img.size[0]}x{img.size[1]} pixels, Format: {img.format}")

    except FileNotFoundError:
        print(f"Error: The text file '{input_txt_path}' was not found.")
    except ValueError:
        print("Error: Found non-hexadecimal characters in the text file. Decryption failed.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # You can change these file names as needed
    INPUT_TEXT = "extracted_payload.txt"
    OUTPUT_JPEG = "photo_output_image.jpg"
    
    text_to_image(INPUT_TEXT, OUTPUT_JPEG)

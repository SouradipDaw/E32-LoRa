#!/usr/bin/env python3
import sys

def image_to_text(jpeg_path, output_txt_path):
    try:
        # 1. Read the raw binary bytes of the existing JPEG image
        with open(jpeg_path, "rb") as image_file:
            jpeg_bytes = image_file.read()
            
        # 2. Convert binary bytes into readable Hex text characters
        hex_text_instructions = jpeg_bytes.hex()
        
        # 3. Save the text string to a file
        with open(output_txt_path, "w") as text_file:
            text_file.write(hex_text_instructions)
            
        print("--- Conversion Successful ---")
        print(f"Source Image:  {jpeg_path} ({len(jpeg_bytes)} bytes)")
        print(f"Output Text:   {output_txt_path} ({len(hex_text_instructions)} characters)")
        print("Ready for LoRa chunking and transmission.")
        
    except FileNotFoundError:
        print(f"Error: The image file '{jpeg_path}' was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # You can change these file names as needed
    INPUT_JPEG = "photo_50kb.jpeg"
    OUTPUT_TEXT = "photo_instructions.txt"
    
    image_to_text(INPUT_JPEG, OUTPUT_TEXT)

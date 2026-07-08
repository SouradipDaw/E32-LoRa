import time
from picamera2 import Picamera2

def capture_dng_image(output_path="my_photo.dng"):
    print("Initializing camera...")
    picam = Picamera2()
    
    # Configure the camera to grab the RAW stream from the sensor
    config = picam.create_still_configuration(raw={"format": "SRGGB10"}) 
    picam.configure(config)
    
    picam.start()
    print("Camera active. Allowing sensor to warm up/auto-expose...")
    time.sleep(2)
    
    print(f"Capturing frame metadata and RAW data...")
    # Capture the complete request object instead of writing a standard file
    request = picam.capture_request()
    
    print(f"Compiling and saving to {output_path}...")
    # Use the official built-in DNG compilation method
    request.save_dng(output_path)
    
    # Clean up hardware resources cleanly
    picam.stop()
    picam.close()
    print("Done!")

if __name__ == "__main__":
    capture_dng_image("my_photo.dng")

import time
from picamera2 import Picamera2

def capture_image(output_path="image.jpg"):
    print("Initializing camera...")
    # Initialize Picamera2
    picam = Picamera2()
    
    # Configure camera for a still capture
    # (By default it picks the optimal configuration)
    config = picam.create_still_configuration()
    picam.configure(config)
    
    # Start the camera sensor pipeline
    picam.start()
    print("Camera active. Allowing sensor to warm up/auto-expose...")
    
    # Wait 2 seconds for auto-exposure and white balance to settle
    time.sleep(2)
    
    print(f"Capturing image and saving to {output_path}...")
    # Capture the image and save to file
    picam.capture_file(output_path)
    
    # Clean up and close the camera session cleanly
    picam.stop()
    picam.close()
    print("Done!")

if __name__ == "__main__":
    capture_image("my_photo.jpg")

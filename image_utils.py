# C:\Users\Aditya Bhatt\Desktop\FastSAPI\15Password_Reset_email>uv add aiosmtplib
import uuid # for generating unique file names
from io import BytesIO # for working with image bytes in memory
from pathlib import Path # for file operation
from PIL import Image , ImageOps # Image for main image functionality , ImageOps for some convient image operations
PROFILE_PICS_DIR = Path("media/profile_pics")
# our fastapi app is currently async but image processing with pillow is CPUbound work. So if we do CPU
# bound work directly in async  endpoint then it blocks the evet loop  and nothing else can be processed.
# so solution is we will write a regular synchronous function and call it using run in thread pool which offloads 
# it to a separate  thread


# Process image function
def process_profile_image(content: bytes) -> str:
    with Image.open(BytesIO(content)) as original:  
        img = ImageOps.exif_transpose(original) # fixes orientation
        img = ImageOps.fit(img , (300 , 300) , method= Image.Resampling.LANCZOS) # resizes and crops the image , LANCZOS gives high quality resampling
        if img.mode in ("RGBA" , "LA" , "P"):
            img = img.convert("RGB")
        filename = f"{uuid.uuid4().hex}.jpg" # generating filename
        filepath = PROFILE_PICS_DIR/filename
        PROFILE_PICS_DIR.mkdir(parents= True , exist_ok= True)
        img.save(filepath , "JPEG" , quality = 85 , optimize = True)
    return filename
# Delete Profile Image Function
def delete_profile_image(filename: str | None) -> None:
    if filename is None:
        return
    filepath = PROFILE_PICS_DIR/filename
    if filepath.exists():
        filepath.unlink()

# C:\Users\Aditya Bhatt\Desktop\FastSAPI\15Password_Reset_email>uv add aiosmtplib
import uuid # for generating unique file names
from io import BytesIO # for working with image bytes in memory
from PIL import Image , ImageOps # Image for main image functionality , ImageOps for some convient image operations
import boto3
from  starlette.concurrency import run_in_threadpool
from config import settings


# get s3_client helper 
def _get_s3_client():
    return boto3.client(
        "s3",
        region_name = settings.s3_region,
        aws_access_key_id = (
            settings.s3_access_key_id.get_secret_value()
            if settings.s3_access_key_id
            else None
        ),
        aws_secret_access_key = (
            settings.s3_secret_access_key.get_secret_value()
            if settings.s3_secret_access_key
            else None
        ),
        endpoint_url = settings.s3_endpoint_url,
    )


# Process image function
def process_profile_image(content: bytes) -> tuple[bytes , str]:
    with Image.open(BytesIO(content)) as original:  
        img = ImageOps.exif_transpose(original) # fixes orientation
        img = ImageOps.fit(img , (300 , 300) , method= Image.Resampling.LANCZOS) # resizes and crops the image , LANCZOS gives high quality resampling
        if img.mode in ("RGBA" , "LA" , "P"):
            img = img.convert("RGB")
        filename = f"{uuid.uuid4().hex}.jpg" # generating filename
        output =  BytesIO()
        img.save(output , "JPEG" , quality = 85 , optimize = True)
        output.seek(0)
    return output.read() , filename

def _upload_to_s3(file_bytes: bytes , key : str) -> None:
    s3 = _get_s3_client()
    s3.upload_fileobj(
        BytesIO(file_bytes),
        settings.s3_bucket_name,
        key,
        ExtraArgs = {"ContentType" : "image/jpeg"},
    )
def _delete_from_s3(key: str) -> None:
    s3 = _get_s3_client()
    s3.delete_object(Bucket= settings.s3_bucket_name , Key = key)

async def upload_profile_image(file_bytes : bytes , filename : str) -> None:
    key = f"profile_pics/{filename}"
    await run_in_threadpool(_upload_to_s3 , file_bytes , key)

async def delete_profile_image(filename : str | None) -> None:
    if filename is None:
        return
    key = f"profile_pics/{filename}"
    await run_in_threadpool(_delete_from_s3 , key)
from fastapi import FastAPI, File, UploadFile, HTTPException
from minio import Minio  # Correct import from the MinIO library
from minio.error import S3Error
from typing import List
import io
from starlette.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)
minio_client = Minio(
    endpoint="42jz2y.stackhero-network.com",
    access_key="YLcZb2SWGXBcchHWIBZ3",
    secret_key="iQIXkU6jKlEG66Z8xuyhGn32kbzaIiO7lRSEd51c",
    secure=True
)


@app.get("/list-buckets")
async def list_buckets():
    try:
        # Get the list of all buckets
        buckets = minio_client.list_buckets()
        
        # Format the response
        bucket_list = [
            {"name": bucket.name, "creation_date": bucket.creation_date.isoformat()}
            for bucket in buckets
        ]
        
        return {"buckets": bucket_list}
    
    except S3Error as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create-bucket/{bucket_name}")
async def create_bucket(bucket_name: str):
    try:
        minio_client.make_bucket(bucket_name)
        return {"message": f"Bucket '{bucket_name}' created successfully"}
    except S3Error as err:
        raise HTTPException(status_code=400, detail=str(err))

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = [
    "image/jpeg",
    "image/png",
    "image/jpg",
    "image/gif",
    "image/webp",
    "image/tiff",
    "application/pdf"
]

@app.post("/upload-object/{bucket_name}")
async def upload_object(bucket_name: str, file: UploadFile = File(...)):
    try:
        # Read file data
        file_data = await file.read()
        
        # Validate file size
        if len(file_data) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds the maximum limit of {MAX_FILE_SIZE // (1024 * 1024)} MB."
            )
        
        # Validate file type
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            allowed_types = ", ".join([t.split("/")[-1] for t in ALLOWED_CONTENT_TYPES])
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed types are: {allowed_types}."
            )
        
        # Upload file to MinIO
        minio_client.put_object(
            bucket_name.strip(),  # Sanitize bucket name
            file.filename,
            data=io.BytesIO(file_data),
            length=len(file_data),
            content_type=file.content_type
        )
        
        return {"message": f"Object '{file.filename}' uploaded successfully to bucket '{bucket_name}'"}
    
    except S3Error as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/download-object/{bucket_name}/{object_name}")
async def download_object(bucket_name: str, object_name: str):
    try:
        response = minio_client.get_object(bucket_name, object_name)
        return StreamingResponse(response, media_type="application/octet-stream")
    except S3Error as err:
        raise HTTPException(status_code=404, detail=str(err))

@app.get("/list-objects/{bucket_name}")
async def list_objects(bucket_name: str):
    try:
        objects = minio_client.list_objects(bucket_name)
        object_list = [obj.object_name for obj in objects]
        return {"objects": object_list}
    except S3Error as err:
        raise HTTPException(status_code=400, detail=str(err))

@app.delete("/delete-object/{bucket_name}/{object_name}")
async def delete_object(bucket_name: str, object_name: str):
    try:
        minio_client.remove_object(bucket_name, object_name)
        return {"message": f"Object '{object_name}' deleted successfully from bucket '{bucket_name}'"}
    except S3Error as err:
        raise HTTPException(status_code=400, detail=str(err))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9000)
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status , UploadFile , Query , BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schema import PostResponse, UserCreate, UserPublic , UserPrivate , Token, UserUpdate , PaginatedPostResponse , ChangePasswordRequest , ForgetPasswordRequest, ResetPasswordRequest
from datetime import timedelta ,UTC , datetime
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func # so we can do case insensitive queries
from auth import create_access_token , hash_password ,verify_password , CurrentUser , generate_reset_token , hash_reset_token
from config import settings 

from PIL import UnidentifiedImageError
from starlette.concurrency import run_in_threadpool
from image_utils import delete_profile_image , process_profile_image
from sqlalchemy import delete as sql_delete
from email_utils import send_password_reset_email

router = APIRouter()


@router.post(
    "",
    response_model=UserPrivate,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(func.lower(models.User.username) == user.username.lower()), # ADITYA and aditya will be same as we arte usiing func for username in database
        #  for user.username we use .lower() as it is a normal string
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == user.email.lower()),
    )
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash = hash_password(user.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
# Login_for_access_time
@router.post("/token" , response_model= Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm , Depends()],
    db: Annotated[AsyncSession , Depends(get_db)],
):
# Look up user by email(case-insensitive)
# Note : OAuth2PasswordRequestForm uses "username" field , but we treat it as email
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email) == form_data.username.lower(),
        ),
    )
    user = result.scalars().first()
# Verify user exists and password is correct
# Dont reveal which one failed (Security best practice)
    if not user or not verify_password(form_data.password , user.password_hash):
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail= "Incorrect email or password",
            headers= {"WWW-Authenticate"  : "Bearer"},
        )
    # create access token with user id as subject
    access_token_expires = timedelta(minutes= settings.access_token_expire_minutes)
    access_token = create_access_token(
        data = {"sub" : str(user.id)},
        expires_delta = access_token_expires,
    )
    return Token(access_token = access_token , token_type = "bearer")

@router.get("/me" , response_model = UserPrivate)
async def get_current_user(current_user : CurrentUser):
   return current_user

@router.post("/forget-password" , status_code = status.HTTP_202_ACCEPTED)
async def forget_password(
    request_data : ForgetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)]
):
  result = await db.execute(
    select(models.User).where(
        func.lower(models.User.email) == request_data.email.lower(),
    ),
  )
  user = result.scalars().first()
  if user:
    await db.execute(
        sql_delete(models.PasswordResetToken).where(
            models.PasswordResetToken.user_id == user.id,
        ),
    )
    token = generate_reset_token()
    token_hash = hash_reset_token(token)
    expires_at = datetime.now(UTC) + timedelta(
        minutes= settings.reset_token_expire_minutes
    )
    reset_token = models.PasswordResetToken(
        user_id = user.id,
        token_hash = token_hash,
        expires_at = expires_at
    )
    db.add(reset_token)
    await db.commit()
    background_tasks.add_task(
        send_password_reset_email,
        to_email = user.email,
        username = user.username,
        token = token,
    )
    return {
        "message" : "If an account exists withb this email , you will recieve password reset instructions."
    }

@router.post("/reset-password" , status_code= status.HTTP_200_OK)
async def reset_password(
    request_data: ResetPasswordRequest,
    db: Annotated[AsyncSession , Depends(get_db)],
):
    token_hash = hash_reset_token(request_data.token)
    result = await db.execute(
       select(models.PasswordResetToken).where(
           models.PasswordResetToken.token_hash == token_hash
       )
    )
    reset_token = result.scalars().first()
    if not reset_token:
        raise HTTPException(
           status_code= status.HTTP_400_BAD_REQUEST,
           detail= "Invalid or expired reset token"
       )
    if reset_token.expires_at < datetime.now(UTC):
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail = "Invalid or expired reset token"
        )
    result = await db.execute(
        select(models.User).where(models.User.id == reset_token.user_id),
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
         status_code= status.HTTP_400_BAD_REQUEST,
         detail = "Invalid or expired reset token"  
        )
    user.password_hash = hash_password(request_data.new_password)
    await db.execute(
        sql_delete(models.PasswordResetToken).where(
            models.PasswordResetToken.user_id == user.id,
        )
    )
    await db.commit()
    return{
        "message": "Password reset successfully. You can log in with your new password"
    }


@router.patch("/me/password" , status_code = status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession , Depends(get_db)]
):
    if not verify_password(password_data.current_password , current_user.password_hash):
       raise HTTPException(
           status_code= status.HTTP_400_BAD_REQUEST,
           detail= "Current password is incorrect"
       )
    current_user.password_hash = hash_password(password_data.new_password)
    await db.execute(
        sql_delete(models.PasswordResetToken).where(
            models.PasswordResetToken.user_id == current_user.id,
        )
    )
    await db.commit()
    return {"message" : "Password changed successfully"}



@router.get("/{user_id}", response_model=UserPublic)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.get("/{user_id}/posts", response_model= PaginatedPostResponse)
async def get_user_posts(user_id: int, 
db: Annotated[AsyncSession, Depends(get_db)],
skip : Annotated[int , Query(ge = 0)] = 0,
limit: Annotated[int , Query(ge = 1 , le =100)] = settings.posts_per_page,
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    count_result = await db.execute(
        select(func.count())
        .select_from(models.Post)
        .where(models.Post.user_id == user_id),
    )
    total = count_result.scalar() or 0
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
        .offset(skip)
        .limit(limit),
    )
    posts = result.scalars().all()
    has_more = skip + len(posts) < total
    return PaginatedPostResponse(
        posts=[PostResponse.model_validate(post) for post in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )


@router.patch("/{user_id}", response_model=UserPrivate)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code= status.HTTP_403_FORBIDDEN,
            detail= "Not authorized to update this user",
        )
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if user_update.username is not None and user_update.username.lower() != user.username.lower():
        result = await db.execute(
            select(models.User).where(func.lower(models.User.username) == user_update.username.lower()),
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )
    if user_update.email is not None and user_update.email.lower() != user.email.lower():
        result = await db.execute(
            select(models.User).where(func.lower(models.User.email) == user_update.email.lower()),
        )
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email.lower()


    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, current_user: CurrentUser ,db: Annotated[AsyncSession, Depends(get_db)]):
    if user_id != current_user.id:
        raise HTTPException(
            status_code= status.HTTP_403_FORBIDDEN,
            detail= "Not authorized to delete this user",
        )   
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    old_filename = user.image_file
    await db.delete(user)
    await db.commit()
    if old_filename:
        delete_profile_image(old_filename)


@router.patch("/{user_id}/picture" , response_model = UserPrivate)
async def upload_profile_picture(
    user_id : int,
    file: UploadFile,
    current_user: CurrentUser,
    db: Annotated[AsyncSession , Depends(get_db)],
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "Not authorized to update this user's profile",
        )
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = f"File too large. Maximum size is {settings.max_upload_size_bytes // (1024*1024)}MB"
        )
    try:
        new_filename = await run_in_threadpool(process_profile_image , content) 
    except UnidentifiedImageError as err:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Invalid image file. Please upload a valid image(JPEG , PNG , GIF , WebP)",

        ) from err
    old_filename = current_user.image_file
    current_user.image_file = new_filename
    await db.commit()
    await db.refresh(current_user)
    if old_filename:
        delete_profile_image(old_filename)
    return current_user
        
# 1. The endpoint itself is asynchronous
# async def upload_profile_picture(...):

# FastAPI can run this endpoint using Python's asynchronous event loop.

# The key asynchronous operations are the ones using await.

# 2. Reading the uploaded file is asynchronous
# content = await file.read()

# UploadFile.read() is async.

# The await essentially says:

# "Start/read this file, and while I'm waiting for the I/O operation, allow the event loop to work on other tasks."

# So this is async I/O.

# 3. Checking the file size is synchronous
# if len(content) > settings.max_upload_size_bytes:

# This is ordinary Python code.

# There is no await.

# len() is extremely fast and doesn't need asynchronous execution.

# 4. This is the important part: run_in_threadpool
# new_filename = await run_in_threadpool(
#     process_profile_image,
#     content
# )

# This is a combination of async + synchronous execution.

# Your process_profile_image() is presumably a normal synchronous function, perhaps doing something like:

# def process_profile_image(content):
#     image = Image.open(...)
#     image.verify(...)
#     ...

# Image processing can involve CPU work and/or blocking file operations.

# If you directly did:

# new_filename = process_profile_image(content)

# inside your async def, the synchronous function could block the event loop.

# Instead:

# await run_in_threadpool(process_profile_image, content)

# means approximately:

# Async event loop
#        │
#        │ submit synchronous function
#        ▼
# Thread pool
#        │
#        │ process_profile_image(content)
#        ▼
#     Result
#        │
#        ▼
# Async endpoint continues

# So your async endpoint remains responsive while the synchronous image-processing function runs in a worker thread.

# 5. try/except is synchronous control flow
# try:
#     new_filename = await run_in_threadpool(...)
# except UnidentifiedImageError as err:

# The try/except itself isn't asynchronous.

# But the operation inside it contains:

# await

# So you're asynchronously waiting for the thread-pool operation, while still handling exceptions normally.

# 6. Database operations are asynchronous
# await db.commit()

# and:

# await db.refresh(current_user)

# These are async database operations.

# The application can yield control while waiting for the database.

# 7. delete_profile_image() is synchronous
# if old_filename:
#     delete_profile_image(old_filename)

# Notice there's no await.

# Therefore this is a normal synchronous function.

# If delete_profile_image() performs file-system operations, it could potentially block the event loop.

# You could also move it to the thread pool:

# if old_filename:
#     await run_in_threadpool(delete_profile_image, old_filename)

# Whether that's necessary depends on what delete_profile_image() actually does.

# So your function has this structure
# async def upload_profile_picture()
# │
# ├── current_user.id != user_id
# │       └── synchronous Python
# │
# ├── await file.read()
# │       └── ASYNC I/O
# │
# ├── len(content)
# │       └── synchronous Python
# │
# ├── await run_in_threadpool(...)
# │       └── ASYNC waiting
# │             │
# │             └── synchronous process_profile_image()
# │                   running in worker thread
# │
# ├── await db.commit()
# │       └── ASYNC database I/O
# │
# ├── await db.refresh()
# │       └── ASYNC database I/O
# │
# ├── delete_profile_image()
# │       └── synchronous
# │
# └── return current_user
# Why mix them?

# Because async and sync are good at different things:

# Operation	Type	Why
# file.read()	Async	Waiting for I/O
# len(content)	Sync	Tiny CPU operation
# process_profile_image()	Sync in thread pool	Potentially blocking image processing
# db.commit()	Async	Waiting for database
# db.refresh()	Async	Waiting for database
# delete_profile_image()	Sync	Normal filesystem function

# The main principle is:

# Use async/await for operations that can yield while waiting, and move blocking synchronous work to a thread pool when you're inside an async endpoint.

# That's exactly why you have:

# await run_in_threadpool(process_profile_image, content)

# instead of simply:

# process_profile_image(content)

# This distinction is very important when building FastAPI applications, because blocking the event loop can reduce the server's ability to handle other requests concurrently.


# Delete profile picture endpoint
@router.delete("/{user_id}/picture" , response_model = UserPrivate)
async def delete_user_picture(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession , Depends(get_db)],
):
   if current_user.id != user_id:
    raise HTTPException(
        status_code = status.HTTP_403_FORBIDDEN,
        detail = "Not authorized to delete this user's picture",
    )
    old_filename = current_user.image_file
    if old_filename is None:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "No profile picture to delete",
        )
    current_user.image_file = None
    await db.commit()

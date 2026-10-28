from io import BytesIO # for file uploads
from pathlib import Path # for reading the  test image
from unittest.mock import AsyncMock , patch # for mocking r email function
import pytest
from httpx  import AsyncClient
from tests.conftest import auth_header , create_test_user , login_user

@pytest.mark.anyio
async def test_create_user_validation_error(client : AsyncClient):
    response = await client.post(
        "api/users",
        json = {
            "username" : "testuser",
        },
    )
    assert response.status_code == 422 # unproceesable entity status  , Pydantic validation fails as required fields are missing [email and password]
    assert "email" in response.text
    assert "password" in response.text

@pytest.mark.anyio
async def test_create_user_duplicate_email(client : AsyncClient):
    await create_test_user(client)
    response = await client.post(
        "api/users",
        json = {
            "username" : "different_user",
            "email"  : "test@example.com",
            "password" : "password123",
        },
    )
    assert response.status_code == 400
    assert  response.json()["detail"] == "Email already registered"

@pytest.mark.anyio
async def test_create_user_success(client : AsyncClient):
    response = await client.post(
        "api/users",
        json = {
            "username" : "newuser",
            "email" : "newuser@example.com",
            "password" : "securepassword123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "image_path" in data
    assert "password" not in data
    assert "password_hash" not in data

@pytest.mark.anyio
async def test_upload_profile_picture(client : AsyncClient , mocked_aws):
    user = await create_test_user(client)
    token = await login_user(client)
    test_image_path = Path(__file__).parent/"test_image.jpg"
    image_bytes = test_image_path.read_bytes()
    response = await client.patch(
        f"/api/users/{user['id']}/picture",
        files = {"file" : ("profile.jpg" , BytesIO(image_bytes) , "image/jpeg")}, # here image name can be any whether profile.jpg or test_image.jpg main content is BytesIO(image_bytes) this is send on the server
        headers = auth_header(token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["image_file"] is not None
    assert data["image_file"].endswith(".jpg")
    assert "s3" in data["image_path"]
    s3_objects = mocked_aws.list_objects_v2(Bucket = "test_bucket")
    assert "Contents" in s3_objects
    assert len(s3_objects["Contents"]) == 1
    assert s3_objects["Contents"][0]["Key"].endswith(data["image_file"])

@pytest.mark.anyio
async def test_forget_pasword_sends_email(client : AsyncClient):
    await create_test_user(client)
    with patch(
        "routers.users.send_password_reset_email",
        new_callable= AsyncMock,
    ) as mock_send:
        response = await client.post(
            "api/users/forget-password",
            json = {"email" : "test@example.com"},
        )
        assert response.status_code == 202
        mock_send.assert_awaited_once()
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["to_email"] == "test@example.com"
        assert call_kwargs["username"] == "testuser"
        assert "token" in call_kwargs

    

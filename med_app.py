import asyncio
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Annotated, List, Optional
import jwt
import uvicorn
from asyncMySQL import Message, User, UserRole, DBConnection
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel
from fastapi import Form
from json import JSONDecodeError


SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Token(BaseModel):
    access_token: str
    token_type: str
    user_role: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()
app.mount("/frontend/static", StaticFiles(directory="frontend/static"), name="static")

templates = Jinja2Templates(directory="frontend/templates")


async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def get_password_hash(password):
    return pwd_context.hash(password)


async def authenticate_user(username: str, password: str) -> Optional[User]:
    user = await DBConnection().get_user(username)
    if not user:
        await DBConnection().insert_user_or_exists(username, await get_password_hash(password), role=UserRole.Client)
        return User(
            name=username,
            hashed_password=await get_password_hash(password),
            role=UserRole.Client
        )
    if not await verify_password(password, user.hashed_password):
        return None
    return user


async def create_access_token(user: User):
    encoded_jwt = jwt.encode(user.as_dict(), SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    name: str = payload.get("name")
    if name is None:
        raise credentials_exception
    user = await DBConnection().get_user(name)
    if user is None:
        raise credentials_exception
    return user


class UserCreds(BaseModel):
    username: str
    password: str


@app.post("/register")
async def register(data: UserCreds) -> bool:
    if await authenticate_user(data.username, data.password) is None:
        await DBConnection().insert_user_or_exists(data.username, pwd_context.hash(data.password))
    return True


@app.post("/login")
async def login_for_access_token(username: Annotated[str, Form()], password: Annotated[str, Form()]) -> Token:
    user = await authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = await create_access_token(user)
    return Token(access_token=access_token, token_type="bearer", user_role=user.role.name)


class UpdatesRequest(BaseModel):
    last_message_id: int


class UpdatesResponse(BaseModel):
    new_messages: List[Message]


@app.post("/updates")
async def get_updates(data: UpdatesRequest, user: Annotated[User, Depends(get_current_user)]):
    if user.role == UserRole.Client:
        print(await DBConnection().get_new_messages(user.name, data.last_message_id))
        return UpdatesResponse(new_messages = await DBConnection().get_new_messages(user.name, data.last_message_id))
    elif user.role == UserRole.Doctor:
        print(await DBConnection().get_queue(data.last_message_id))
        return UpdatesResponse(new_messages = await DBConnection().get_queue(data.last_message_id))

@app.post('/')
async def lander(request: Request):
    content_type = request.headers.get('Content-Type')
    
    if content_type is None:
        raise HTTPException(status_code=400, detail='No Content-Type provided')
    elif content_type == 'application/json':
        try:
            return await request.json()
        except JSONDecodeError:
            raise HTTPException(status_code=400, detail='Invalid JSON data')
    else:
        raise HTTPException(status_code=400, detail='Content-Type not supported')


class SendMessageRequest(BaseModel):
    message_text: str
    """For doctors only, and for them that field is required."""
    recipient: Optional[str]


@app.post("/send_message")
async def send_message(data: SendMessageRequest, user: Annotated[User, Depends(get_current_user)]) -> bool:
    if user.role == UserRole.Client:
        await DBConnection().insert_message(user.name, data.message_text)
        return True
    elif user.role == UserRole.Doctor:
        if not data.recipient:
            return False
        await DBConnection().insert_message(data.recipient, data.message_text, is_doc=True)
        #await DBConnection().mark_messages_as_answered(data.recipient)
        return True
    return False


@app.get("/")
async def default():
    return RedirectResponse("/home")


@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="home.html", context={'rooms': ["Login to select room"]})


@app.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})


@app.get("/chat", response_class=HTMLResponse)
async def get_chat(request: Request):
    return templates.TemplateResponse(request=request, name="chat.html")


async def main():
    print(await DBConnection().insert_user_or_exists("vadim", "hashed_vadim"))
    print(await DBConnection().insert_user_or_exists("doc", await get_password_hash("doc"), UserRole.Doctor))
    config = uvicorn.Config("med_app:app", host = "0.0.0.0", port = 8000, reload = True)
    server = uvicorn.Server(config)
    print(await DBConnection().insert_message("vadim2", "bibabbba"))
    print(await DBConnection().insert_message("vadim2", "second message"))
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())

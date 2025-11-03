#!/usr/bin/env python
"""
Seed curated FastAPI JWT/OAuth2 examples into the curated collection.

Adds minimal, canonical snippets with strong metadata for retrieval.
"""
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from src.rag import create_embedding_model
from src.rag.vector_store import VectorStore


def main() -> int:
    embedding = create_embedding_model()

    curated_store = VectorStore(
        embedding_model=embedding,
        collection_name="devmatrix_curated",
    )

    examples = [
        {
            "code": (
                "from datetime import datetime, timedelta\n"
                "from jose import jwt, JWTError\n"
                "from fastapi import FastAPI, Depends, HTTPException, status\n"
                "from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm\n\n"
                "SECRET_KEY = 'change_me'\n"
                "ALGORITHM = 'HS256'\n"
                "ACCESS_TOKEN_EXPIRE_MINUTES = 30\n\n"
                "oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')\n\n"
                "def create_access_token(data: dict, expires_delta: timedelta | None = None):\n"
                "    to_encode = data.copy()\n"
                "    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))\n"
                "    to_encode.update({'exp': expire})\n"
                "    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)\n\n"
                "async def get_current_user(token: str = Depends(oauth2_scheme)):\n"
                "    try:\n"
                "        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])\n"
                "        username: str | None = payload.get('sub')\n"
                "        if username is None:\n"
                "            raise HTTPException(status_code=401, detail='Invalid token')\n"
                "        return {'username': username}\n"
                "    except JWTError:\n"
                "        raise HTTPException(status_code=401, detail='Invalid token')\n\n"
                "app = FastAPI()\n\n"
                "@app.post('/token')\n"
                "async def login(form_data: OAuth2PasswordRequestForm = Depends()):\n"
                "    access_token = create_access_token({'sub': form_data.username})\n"
                "    return {'access_token': access_token, 'token_type': 'bearer'}\n\n"
                "@app.get('/users/me')\n"
                "async def read_users_me(current_user: dict = Depends(get_current_user)):\n"
                "    return current_user\n"
            ),
            "metadata": {
                "language": "python",
                "framework": "fastapi",
                "source": "official_docs",
                "tags": "jwt,oauth2,bearer,security,python-jose",
                "approved": True,
                "pattern": "fastapi_jwt_oauth2",
                "task_type": "security",
                "indexed_at": datetime.utcnow().isoformat(),
                "description": "FastAPI JWT with OAuth2PasswordBearer and token endpoints",
            },
        },
        {
            "code": (
                "from passlib.context import CryptContext\n\n"
                "pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')\n\n"
                "def verify_password(plain_password: str, hashed_password: str) -> bool:\n"
                "    return pwd_context.verify(plain_password, hashed_password)\n\n"
                "def get_password_hash(password: str) -> str:\n"
                "    return pwd_context.hash(password)\n"
            ),
            "metadata": {
                "language": "python",
                "framework": "fastapi",
                "source": "official_docs",
                "tags": "jwt,oauth2,bearer,security,passlib",
                "approved": True,
                "pattern": "fastapi_password_hashing",
                "task_type": "security",
                "indexed_at": datetime.utcnow().isoformat(),
                "description": "Password hashing utilities for JWT flows",
            },
        },
        {
            "code": (
                "from datetime import timedelta\n"
                "from fastapi import Depends\n"
                "from fastapi.security import OAuth2PasswordRequestForm\n"
                "# create_access_token as defined elsewhere\n\n"
                "ACCESS_TOKEN_EXPIRE_MINUTES = 60\n\n"
                "async def login(form_data: OAuth2PasswordRequestForm = Depends()):\n"
                "    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)\n"
                "    token = create_access_token({'sub': form_data.username}, expires_delta=expires)\n"
                "    return {'access_token': token, 'token_type': 'bearer'}\n"
            ),
            "metadata": {
                "language": "python",
                "framework": "fastapi",
                "source": "official_docs",
                "tags": "jwt,oauth2,bearer,expiry",
                "approved": True,
                "pattern": "fastapi_jwt_expiry",
                "task_type": "security",
                "indexed_at": datetime.utcnow().isoformat(),
                "description": "JWT with configurable expiration",
            },
        },
        {
            "code": (
                "from jose import JWTError\n"
                "from fastapi import Depends, HTTPException, status\n"
                "from fastapi.security import OAuth2PasswordBearer\n\n"
                "oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')\n\n"
                "async def get_current_user_strict(token: str = Depends(oauth2_scheme)):\n"
                "    try:\n"
                "        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])\n"
                "        sub = payload.get('sub')\n"
                "        if not sub:\n"
                "            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')\n"
                "        return sub\n"
                "    except JWTError:\n"
                "        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')\n"
            ),
            "metadata": {
                "language": "python",
                "framework": "fastapi",
                "source": "official_docs",
                "tags": "jwt,oauth2,security,dependency",
                "approved": True,
                "pattern": "fastapi_jwt_dependency_strict",
                "task_type": "security",
                "indexed_at": datetime.utcnow().isoformat(),
                "description": "Strict dependency to decode and validate JWT",
            },
        },
        {
            "code": (
                "# Quick test commands (documentation snippet)\n"
                "# 1) Get token\n"
                "# curl -X POST -d 'username=alice&password=secret' http://localhost:8000/token\n"
                "# 2) Access protected\n"
                "# curl -H 'Authorization: Bearer <TOKEN>' http://localhost:8000/users/me\n"
            ),
            "metadata": {
                "language": "bash",
                "framework": "fastapi",
                "source": "official_docs",
                "tags": "jwt,oauth2,curl,testing",
                "approved": True,
                "pattern": "fastapi_jwt_curl_tests",
                "task_type": "security",
                "indexed_at": datetime.utcnow().isoformat(),
                "description": "Curl commands to test JWT issue and use",
            },
        },
        {
            "code": (
                "from fastapi import FastAPI, Depends\n"
                "from fastapi.security import OAuth2PasswordRequestForm\n"
                "app = FastAPI()\n\n"
                "@app.post('/token')\n"
                "async def issue_token(form_data: OAuth2PasswordRequestForm = Depends()):\n"
                "    return {'access_token': create_access_token({'sub': form_data.username}), 'token_type': 'bearer'}\n"
            ),
            "metadata": {
                "language": "python",
                "framework": "fastapi",
                "source": "official_docs",
                "tags": "jwt,oauth2,bearer,token-endpoint",
                "approved": True,
                "pattern": "fastapi_jwt_token_endpoint_minimal",
                "task_type": "security",
                "indexed_at": datetime.utcnow().isoformat(),
                "description": "Minimal token endpoint issuing JWT",
            },
        },
        {
            "code": (
                "# curl tests for JWT flow\n"
                "curl -s -X POST -d 'username=alice&password=secret' http://localhost:8000/token | jq -r .access_token\n"
                "# TOKEN=$(...)\n"
                "# curl -s -H \"Authorization: Bearer $TOKEN\" http://localhost:8000/users/me\n"
            ),
            "metadata": {
                "language": "bash",
                "framework": "fastapi",
                "source": "official_docs",
                "tags": "jwt,curl,testing,bearer",
                "approved": True,
                "pattern": "fastapi_jwt_curl_minimal",
                "task_type": "security",
                "indexed_at": datetime.utcnow().isoformat(),
                "description": "Minimal curl tests for obtaining and using JWT",
            },
        },
    ]

    added = 0
    for ex in examples:
        curated_store.add_example(code=ex["code"], metadata=ex["metadata"]) 
        added += 1

    print(f"Seeded {added} curated JWT examples into 'devmatrix_curated'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



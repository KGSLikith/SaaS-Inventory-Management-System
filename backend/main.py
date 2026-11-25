import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "stockflow_mvp")
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
DEFAULT_LOW_STOCK_THRESHOLD = 10

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(title="StockFlow MVP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client: Optional[MongoClient] = None
db = None


def get_db():
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db


def parse_object_id(value: str, label: str = "ID") -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=400, detail=f"Invalid {label}")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    database = get_db()
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        org_id: Optional[str] = payload.get("org_id")
        if not user_id or not org_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = database.users.find_one({"_id": parse_object_id(user_id, "user ID")})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    org = database.organizations.find_one({"_id": parse_object_id(org_id, "organization ID")})
    if not org:
        raise HTTPException(status_code=401, detail="Organization not found")

    return {
        "user_id": str(user["_id"]),
        "email": user["email"],
        "name": user.get("name", ""),
        "org_id": str(org["_id"]),
        "org_name": org["name"],
        "low_stock_threshold": int(org.get("low_stock_threshold", DEFAULT_LOW_STOCK_THRESHOLD)),
    }


def serialize_product(doc: dict, threshold: int) -> dict:
    qty = int(doc.get("quantity", 0))
    item_threshold = int(doc.get("low_stock_threshold", threshold))
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "sku": doc["sku"],
        "quantity": qty,
        "price": float(doc.get("price", 0.0)),
        "low_stock_threshold": item_threshold,
        "is_low_stock": qty <= item_threshold,
        "updated_at": doc.get("updated_at"),
    }


# --- Pydantic Schemas ---

class SignupRequest(BaseModel):
    org_name: str = Field(..., min_length=2, max_length=120)
    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., min_length=3, max_length=160)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    sku: str = Field(..., min_length=1, max_length=80)
    quantity: int = Field(default=0, ge=0)
    price: float = Field(default=0.0, ge=0)
    low_stock_threshold: Optional[int] = Field(default=None, ge=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    sku: Optional[str] = Field(default=None, min_length=1, max_length=80)
    quantity: Optional[int] = Field(default=None, ge=0)
    price: Optional[float] = Field(default=None, ge=0)
    low_stock_threshold: Optional[int] = Field(default=None, ge=0)


class QuantityAdjust(BaseModel):
    delta: Optional[int] = None
    quantity: Optional[int] = Field(default=None, ge=0)


class SettingsUpdate(BaseModel):
    org_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    low_stock_threshold: int = Field(..., ge=0)


# --- Startup ---

@app.on_event("startup")
def startup_db():
    global client, db
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    db.users.create_index("email", unique=True)
    db.products.create_index([("org_id", 1), ("sku", 1)], unique=True)


# --- Auth Routes ---

@app.post("/api/auth/signup", status_code=201)
def signup(payload: SignupRequest):
    database = get_db()
    email = payload.email.strip().lower()

    if database.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email is already registered")

    now = datetime.now(timezone.utc).isoformat()
    org_result = database.organizations.insert_one(
        {
            "name": payload.org_name.strip(),
            "low_stock_threshold": DEFAULT_LOW_STOCK_THRESHOLD,
            "created_at": now,
        }
    )
    org_id = org_result.inserted_id

    try:
        user_result = database.users.insert_one(
            {
                "email": email,
                "name": payload.name.strip(),
                "password_hash": hash_password(payload.password),
                "org_id": org_id,
                "created_at": now,
            }
        )
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Email is already registered")

    token = create_access_token({"sub": str(user_result.inserted_id), "org_id": str(org_id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user_result.inserted_id),
            "email": email,
            "name": payload.name.strip(),
            "org_id": str(org_id),
            "org_name": payload.org_name.strip(),
        },
    }


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    database = get_db()
    email = payload.email.strip().lower()
    user = database.users.find_one({"email": email})

    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    org = database.organizations.find_one({"_id": user["org_id"]})
    org_name = org["name"] if org else ""

    token = create_access_token({"sub": str(user["_id"]), "org_id": str(user["org_id"])})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("name", ""),
            "org_id": str(user["org_id"]),
            "org_name": org_name,
        },
    }


# --- Dashboard Route ---

@app.get("/api/dashboard")
def get_dashboard(current_user: dict = Depends(get_current_user)):
    database = get_db()
    org_oid = parse_object_id(current_user["org_id"], "organization ID")
    default_threshold = current_user["low_stock_threshold"]

    docs = list(database.products.find({"org_id": org_oid}))
    products = [serialize_product(d, default_threshold) for d in docs]

    total_products = len(products)
    total_units = sum(p["quantity"] for p in products)
    inventory_value = round(sum(p["quantity"] * p["price"] for p in products), 2)
    low_stock_items = [p for p in products if p["is_low_stock"]]

    return {
        "org_name": current_user["org_name"],
        "low_stock_threshold": default_threshold,
        "total_products": total_products,
        "total_units": total_units,
        "inventory_value": inventory_value,
        "low_stock_count": len(low_stock_items),
        "low_stock_items": low_stock_items,
    }


# --- Product Routes ---

@app.get("/api/products")
def list_products(current_user: dict = Depends(get_current_user)):
    database = get_db()
    org_oid = parse_object_id(current_user["org_id"], "organization ID")
    threshold = current_user["low_stock_threshold"]

    docs = list(database.products.find({"org_id": org_oid}).sort("_id", -1))
    return [serialize_product(d, threshold) for d in docs]


@app.post("/api/products", status_code=201)
def create_product(payload: ProductCreate, current_user: dict = Depends(get_current_user)):
    database = get_db()
    org_oid = parse_object_id(current_user["org_id"], "organization ID")
    now = datetime.now(timezone.utc).isoformat()
    sku = payload.sku.strip().upper()
    threshold = (
        payload.low_stock_threshold
        if payload.low_stock_threshold is not None
        else current_user["low_stock_threshold"]
    )

    doc = {
        "org_id": org_oid,
        "name": payload.name.strip(),
        "sku": sku,
        "quantity": payload.quantity,
        "price": payload.price,
        "low_stock_threshold": threshold,
        "updated_at": now,
    }

    try:
        inserted = database.products.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail=f"SKU '{sku}' already exists in your organization")

    created = database.products.find_one({"_id": inserted.inserted_id})
    return serialize_product(created, current_user["low_stock_threshold"])


@app.put("/api/products/{product_id}")
def update_product(
    product_id: str,
    payload: ProductUpdate,
    current_user: dict = Depends(get_current_user),
):
    database = get_db()
    org_oid = parse_object_id(current_user["org_id"], "organization ID")
    prod_oid = parse_object_id(product_id, "product ID")

    existing = database.products.find_one({"_id": prod_oid, "org_id": org_oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if payload.name is not None:
        updates["name"] = payload.name.strip()
    if payload.sku is not None:
        updates["sku"] = payload.sku.strip().upper()
    if payload.quantity is not None:
        updates["quantity"] = payload.quantity
    if payload.price is not None:
        updates["price"] = payload.price
    if payload.low_stock_threshold is not None:
        updates["low_stock_threshold"] = payload.low_stock_threshold

    try:
        updated = database.products.find_one_and_update(
            {"_id": prod_oid, "org_id": org_oid},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="SKU already exists in your organization")

    return serialize_product(updated, current_user["low_stock_threshold"])


@app.patch("/api/products/{product_id}/quantity")
def adjust_product_quantity(
    product_id: str,
    payload: QuantityAdjust,
    current_user: dict = Depends(get_current_user),
):
    database = get_db()
    org_oid = parse_object_id(current_user["org_id"], "organization ID")
    prod_oid = parse_object_id(product_id, "product ID")

    existing = database.products.find_one({"_id": prod_oid, "org_id": org_oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    if payload.quantity is not None:
        new_qty = payload.quantity
    elif payload.delta is not None:
        new_qty = int(existing.get("quantity", 0)) + payload.delta
        if new_qty < 0:
            raise HTTPException(status_code=400, detail="Quantity cannot be negative")
    else:
        raise HTTPException(status_code=400, detail="Provide 'quantity' or 'delta'")

    updated = database.products.find_one_and_update(
        {"_id": prod_oid, "org_id": org_oid},
        {"$set": {"quantity": new_qty, "updated_at": datetime.now(timezone.utc).isoformat()}},
        return_document=ReturnDocument.AFTER,
    )
    return serialize_product(updated, current_user["low_stock_threshold"])


@app.delete("/api/products/{product_id}")
def delete_product(product_id: str, current_user: dict = Depends(get_current_user)):
    database = get_db()
    org_oid = parse_object_id(current_user["org_id"], "organization ID")
    prod_oid = parse_object_id(product_id, "product ID")

    result = database.products.delete_one({"_id": prod_oid, "org_id": org_oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"deleted": True, "id": product_id}


# --- Settings Routes ---

@app.get("/api/settings")
def get_settings(current_user: dict = Depends(get_current_user)):
    return {
        "org_id": current_user["org_id"],
        "org_name": current_user["org_name"],
        "low_stock_threshold": current_user["low_stock_threshold"],
    }


@app.put("/api/settings")
def update_settings(payload: SettingsUpdate, current_user: dict = Depends(get_current_user)):
    database = get_db()
    org_oid = parse_object_id(current_user["org_id"], "organization ID")

    updates = {"low_stock_threshold": payload.low_stock_threshold}
    if payload.org_name is not None:
        updates["name"] = payload.org_name.strip()

    updated_org = database.organizations.find_one_and_update(
        {"_id": org_oid},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    if not updated_org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "org_id": str(updated_org["_id"]),
        "org_name": updated_org["name"],
        "low_stock_threshold": int(updated_org.get("low_stock_threshold", DEFAULT_LOW_STOCK_THRESHOLD)),
    }


# --- Health & Built React Frontend Serving ---

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/api/health")
def api_health():
    return {"status": "ok", "service": "StockFlow MVP API", "database": "mongodb"}


@app.get("/", include_in_schema=False)
def serve_root():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"status": "ok", "service": "StockFlow MVP API", "database": "mongodb"})


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str):
    if full_path.startswith("api"):
        raise HTTPException(status_code=404, detail="Not found")
    candidate = FRONTEND_DIST / full_path
    if full_path and candidate.is_file():
        return FileResponse(candidate)
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Frontend build not found")
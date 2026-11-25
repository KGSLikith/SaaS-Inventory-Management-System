from typing import Optional
from pydantic import BaseModel, EmailStr, Field
class SignupRequest(BaseModel):
    organizationName: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=4)
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1)
    sku: str = Field(..., min_length=1)
    description: Optional[str] = ""
    quantity: int = Field(default=0, ge=0)
    cost_price: float = Field(default=0.0, ge=0)
    selling_price: float = Field(default=0.0, ge=0)
    low_stock_threshold: Optional[int | str] = None
class QuantityUpdate(BaseModel):
    quantity: int = Field(..., ge=0)
class SettingsUpdate(BaseModel):
    default_low_stock_threshold: int = Field(..., ge=0)
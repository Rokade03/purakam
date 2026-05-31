from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: str = Field(..., min_length=10, max_length=15)
    address: Optional[str] = None
    role: str = "customer"  # "customer" or "partner"
    
    # Partner specific fields if role == "partner"
    service_category: Optional[str] = None
    hourly_rate: Optional[float] = None
    bio: Optional[str] = None

class PartnerProfileUpdate(BaseModel):
    service_category: Optional[str] = None
    hourly_rate: Optional[float] = None
    availability_status: Optional[bool] = None
    bio: Optional[str] = None

class PartnerProfileResponse(BaseModel):
    id: int
    user_id: int
    service_category: str
    hourly_rate: float
    rating: float
    availability_status: bool
    bio: Optional[str] = None
    completed_jobs: int

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str
    address: Optional[str] = None
    role: str
    created_at: datetime
    partner_profile: Optional[PartnerProfileResponse] = None
    access_token: Optional[str] = None

    class Config:
        from_attributes = True

class ServiceCategoryResponse(BaseModel):
    id: int
    name: str
    icon_key: str
    description: str
    base_price: float

    class Config:
        from_attributes = True

class BookingCreate(BaseModel):
    service_category: str
    booking_date: str  # YYYY-MM-DD
    time_slot: str
    details: Optional[str] = None
    price: float
    address: str
    payment_method: str = "UPI"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    partner_id: Optional[int] = None

class ReviewCreate(BaseModel):
    booking_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    booking_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class BookingResponse(BaseModel):
    id: int
    customer_id: int
    partner_id: Optional[int] = None
    service_category: str
    booking_date: str
    time_slot: str
    details: Optional[str] = None
    price: float
    status: str
    address: str
    payment_method: str
    payment_status: str
    attachment_path: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    
    # Optionally embed customer and partner user details
    customer: Optional[UserResponse] = None
    partner: Optional[UserResponse] = None
    review: Optional[ReviewResponse] = None

    class Config:
        from_attributes = True

class ChatMessageCreate(BaseModel):
    message_text: str = Field(..., min_length=1, max_length=1000)

class ChatMessageResponse(BaseModel):
    id: int
    booking_id: int
    sender_id: int
    message_text: str
    timestamp: datetime
    sender_name: Optional[str] = None

    class Config:
        from_attributes = True

class CategoryCount(BaseModel):
    name: str
    count: int

class AdminStatsResponse(BaseModel):
    total_bookings: int
    total_customers: int
    total_partners_online: int
    total_partners_offline: int
    total_revenue: float
    category_breakdown: List[CategoryCount]

class ServiceCategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    icon_key: str = Field(..., min_length=1)
    description: str = Field(..., min_length=5)
    base_price: float = Field(..., ge=0.0)

class ServiceCategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon_key: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[float] = None

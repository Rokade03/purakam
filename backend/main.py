import os
from fastapi import FastAPI, Depends, HTTPException, status, Header, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from . import database, schemas
from .database import get_db, User, PartnerProfile, ServiceCategory, Booking, Review, ChatMessage, hash_password

import math
from jose import jwt, JWTError

# JWT Configuration
SECRET_KEY = "purakam_super_secret_jwt_signing_key_for_india_market"
ALGORITHM = "HS256"

def create_access_token(user_id: int, role: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow().timestamp() + 86400  # Token expires in 24 hours
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# Haversine distance calculator
def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Earth radius in kilometers
    R = 6371.0
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

app = FastAPI(title="Purakam API Backend", version="1.0.0")

# Setup upload directory
UPLOAD_DIR = "backend/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Helper to verify auth tokens (simplifies security for local demo)
def get_current_user_id(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token"
        )
    try:
        token = authorization.split(" ")[1]
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token"
            )
        user_id = payload.get("user_id")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        return user_id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token"
        )

def get_current_admin_id(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token"
        )
    try:
        token = authorization.split(" ")[1]
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token"
            )
        user_id = payload.get("user_id")
        role = payload.get("role")
        if role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators are authorized to access this resource"
            )
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators are authorized to access this resource"
            )
        return user_id
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token"
        )

# === Auth Routes ===

@app.post("/api/auth/register", response_model=schemas.UserResponse)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new User
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        phone=user_data.phone,
        address=user_data.address,
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # If role is partner, create the PartnerProfile
    if user_data.role == "partner":
        if not user_data.service_category or user_data.hourly_rate is None:
            # Delete user to rollback manually
            db.delete(new_user)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Service category and hourly rate required for partner role"
            )
        
        new_partner = PartnerProfile(
            user_id=new_user.id,
            service_category=user_data.service_category,
            hourly_rate=user_data.hourly_rate,
            bio=user_data.bio or f"Professional {user_data.service_category} in the local area.",
            availability_status=False  # Starts offline
        )
        db.add(new_partner)
        db.commit()
        db.refresh(new_user)

    token = create_access_token(new_user.id, new_user.role)
    new_user.access_token = token
    return new_user

@app.post("/api/auth/login", response_model=schemas.UserResponse)
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or user.password_hash != hash_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    token = create_access_token(user.id, user.role)
    user.access_token = token
    return user

@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_me(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    token = create_access_token(user.id, user.role)
    user.access_token = token
    return user

# === Service Category Routes ===

@app.get("/api/services", response_model=List[schemas.ServiceCategoryResponse])
def get_service_categories(db: Session = Depends(get_db)):
    return db.query(ServiceCategory).all()

# === Partner Profile Routes ===

@app.get("/api/partners", response_model=List[schemas.UserResponse])
def get_partners(category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == "partner")
    if category:
        query = query.join(PartnerProfile).filter(PartnerProfile.service_category == category)
    return query.all()

@app.put("/api/partner/profile", response_model=schemas.PartnerProfileResponse)
def update_partner_profile(
    profile_data: schemas.PartnerProfileUpdate, 
    user_id: int = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner profile not found"
        )
    
    if profile_data.service_category is not None:
        profile.service_category = profile_data.service_category
    if profile_data.hourly_rate is not None:
        profile.hourly_rate = profile_data.hourly_rate
    if profile_data.availability_status is not None:
        profile.availability_status = profile_data.availability_status
    if profile_data.bio is not None:
        profile.bio = profile_data.bio
        
    db.commit()
    db.refresh(profile)
    return profile

# === Booking Routes ===

@app.post("/api/bookings", response_model=schemas.BookingResponse)
def create_booking(
    booking_data: schemas.BookingCreate, 
    customer_id: int = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    # Find active/online partners in this service category
    online_partners = db.query(PartnerProfile).filter(
        PartnerProfile.service_category == booking_data.service_category,
        PartnerProfile.availability_status == True
    ).all()
    
    assigned_partner_id = None
    booking_status = "pending"
    
    # Check if a specific partner is requested directly
    if booking_data.partner_id is not None:
        partner_profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == booking_data.partner_id).first()
        if not partner_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid service partner ID requested."
            )
        assigned_partner_id = booking_data.partner_id
        # Directly accept if partner is online/available, else leave pending
        booking_status = "accepted" if partner_profile.availability_status else "pending"
        
    # Auto-assign based on Proximity Haversine distance
    elif online_partners and booking_data.latitude is not None and booking_data.longitude is not None:
        partner_distances = []
        for partner_profile in online_partners:
            partner_user = db.query(User).filter(User.id == partner_profile.user_id).first()
            if partner_user and partner_user.latitude is not None and partner_user.longitude is not None:
                dist = calculate_haversine_distance(
                    booking_data.latitude, booking_data.longitude,
                    partner_user.latitude, partner_user.longitude
                )
                partner_distances.append((partner_profile, dist))
        
        if partner_distances:
            partner_distances.sort(key=lambda x: x[1])  # Sort closest distance first
            closest_partner = partner_distances[0][0]
            assigned_partner_id = closest_partner.user_id
            booking_status = "accepted"
            
    # Fallback: Auto-assign highest rated online partner if coordinates are missing
    elif online_partners:
        best_partner = max(online_partners, key=lambda p: p.rating)
        assigned_partner_id = best_partner.user_id
        booking_status = "accepted"

    new_booking = Booking(
        customer_id=customer_id,
        partner_id=assigned_partner_id,
        service_category=booking_data.service_category,
        booking_date=booking_data.booking_date,
        time_slot=booking_data.time_slot,
        details=booking_data.details,
        price=booking_data.price,
        status=booking_status,
        address=booking_data.address,
        payment_method=booking_data.payment_method,
        payment_status="completed" if booking_data.payment_method == "UPI" else "pending",
        latitude=booking_data.latitude,
        longitude=booking_data.longitude
    )
    
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking

@app.get("/api/bookings", response_model=List[schemas.BookingResponse])
def get_bookings(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user.role == "partner":
        return db.query(Booking).filter(Booking.partner_id == user_id).order_by(Booking.id.desc()).all()
    else:
        return db.query(Booking).filter(Booking.customer_id == user_id).order_by(Booking.id.desc()).all()

@app.get("/api/partner/incoming-bookings", response_model=List[schemas.BookingResponse])
def get_incoming_bookings_for_partner(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    partner_profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == user_id).first()
    if not partner_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only service partners can view incoming jobs"
        )
    # Return all pending bookings matching partner's service category
    return db.query(Booking).filter(
        Booking.service_category == partner_profile.service_category,
        Booking.status == "pending"
    ).order_by(Booking.id.desc()).all()

@app.put("/api/bookings/{booking_id}/status", response_model=schemas.BookingResponse)
def update_booking_status(
    booking_id: int, 
    new_status: str, 
    user_id: int = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    user = db.query(User).filter(User.id == user_id).first()
    
    # Partner Accepting a pending booking
    if new_status == "accepted" and booking.status == "pending" and user.role == "partner":
        booking.partner_id = user_id
        booking.status = "accepted"
    # General status progressions by assigned partner
    elif user.role == "partner" and booking.partner_id == user_id:
        if new_status in ["on_the_way", "in_progress"]:
            booking.status = new_status
        elif new_status == "completed":
            booking.status = "completed"
            booking.payment_status = "completed"  # Cash collections or UPI matches complete
            # Increment partner's completed jobs
            partner_profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == user_id).first()
            if partner_profile:
                partner_profile.completed_jobs += 1
    # Customer cancels
    elif user.role == "customer" and booking.customer_id == user_id:
        if new_status == "cancelled" and booking.status in ["pending", "accepted"]:
            booking.status = "cancelled"
        else:
            raise HTTPException(status_code=400, detail="Cannot cancel booking in current state")
    else:
        raise HTTPException(status_code=403, detail="Unauthorized state change request")

    db.commit()
    db.refresh(booking)
    return booking

# === Review Routes ===

@app.post("/api/reviews", response_model=schemas.ReviewResponse)
def submit_review(
    review_data: schemas.ReviewCreate, 
    customer_id: int = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(
        Booking.id == review_data.booking_id,
        Booking.customer_id == customer_id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found or not owned by customer")
    if booking.status != "completed":
        raise HTTPException(status_code=400, detail="Can only review completed bookings")
    
    # Check if review already exists
    existing_review = db.query(Review).filter(Review.booking_id == review_data.booking_id).first()
    if existing_review:
        raise HTTPException(status_code=400, detail="Review already submitted for this booking")

    new_review = Review(
        booking_id=review_data.booking_id,
        rating=review_data.rating,
        comment=review_data.comment
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    # Re-calculate partner's average rating
    if booking.partner_id:
        partner_id = booking.partner_id
        all_partner_bookings = db.query(Booking).filter(
            Booking.partner_id == partner_id,
            Booking.status == "completed"
        ).all()
        
        booking_ids = [b.id for b in all_partner_bookings]
        all_reviews = db.query(Review).filter(Review.booking_id.in_(booking_ids)).all()
        
        if all_reviews:
            avg_rating = sum(r.rating for r in all_reviews) / len(all_reviews)
            partner_profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == partner_id).first()
            if partner_profile:
                partner_profile.rating = round(avg_rating, 2)
                db.commit()

    return new_review

# === File Upload Attachment Routes ===

@app.post("/api/bookings/{booking_id}/upload")
async def upload_booking_attachment(
    booking_id: int,
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.customer_id == user_id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found or unauthorized")
        
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov", ".avi", ".mkv", ".webm"]:
        raise HTTPException(status_code=400, detail="Only standard images and videos are supported")
        
    filename = f"booking_{booking_id}_{int(datetime.utcnow().timestamp())}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    booking.attachment_path = filename
    db.commit()
    db.refresh(booking)
    return {"filename": filename, "status": "success"}

# === Chat Messaging Routes ===

@app.get("/api/bookings/{booking_id}/messages", response_model=List[schemas.ChatMessageResponse])
def get_booking_messages(
    booking_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    if booking.customer_id != user_id and booking.partner_id != user_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized access to chat")
        
    messages = db.query(ChatMessage).filter(ChatMessage.booking_id == booking_id).order_by(ChatMessage.timestamp.asc()).all()
    
    # Populate sender names dynamically for client view
    response_list = []
    for m in messages:
        sender = db.query(User).filter(User.id == m.sender_id).first()
        response_list.append(schemas.ChatMessageResponse(
            id=m.id,
            booking_id=m.booking_id,
            sender_id=m.sender_id,
            message_text=m.message_text,
            timestamp=m.timestamp,
            sender_name=sender.name if sender else "Unknown"
        ))
    return response_list

@app.post("/api/bookings/{booking_id}/messages", response_model=schemas.ChatMessageResponse)
def send_booking_message(
    booking_id: int,
    msg_data: schemas.ChatMessageCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    if booking.customer_id != user_id and booking.partner_id != user_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized access to chat")
        
    new_msg = ChatMessage(
        booking_id=booking_id,
        sender_id=user_id,
        message_text=msg_data.message_text
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    
    sender = db.query(User).filter(User.id == user_id).first()
    return schemas.ChatMessageResponse(
        id=new_msg.id,
        booking_id=new_msg.booking_id,
        sender_id=new_msg.sender_id,
        message_text=new_msg.message_text,
        timestamp=new_msg.timestamp,
        sender_name=sender.name if sender else "Unknown"
    )

# === Admin Console Routes ===

@app.get("/api/admin/stats", response_model=schemas.AdminStatsResponse)
def get_admin_stats(admin_id: int = Depends(get_current_admin_id), db: Session = Depends(get_db)):
    total_bookings = db.query(Booking).count()
    total_customers = db.query(User).filter(User.role == "customer").count()
    total_partners_online = db.query(PartnerProfile).filter(PartnerProfile.availability_status == True).count()
    total_partners_offline = db.query(PartnerProfile).filter(PartnerProfile.availability_status == False).count()
    
    # Calculate revenue
    completed_bookings = db.query(Booking).filter(Booking.status == "completed").all()
    total_revenue = sum(b.price for b in completed_bookings)
    
    # Category breakdowns
    categories = db.query(ServiceCategory).all()
    category_breakdown = []
    for cat in categories:
        count = db.query(Booking).filter(Booking.service_category == cat.name).count()
        category_breakdown.append(schemas.CategoryCount(name=cat.name, count=count))
        
    return schemas.AdminStatsResponse(
        total_bookings=total_bookings,
        total_customers=total_customers,
        total_partners_online=total_partners_online,
        total_partners_offline=total_partners_offline,
        total_revenue=total_revenue,
        category_breakdown=category_breakdown
    )

@app.get("/api/admin/users", response_model=List[schemas.UserResponse])
def get_admin_users(admin_id: int = Depends(get_current_admin_id), db: Session = Depends(get_db)):
    return db.query(User).all()

@app.get("/api/admin/bookings", response_model=List[schemas.BookingResponse])
def get_admin_bookings(admin_id: int = Depends(get_current_admin_id), db: Session = Depends(get_db)):
    return db.query(Booking).order_by(Booking.id.desc()).all()

@app.post("/api/admin/services", response_model=schemas.ServiceCategoryResponse)
def create_service_category(
    cat_data: schemas.ServiceCategoryCreate,
    admin_id: int = Depends(get_current_admin_id),
    db: Session = Depends(get_db)
):
    # Check if category name already exists
    existing = db.query(ServiceCategory).filter(ServiceCategory.name == cat_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Service category already exists")
        
    new_cat = ServiceCategory(
        name=cat_data.name,
        icon_key=cat_data.icon_key,
        description=cat_data.description,
        base_price=cat_data.base_price
    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat

@app.put("/api/admin/services/{service_id}", response_model=schemas.ServiceCategoryResponse)
def update_service_category(
    service_id: int,
    cat_data: schemas.ServiceCategoryUpdate,
    admin_id: int = Depends(get_current_admin_id),
    db: Session = Depends(get_db)
):
    cat = db.query(ServiceCategory).filter(ServiceCategory.id == service_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Service category not found")
        
    if cat_data.name is not None:
        cat.name = cat_data.name
    if cat_data.icon_key is not None:
        cat.icon_key = cat_data.icon_key
    if cat_data.description is not None:
        cat.description = cat_data.description
    if cat_data.base_price is not None:
        cat.base_price = cat_data.base_price
        
    db.commit()
    db.refresh(cat)
    return cat

@app.delete("/api/admin/services/{service_id}")
def delete_service_category(
    service_id: int,
    admin_id: int = Depends(get_current_admin_id),
    db: Session = Depends(get_db)
):
    cat = db.query(ServiceCategory).filter(ServiceCategory.id == service_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Service category not found")
        
    db.delete(cat)
    db.commit()
    return {"message": "Service category deleted successfully"}


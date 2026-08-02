import os
import random
import razorpay
from fastapi import FastAPI, Depends, HTTPException, status, Header, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_dummy_key_id")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "dummy_secret")

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from . import database, schemas
from .database import get_db, User, PartnerProfile, ServiceCategory, Booking, Review, ChatMessage, PartnerDeclinedBooking, hash_password

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
    
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_otp(to_email: str, otp_code: str):
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    
    if not smtp_user or not smtp_password:
        print(f"📧 [DEV SANDBOX MODE] No SMTP credentials configured. OTP Code for {to_email} is {otp_code}")
        return False
        
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your Purakam Verification Code: {otp_code}"
        msg["From"] = f"Purakam Services <{smtp_user}>"
        msg["To"] = to_email
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 16px; background-color: #ffffff;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #111827; margin: 0; font-size: 24px;">Purakam</h1>
                <p style="color: #6b7280; font-size: 14px; margin-top: 4px;">Household Services Platform</p>
            </div>
            <h2 style="color: #111827; font-size: 18px;">Verify Your Email Address</h2>
            <p style="color: #4b5563; line-height: 1.5;">Thank you for registering with Purakam! Please enter the 6-digit OTP verification code below to complete your registration:</p>
            <div style="font-size: 32px; font-weight: bold; color: #22c55e; letter-spacing: 6px; padding: 16px; background: #f3f4f6; border-radius: 12px; text-align: center; margin: 24px 0;">
                {otp_code}
            </div>
            <p style="color: #6b7280; font-size: 13px; line-height: 1.4;">This code will expire in 15 minutes. If you did not register for Purakam, please ignore this email.</p>
        </div>
        """
        msg.attach(MIMEText(html_content, "html"))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, msg.as_string())
        print(f"✅ Real email successfully sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send real email to {to_email}: {e}")
        return False

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

    # Validate address presence
    if not user_data.address or not user_data.address.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Address is required"
        )


    # Generate 6-digit OTP verification code
    import random
    from datetime import datetime, timedelta
    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    # Create new User (is_verified = False for new registrations)
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        phone=user_data.phone,
        address=user_data.address,
        role=user_data.role,
        is_verified=False,
        verification_code=otp_code,
        verification_code_expires_at=expires_at
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
            
        if not user_data.aadhar_card or not user_data.pan_card:
            db.delete(new_user)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aadhar card number and PAN card number are required for service partners"
            )
            
        aadhar_stripped = user_data.aadhar_card.replace(" ", "").replace("-", "")
        if len(aadhar_stripped) != 12 or not aadhar_stripped.isdigit():
            db.delete(new_user)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aadhar card must be a 12-digit numeric code"
            )
            
        pan_upper = user_data.pan_card.upper().strip()
        if len(pan_upper) != 10 or not pan_upper.isalnum():
            db.delete(new_user)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PAN card must be a 10-character alphanumeric code"
            )
        
        new_partner = PartnerProfile(
            user_id=new_user.id,
            service_category=user_data.service_category,
            hourly_rate=user_data.hourly_rate,
            bio=user_data.bio or f"Professional {user_data.service_category} in the local area.",
            availability_status=False,  # Starts offline
            aadhar_card=aadhar_stripped,
            pan_card=pan_upper
        )
        db.add(new_partner)
        db.refresh(new_user)

    sent = send_email_otp(new_user.email, otp_code)
    token = create_access_token(new_user.id, new_user.role)

    new_user.access_token = token
    if sent:
        new_user.verification_code = None
    return new_user

@app.post("/api/auth/verify-email", response_model=schemas.UserResponse)
def verify_email(req: schemas.VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found with this email"
        )
    
    if user.is_verified:
        token = create_access_token(user.id, user.role)
        user.access_token = token
        return user

    if not user.verification_code or user.verification_code != req.code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 6-digit verification code"
        )
    
    from datetime import datetime
    if user.verification_code_expires_at and datetime.utcnow() > user.verification_code_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new code."
        )

    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires_at = None
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.role)
    user.access_token = token
    return user

@app.post("/api/auth/resend-verification")
def resend_verification(req: schemas.ResendVerificationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found with this email"
        )
    
    if user.is_verified:
        return {"message": "Email is already verified"}

    import random
    from datetime import datetime, timedelta
    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    user.verification_code = otp_code
    user.verification_code_expires_at = expires_at
    db.commit()

    sent = send_email_otp(user.email, otp_code)
    res = {"message": "New verification code sent to your email"}
    if not sent:
        res["verification_code"] = otp_code
    return res


@app.post("/api/auth/login", response_model=schemas.UserResponse)
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or user.password_hash != hash_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="EMAIL_NOT_VERIFIED"
        )

    token = create_access_token(user.id, user.role)
    user.access_token = token
    return user


@app.post("/api/auth/google", response_model=schemas.UserResponse)
def login_with_google(google_data: schemas.GoogleUserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == google_data.email).first()
    if not user:
        # Create a new user with placeholder details
        import secrets
        random_password = secrets.token_hex(16)
        user = User(
            name=google_data.name,
            email=google_data.email,
            password_hash=hash_password(random_password),
            phone="0000000000",
            role="customer",
            is_verified=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)
    
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

@app.put("/api/partner/location")
def update_partner_location(
    loc_data: schemas.PartnerLocationUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != "partner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only service partners can update location"
        )
    user.latitude = loc_data.latitude
    user.longitude = loc_data.longitude
    db.commit()
    return {"message": "Location updated successfully"}

DISPATCH_TIMEOUT_SECONDS = int(os.environ.get("DISPATCH_TIMEOUT_SECONDS", "600"))

def check_and_expire_bookings(db: Session):
    now = datetime.utcnow()
    requested_bookings = db.query(Booking).filter(Booking.status == "requested").all()
    expired_count = 0
    for booking in requested_bookings:
        elapsed = (now - booking.created_at).total_seconds()
        if elapsed > DISPATCH_TIMEOUT_SECONDS:
            booking.status = "cancelled"
            expired_count += 1
    if expired_count > 0:
        db.commit()

# === Booking Routes ===

@app.post("/api/bookings", response_model=schemas.BookingResponse)
def create_booking(
    booking_data: schemas.BookingCreate, 
    customer_id: int = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    ALLOWED_MUMBAI_AREAS = {
        "Colaba & South Mumbai",
        "Dadar & Central Mumbai",
        "Bandra & Western Suburbs",
        "Andheri & Western Suburbs",
        "Borivali & Northern Suburbs",
        "Ghatkopar & Eastern Suburbs",
        "Powai & East Mumbai",
        "Thane",
        "Navi Mumbai"
    }
    
    if not booking_data.area_name or booking_data.area_name not in ALLOWED_MUMBAI_AREAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Service area must be a valid region in Mumbai, Thane, or Navi Mumbai"
        )
        
    address_lower = (booking_data.address or "").lower()
    if not any(city in address_lower for city in ["mumbai", "thane", "navi mumbai"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doorstep address must be located in Mumbai, Thane, or Navi Mumbai"
        )

    # Validate pincode format and region
    pincode = booking_data.pincode
    if not pincode or len(pincode) != 6 or not pincode.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pincode must be exactly 6 digits"
        )
        
    if not (pincode.startswith("400") or pincode.startswith("401") or pincode.startswith("421")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Service is only available in Mumbai, Thane, or Navi Mumbai regions matching valid local pincodes"
        )

    otp_code = str(random.randint(100000, 999999))
    new_booking = Booking(
        customer_id=customer_id,
        partner_id=None,
        service_category=booking_data.service_category,
        booking_date=booking_data.booking_date,
        time_slot=booking_data.time_slot,
        details=booking_data.details,
        price=booking_data.price,
        status="requested",
        address=booking_data.address,
        payment_method=booking_data.payment_method,
        payment_status="pending",
        otp=otp_code,
        latitude=booking_data.latitude,
        longitude=booking_data.longitude,
        area_name=booking_data.area_name,
        pincode=booking_data.pincode
    )
    
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking

@app.post("/api/bookings/{booking_id}/order")
def create_razorpay_order(
    booking_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.customer_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this booking")
        
    amount_paise = int(booking.price * 100)
    
    if RAZORPAY_KEY_ID == "rzp_test_dummy_key_id":
        mock_order_id = f"order_mock_{booking_id}_{random.randint(1000, 9999)}"
        booking.razorpay_order_id = mock_order_id
        db.commit()
        return {
            "order_id": mock_order_id,
            "amount": amount_paise,
            "key_id": RAZORPAY_KEY_ID
        }
        
    try:
        order_data = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"receipt_booking_{booking_id}",
            "payment_capture": 1
        }
        order = razorpay_client.order.create(data=order_data)
        booking.razorpay_order_id = order["id"]
        db.commit()
        return {
            "order_id": order["id"],
            "amount": amount_paise,
            "key_id": RAZORPAY_KEY_ID
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Razorpay order creation failed: {str(e)}")

@app.post("/api/bookings/{booking_id}/verify-payment")
def verify_razorpay_payment(
    booking_id: int,
    verification: schemas.RazorpayVerification,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.customer_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this booking")
        
    if RAZORPAY_KEY_ID == "rzp_test_dummy_key_id":
        if verification.razorpay_order_id != booking.razorpay_order_id:
            raise HTTPException(status_code=400, detail="Invalid order ID signature")
        booking.payment_status = "completed"
        booking.razorpay_payment_id = verification.razorpay_payment_id
        booking.razorpay_signature = verification.razorpay_signature
        db.commit()
        return {"status": "success", "message": "Payment verified (mocked)"}
        
    try:
        param_dict = {
            'razorpay_order_id': verification.razorpay_order_id,
            'razorpay_payment_id': verification.razorpay_payment_id,
            'razorpay_signature': verification.razorpay_signature
        }
        razorpay_client.utility.verify_payment_signature(param_dict)
        
        booking.payment_status = "completed"
        booking.razorpay_payment_id = verification.razorpay_payment_id
        booking.razorpay_signature = verification.razorpay_signature
        db.commit()
        return {"status": "success", "message": "Payment verified successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payment signature verification failed: {str(e)}")

@app.get("/api/bookings", response_model=List[schemas.BookingResponse])
def get_bookings(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    check_and_expire_bookings(db)
    user = db.query(User).filter(User.id == user_id).first()
    if user.role == "partner":
        bookings = db.query(Booking).filter(Booking.partner_id == user_id).order_by(Booking.id.desc()).all()
        result = []
        for b in bookings:
            pydantic_b = schemas.BookingResponse.model_validate(b)
            pydantic_b.otp = None
            result.append(pydantic_b)
        return result
    else:
        return db.query(Booking).filter(Booking.customer_id == user_id).order_by(Booking.id.desc()).all()

@app.get("/api/partner/incoming-bookings", response_model=List[schemas.BookingResponse])
def get_incoming_bookings_for_partner(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    check_and_expire_bookings(db)
    partner_profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == user_id).first()
    if not partner_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only service partners can view incoming jobs"
        )
    
    # Check provider availability (online/offline)
    if not partner_profile.availability_status:
        return []
        
    partner_user = db.query(User).filter(User.id == user_id).first()
    
    # Get declined booking IDs
    declined_ids = [d.booking_id for d in db.query(PartnerDeclinedBooking).filter(PartnerDeclinedBooking.partner_id == user_id).all()]
    
    # Return all requested bookings matching partner's service category (category-wide broadcasting)
    bookings = db.query(Booking).filter(
        Booking.service_category == partner_profile.service_category,
        Booking.status == "requested"
    ).order_by(Booking.id.desc()).all()
    
    result = []
    for b in bookings:
        if b.id in declined_ids:
            continue
        
        pydantic_b = schemas.BookingResponse.model_validate(b)
        pydantic_b.otp = None
        result.append(pydantic_b)
            
    return result

@app.post("/api/bookings/{booking_id}/decline")
def decline_booking(booking_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    partner_profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == user_id).first()
    if not partner_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only service partners can decline bookings"
        )
    
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if booking.status != "requested":
        raise HTTPException(status_code=400, detail="Can only decline active requested bookings")
        
    # Add to declined table if not already declined
    existing = db.query(PartnerDeclinedBooking).filter(
        PartnerDeclinedBooking.partner_id == user_id,
        PartnerDeclinedBooking.booking_id == booking_id
    ).first()
    
    if not existing:
        declined_record = PartnerDeclinedBooking(partner_id=user_id, booking_id=booking_id)
        db.add(declined_record)
        db.commit()
        
    return {"detail": "Booking request declined successfully"}

@app.put("/api/bookings/{booking_id}/status", response_model=schemas.BookingResponse)
def update_booking_status(
    booking_id: int, 
    new_status: str, 
    otp: Optional[str] = None,
    user_id: int = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    user = db.query(User).filter(User.id == user_id).first()
    
    # Partner Accepting a requested booking
    if new_status == "accepted" and user.role == "partner":
        if booking.status == "accepted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This booking request has already been accepted by another service provider."
            )
        elif booking.status != "requested":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This booking request is no longer available."
            )
        booking.partner_id = user_id
        booking.status = "accepted"
        booking.accepted_at = datetime.utcnow()
    # General status progressions by assigned partner
    elif user.role == "partner" and booking.partner_id == user_id:
        if new_status == "on_the_way":
            booking.status = new_status
        elif new_status == "in_progress":
            if not otp:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification OTP is required to start work."
                )
            if booking.otp and otp != booking.otp:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid verification OTP. Please ask the customer for the correct OTP."
                )
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
        if new_status == "cancelled" and booking.status in ["requested", "accepted"]:
            booking.status = "cancelled"
        else:
            raise HTTPException(status_code=400, detail="Cannot cancel booking in current state")
    else:
        raise HTTPException(status_code=403, detail="Unauthorized state change request")

    db.commit()
    db.refresh(booking)
    
    pydantic_booking = schemas.BookingResponse.model_validate(booking)
    if user.role == "partner":
        pydantic_booking.otp = None
    return pydantic_booking

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
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.customer_id == user_id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found or unauthorized")
        
    all_files = []
    if file:
        all_files.append(file)
    if files:
        all_files.extend(files)
        
    if not all_files:
        raise HTTPException(status_code=400, detail="No files uploaded")
        
    saved_filenames = []
    for f in all_files:
        file_ext = os.path.splitext(f.filename)[1].lower()
        if file_ext not in [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {f.filename}")
            
        filename = f"booking_{booking_id}_{int(datetime.utcnow().timestamp())}_{random.randint(1000, 9999)}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        try:
            with open(file_path, "wb") as buffer:
                content = await f.read()
                buffer.write(content)
            saved_filenames.append(filename)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
            
    if saved_filenames:
        if booking.attachment_path:
            booking.attachment_path = f"{booking.attachment_path},{','.join(saved_filenames)}"
        else:
            booking.attachment_path = ",".join(saved_filenames)
        db.commit()
        db.refresh(booking)
        
    return {
        "filename": saved_filenames[0] if saved_filenames else None,
        "filenames": saved_filenames,
        "status": "success"
    }

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
        
    # Dispatch system specific metrics
    total_requested = db.query(Booking).filter(Booking.status == "requested").count()
    total_assigned = db.query(Booking).filter(Booking.status.in_(["accepted", "on_the_way", "in_progress", "completed"])).count()
    total_cancelled = db.query(Booking).filter(Booking.status == "cancelled").count()
    
    # Calculate average assignment time
    assigned_bookings = db.query(Booking).filter(
        Booking.accepted_at.isnot(None),
        Booking.created_at.isnot(None)
    ).all()
    
    if assigned_bookings:
        total_time = sum((b.accepted_at - b.created_at).total_seconds() for b in assigned_bookings)
        avg_assignment_time = total_time / len(assigned_bookings)
    else:
        avg_assignment_time = 0.0
        
    return schemas.AdminStatsResponse(
        total_bookings=total_bookings,
        total_customers=total_customers,
        total_partners_online=total_partners_online,
        total_partners_offline=total_partners_offline,
        total_revenue=total_revenue,
        category_breakdown=category_breakdown,
        total_requested_bookings=total_requested,
        total_assigned_bookings=total_assigned,
        total_cancelled_bookings=total_cancelled,
        average_assignment_time_seconds=avg_assignment_time
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


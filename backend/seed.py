from sqlalchemy import inspect, text
from backend.database import engine, Base, SessionLocal, User, PartnerProfile, ServiceCategory, hash_password

def seed_db():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Run automatic schema migration to ensure 'otp', 'area_name', and 'accepted_at' columns exist
    inspector = inspect(engine)
    if inspector.has_table('bookings'):
        columns = [col['name'] for col in inspector.get_columns('bookings')]
        if 'otp' not in columns:
            print("Migration: Adding missing 'otp' column to bookings table...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN otp VARCHAR(255);"))
            print("Migration: 'otp' column added successfully.")
        if 'area_name' not in columns:
            print("Migration: Adding missing 'area_name' column to bookings table...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN area_name VARCHAR(255);"))
            print("Migration: 'area_name' column added successfully.")
        if 'accepted_at' not in columns:
            print("Migration: Adding missing 'accepted_at' column to bookings table...")
            db_type = "TIMESTAMP" if engine.dialect.name == "postgresql" else "DATETIME"
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE bookings ADD COLUMN accepted_at {db_type};"))
            print("Migration: 'accepted_at' column added successfully.")
        if 'pincode' not in columns:
            print("Migration: Adding missing 'pincode' column to bookings table...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN pincode VARCHAR(6);"))
            print("Migration: 'pincode' column added successfully.")
        if 'razorpay_order_id' not in columns:
            print("Migration: Adding missing 'razorpay_order_id' column to bookings table...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN razorpay_order_id VARCHAR(255);"))
            print("Migration: 'razorpay_order_id' column added successfully.")
        if 'razorpay_payment_id' not in columns:
            print("Migration: Adding missing 'razorpay_payment_id' column to bookings table...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN razorpay_payment_id VARCHAR(255);"))
            print("Migration: 'razorpay_payment_id' column added successfully.")
        if 'razorpay_signature' not in columns:
            print("Migration: Adding missing 'razorpay_signature' column to bookings table...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN razorpay_signature VARCHAR(255);"))
            print("Migration: 'razorpay_signature' column added successfully.")

    if inspector.has_table('partner_profiles'):
        columns = [col['name'] for col in inspector.get_columns('partner_profiles')]
        if 'aadhar_card' not in columns:
            print("Migration: Adding missing 'aadhar_card' column to partner_profiles table...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE partner_profiles ADD COLUMN aadhar_card VARCHAR(255);"))
            print("Migration: 'aadhar_card' column added successfully.")
        if 'pan_card' not in columns:
            print("Migration: Adding missing 'pan_card' column to partner_profiles table...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE partner_profiles ADD COLUMN pan_card VARCHAR(255);"))
            print("Migration: 'pan_card' column added successfully.")
    
    db = SessionLocal()
    try:
        # 1. Seed Service Categories
        categories = [
            {
                "name": "Electrician",
                "icon_key": "zap",
                "description": "General electrical work, fan installations, light fittings, and residential wiring.",
                "base_price": 199.0
            },
            {
                "name": "Switchboard & Wiring",
                "icon_key": "plug",
                "description": "Switchboard repairs, socket replacement, short circuit fixes, and circuit breakers.",
                "base_price": 249.0
            },
            {
                "name": "AC & Appliance Repair",
                "icon_key": "wind",
                "description": "AC servicing, refrigerator geyser faults, washing machine electrical diagnostics.",
                "base_price": 399.0
            },
            {
                "name": "Inverter & Battery",
                "icon_key": "activity",
                "description": "Home inverter setups, backup battery diagnostics, connection fixes, and testing.",
                "base_price": 499.0
            },
            {
                "name": "Geyser & Water Heater",
                "icon_key": "droplet",
                "description": "Geyser element replacement, thermostat repairs, electrical leakage checks, and geyser setup.",
                "base_price": 299.0
            }
        ]
        
        print("Seeding service categories...")
        for cat_data in categories:
            existing = db.query(ServiceCategory).filter(ServiceCategory.name == cat_data["name"]).first()
            if not existing:
                cat = ServiceCategory(**cat_data)
                db.add(cat)
        db.commit()

        # 2. Seed Mock Customers
        customers = [
            {
                "name": "Aayush Rokade",
                "email": "customer@purakam.in",
                "password_hash": hash_password("customer123"),
                "phone": "+919876543210",
                "address": "402, Sea Breeze Apts, Bandra West, Mumbai, Maharashtra - 400050",
                "latitude": 19.0600,
                "longitude": 72.8258,
                "role": "customer"
            },
            {
                "name": "Purakam Admin",
                "email": "admin@purakam.in",
                "password_hash": hash_password("admin123"),
                "phone": "+919999000099",
                "address": "Purakam HQ, Bandra, Mumbai, MH - 400050",
                "latitude": 19.0600,
                "longitude": 72.8258,
                "role": "admin"
            }
        ]
        print("Seeding mock customers...")
        for cust_data in customers:
            existing = db.query(User).filter(User.email == cust_data["email"]).first()
            if not existing:
                cust = User(**cust_data)
                db.add(cust)
        db.commit()

        # 3. Seed Mock Service Partners
        partners = [
            {
                "name": "Rajesh Kumar",
                "email": "rajesh@purakam.in",
                "password_hash": hash_password("partner123"),
                "phone": "+919999888877",
                "address": "Sector 15, Vashi, Navi Mumbai, MH - 400703",
                "latitude": None,
                "longitude": None,
                "role": "partner",
                "profile": {
                    "service_category": "Electrician",
                    "hourly_rate": 250.0,
                    "rating": 4.8,
                    "availability_status": True,  # Online
                    "bio": "Certified electrician with 8+ years experience. Navi Mumbai based.",
                    "completed_jobs": 154,
                    "aadhar_card": "111122223333",
                    "pan_card": "ABCDE1234F"
                }
            },
            {
                "name": "Vijay Shinde",
                "email": "vijay@purakam.in",
                "password_hash": hash_password("partner123"),
                "phone": "+919999222233",
                "address": "Andheri West, Mumbai, MH - 400053",
                "latitude": 19.1197,
                "longitude": 72.8468,
                "role": "partner",
                "profile": {
                    "service_category": "Electrician",
                    "hourly_rate": 280.0,
                    "rating": 4.5,
                    "availability_status": True,  # Online
                    "bio": "Local Andheri electrician. Fast home service in Mumbai areas.",
                    "completed_jobs": 64,
                    "aadhar_card": "222233334444",
                    "pan_card": "BCDEF2345G"
                }
            },
            {
                "name": "Amit Sharma",
                "email": "amit@purakam.in",
                "password_hash": hash_password("partner123"),
                "phone": "+919999111122",
                "address": "Dadar West, Mumbai, MH - 400028",
                "latitude": 19.0178,
                "longitude": 72.8302,
                "role": "partner",
                "profile": {
                    "service_category": "AC & Appliance Repair",
                    "hourly_rate": 299.0,
                    "rating": 4.6,
                    "availability_status": True,  # Online
                    "bio": "Expert AC & Appliance repair technician in Dadar Mumbai.",
                    "completed_jobs": 98,
                    "aadhar_card": "333344445555",
                    "pan_card": "CDEFG3456H"
                }
            },
            {
                "name": "Suresh Patel",
                "email": "suresh@purakam.in",
                "password_hash": hash_password("partner123"),
                "phone": "+919999333344",
                "address": "Ghatkopar East, Mumbai, MH - 400077",
                "latitude": 19.0856,
                "longitude": 72.9082,
                "role": "partner",
                "profile": {
                    "service_category": "Inverter & Battery",
                    "hourly_rate": 450.0,
                    "rating": 4.9,
                    "availability_status": False,  # Offline
                    "bio": "Specialized in home inverters, battery backups in Ghatkopar Mumbai.",
                    "completed_jobs": 210,
                    "aadhar_card": "444455556666",
                    "pan_card": "DEFGH4567I"
                }
            },
            {
                "name": "Priya Devi",
                "email": "priya@purakam.in",
                "password_hash": hash_password("partner123"),
                "phone": "+919999555566",
                "address": "Hiranandani Gardens, Powai, Mumbai, MH - 400076",
                "latitude": 19.1176,
                "longitude": 72.9060,
                "role": "partner",
                "profile": {
                    "service_category": "Geyser & Water Heater",
                    "hourly_rate": 350.0,
                    "rating": 4.7,
                    "availability_status": True,  # Online
                    "bio": "Professional geyser, thermostat repair technician in Powai Mumbai.",
                    "completed_jobs": 87,
                    "aadhar_card": "555566667777",
                    "pan_card": "EFGHI5678J"
                }
            }
        ]

        print("Seeding mock partners and profiles...")
        for p_data in partners:
            profile_data = p_data.pop("profile")
            existing = db.query(User).filter(User.email == p_data["email"]).first()
            if not existing:
                partner_user = User(**p_data)
                db.add(partner_user)
                db.commit()
                db.refresh(partner_user)
                
                profile = PartnerProfile(user_id=partner_user.id, **profile_data)
                db.add(profile)
        db.commit()
        
        print("Database seeded successfully!")
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()

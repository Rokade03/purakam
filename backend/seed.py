from sqlalchemy import inspect, text
from backend.database import engine, Base, SessionLocal, User, PartnerProfile, ServiceCategory, Booking, ChatMessage, Review, PartnerDeclinedBooking, hash_password

def seed_db():
    print("Initializing database tables & schema migrations...")
    Base.metadata.create_all(bind=engine)
    
    # Run automatic schema migrations for additional columns
    inspector = inspect(engine)
    if inspector.has_table('bookings'):
        columns = [col['name'] for col in inspector.get_columns('bookings')]
        if 'otp' not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN otp VARCHAR(255);"))
        if 'area_name' not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN area_name VARCHAR(255);"))
        if 'accepted_at' not in columns:
            db_type = "TIMESTAMP" if engine.dialect.name == "postgresql" else "DATETIME"
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE bookings ADD COLUMN accepted_at {db_type};"))
        if 'pincode' not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN pincode VARCHAR(6);"))
        if 'razorpay_order_id' not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN razorpay_order_id VARCHAR(255);"))
        if 'razorpay_payment_id' not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN razorpay_payment_id VARCHAR(255);"))
        if 'razorpay_signature' not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN razorpay_signature VARCHAR(255);"))

    if inspector.has_table('partner_profiles'):
        columns = [col['name'] for col in inspector.get_columns('partner_profiles')]
        if 'aadhar_card' not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE partner_profiles ADD COLUMN aadhar_card VARCHAR(255);"))
        if 'pan_card' not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE partner_profiles ADD COLUMN pan_card VARCHAR(255);"))
        if 'experience_years' not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE partner_profiles ADD COLUMN experience_years INTEGER DEFAULT 2;"))

    db = SessionLocal()
    try:
        # 1. Clean extra accounts and stale bookings
        print("Cleaning up database to leave only 3 clean test accounts...")
        db.query(ChatMessage).delete()
        db.query(Review).delete()
        db.query(PartnerDeclinedBooking).delete()
        db.query(Booking).delete()
        db.commit()

        TEST_EMAILS = {"user@purakam.in", "partner@purakam.in", "acservice@purakam.in"}
        non_test_users = db.query(User).filter(User.email.notin_(TEST_EMAILS)).all()
        for u in non_test_users:
            if u.partner_profile:
                db.delete(u.partner_profile)
            db.delete(u)
        db.commit()

        # 2. Seed Service Categories
        categories = [
            {"name": "Electrician", "icon_key": "zap", "description": "General electrical work, fan installations, light fittings.", "base_price": 199.0},
            {"name": "Switchboard & Wiring", "icon_key": "plug", "description": "Switchboard repairs, socket replacement, short circuit fixes.", "base_price": 249.0},
            {"name": "AC & Appliance Repair", "icon_key": "wind", "description": "AC servicing, refrigerator geyser faults, diagnostics.", "base_price": 399.0},
            {"name": "Inverter & Battery", "icon_key": "activity", "description": "Home inverter setups, backup battery diagnostics.", "base_price": 499.0},
            {"name": "Geyser & Water Heater", "icon_key": "droplet", "description": "Geyser element replacement, thermostat repairs.", "base_price": 299.0}
        ]
        for cat_data in categories:
            existing = db.query(ServiceCategory).filter(ServiceCategory.name == cat_data["name"]).first()
            if not existing:
                db.add(ServiceCategory(**cat_data))
        db.commit()

        # 3. Seed 3 Clean Test Accounts
        # Account 1: Customer
        cust = db.query(User).filter(User.email == "user@purakam.in").first()
        if not cust:
            cust = User(
                name="Rahul Sharma (Customer)",
                email="user@purakam.in",
                password_hash=hash_password("password123"),
                phone="+919876543210",
                address="Bandra West, Mumbai",
                latitude=19.0600,
                longitude=72.8258,
                role="customer",
                is_verified=True
            )
            db.add(cust)
            db.commit()
        else:
            cust.password_hash = hash_password("password123")
            cust.is_verified = True
            db.commit()

        # Account 2: Electrician Partner
        part1 = db.query(User).filter(User.email == "partner@purakam.in").first()
        if not part1:
            part1 = User(
                name="Rajesh Kumar (Electrician)",
                email="partner@purakam.in",
                password_hash=hash_password("password123"),
                phone="+919876543211",
                address="Khar West, Mumbai",
                latitude=19.0700,
                longitude=72.8358,
                role="partner",
                is_verified=True
            )
            db.add(part1)
            db.commit()
            db.refresh(part1)
        else:
            part1.password_hash = hash_password("password123")
            part1.is_verified = True
            db.commit()

        p1_profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == part1.id).first()
        if not p1_profile:
            p1_profile = PartnerProfile(
                user_id=part1.id,
                service_category="Electrician",
                hourly_rate=350.0,
                experience_years=3,
                availability_status=True,
                rating=4.9,
                completed_jobs=12,
                aadhar_card="123456789012",
                pan_card="ABCDE1234F"
            )
            db.add(p1_profile)
            db.commit()

        # Account 3: AC Repair Partner
        part2 = db.query(User).filter(User.email == "acservice@purakam.in").first()
        if not part2:
            part2 = User(
                name="Amit Verma (AC Repair)",
                email="acservice@purakam.in",
                password_hash=hash_password("password123"),
                phone="+919876543212",
                address="Andheri West, Mumbai",
                latitude=19.1197,
                longitude=72.8468,
                role="partner",
                is_verified=True
            )
            db.add(part2)
            db.commit()
            db.refresh(part2)
        else:
            part2.password_hash = hash_password("password123")
            part2.is_verified = True
            db.commit()

        p2_profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == part2.id).first()
        if not p2_profile:
            p2_profile = PartnerProfile(
                user_id=part2.id,
                service_category="AC & Appliance Repair",
                hourly_rate=450.0,
                experience_years=4,
                availability_status=True,
                rating=4.8,
                completed_jobs=24,
                aadhar_card="987654321098",
                pan_card="XYZDE9876F"
            )
            db.add(p2_profile)
            db.commit()

        print("Database seed & cleanup completed! 3 clean test accounts active.")
    except Exception as e:
        print(f"Seed exception: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()

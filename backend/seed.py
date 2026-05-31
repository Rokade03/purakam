from backend.database import engine, Base, SessionLocal, User, PartnerProfile, ServiceCategory, hash_password

def seed_db():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    
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
                "address": "402, Marvel Crest, Koregaon Park, Pune, Maharashtra - 411001",
                "latitude": 18.5362,
                "longitude": 73.8940,
                "role": "customer"
            },
            {
                "name": "Purakam Admin",
                "email": "admin@purakam.in",
                "password_hash": hash_password("admin123"),
                "phone": "+919999000099",
                "address": "Purakam HQ, Koregaon Park, Pune, MH",
                "latitude": 18.5362,
                "longitude": 73.8940,
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
                "address": "Block C, Sector 62, Noida, UP - 201301",
                "latitude": 28.6280,
                "longitude": 77.3800,
                "role": "partner",
                "profile": {
                    "service_category": "Electrician",
                    "hourly_rate": 250.0,
                    "rating": 4.8,
                    "availability_status": True,  # Online
                    "bio": "Certified electrician with 8+ years experience. Noida based.",
                    "completed_jobs": 154
                }
            },
            {
                "name": "Vijay Shinde",
                "email": "vijay@purakam.in",
                "password_hash": hash_password("partner123"),
                "phone": "+919999222233",
                "address": "Yerwada, Pune, MH - 411006",
                "latitude": 18.5529,
                "longitude": 73.8796,
                "role": "partner",
                "profile": {
                    "service_category": "Electrician",
                    "hourly_rate": 280.0,
                    "rating": 4.5,
                    "availability_status": True,  # Online
                    "bio": "Local Yerwada electrician. Fast home service in Pune areas.",
                    "completed_jobs": 64
                }
            },
            {
                "name": "Amit Sharma",
                "email": "amit@purakam.in",
                "password_hash": hash_password("partner123"),
                "phone": "+919999111122",
                "address": "H-32, Lajpat Nagar, New Delhi - 110024",
                "latitude": 28.5684,
                "longitude": 77.2503,
                "role": "partner",
                "profile": {
                    "service_category": "AC & Appliance Repair",
                    "hourly_rate": 299.0,
                    "rating": 4.6,
                    "availability_status": True,  # Online
                    "bio": "Expert AC & Appliance repair technician. Noida and Delhi NCR coverage.",
                    "completed_jobs": 98
                }
            },
            {
                "name": "Suresh Patel",
                "email": "suresh@purakam.in",
                "password_hash": hash_password("partner123"),
                "phone": "+919999333344",
                "address": "45, GIDC Estate, Ahmedabad, Gujarat - 380009",
                "latitude": 23.0225,
                "longitude": 72.5714,
                "role": "partner",
                "profile": {
                    "service_category": "Inverter & Battery",
                    "hourly_rate": 450.0,
                    "rating": 4.9,
                    "availability_status": False,  # Offline
                    "bio": "Specialized in home inverters, battery backups, and power testing.",
                    "completed_jobs": 210
                }
            },
            {
                "name": "Priya Devi",
                "email": "priya@purakam.in",
                "password_hash": hash_password("partner123"),
                "phone": "+919999555566",
                "address": "Flat 101, Lakeview Apts, HSR Layout, Bengaluru, KA - 560102",
                "latitude": 18.5463,
                "longitude": 73.9033,
                "role": "partner",
                "profile": {
                    "service_category": "Geyser & Water Heater",
                    "hourly_rate": 350.0,
                    "rating": 4.7,
                    "availability_status": True,  # Online
                    "bio": "Professional geyser, thermostat, and water heater repair technician in Pune.",
                    "completed_jobs": 87
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

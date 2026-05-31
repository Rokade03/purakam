import requests
import time

API_URL = "http://127.0.0.1:8000/api"

def run_tests():
    print("=== STARTING INTEGRATION TESTS ===")
    
    # 1. Register test customer
    print("\n1. Registering test customer...")
    cust_payload = {
        "name": "Test Customer",
        "email": "test_customer@purakam.in",
        "password": "password123",
        "phone": "+919900000001",
        "address": "123, Testing Boulevard, Pune, MH",
        "role": "customer"
    }
    r = requests.post(f"{API_URL}/auth/register", json=cust_payload)
    if r.status_code == 200:
        print("Customer registered successfully!")
    elif r.status_code == 400 and "already registered" in r.text:
        print("Customer already registered. Proceeding.")
    else:
        print(f"Failed to register customer: {r.text}")
        return

    # 2. Register test partner
    print("\n2. Registering test partner (Electrician)...")
    part_payload = {
        "name": "Test Electrician",
        "email": "test_partner@purakam.in",
        "password": "password123",
        "phone": "+919900000002",
        "address": "456, Skill Road, Pune, MH",
        "role": "partner",
        "service_category": "Electrician",
        "hourly_rate": 300.0,
        "bio": "Certified test electrician."
    }
    r = requests.post(f"{API_URL}/auth/register", json=part_payload)
    if r.status_code == 200:
        print("Partner registered successfully!")
    elif r.status_code == 400 and "already registered" in r.text:
        print("Partner already registered. Proceeding.")
    else:
        print(f"Failed to register partner: {r.text}")
        return

    # 3. Login Customer and Partner to get real JWT tokens
    print("\n3. Logging in users to fetch sessions...")
    # Customer login
    r = requests.post(f"{API_URL}/auth/login", json={"email": "test_customer@purakam.in", "password": "password123"})
    assert r.status_code == 200, "Customer login failed"
    cust_token = r.json()["access_token"]
    cust_id = r.json()["id"]
    cust_headers = {"Authorization": f"Bearer {cust_token}"}
    print(f"Customer JWT Token fetched successfully.")

    # Partner login
    r = requests.post(f"{API_URL}/auth/login", json={"email": "test_partner@purakam.in", "password": "password123"})
    assert r.status_code == 200, "Partner login failed"
    part_token = r.json()["access_token"]
    part_id = r.json()["id"]
    part_headers = {"Authorization": f"Bearer {part_token}"}
    print(f"Partner JWT Token fetched successfully.")

    # 4. Turn Partner Online
    print("\n4. Toggling partner status to ONLINE...")
    r = requests.put(f"{API_URL}/partner/profile", json={"availability_status": True}, headers=part_headers)
    assert r.status_code == 200, "Failed to toggle partner status"
    assert r.json()["availability_status"] is True
    print("Partner status updated to: ONLINE")

    # 5. Place booking as customer with Pune coordinates (Geographic Proximity Test)
    # Online Electricians:
    # - Rajesh Kumar (Noida, far, rating 4.8)
    # - Vijay Shinde (Pune, near, rating 4.5)
    # Booking at Koregaon Park, Pune should match Vijay Shinde.
    print("\n5. Placing booking with Pune coordinates (Koregaon Park)...")
    booking_payload_pune = {
        "service_category": "Electrician",
        "booking_date": "2026-06-01",
        "time_slot": "10:00 AM - 12:00 PM",
        "details": "Install living room lights.",
        "price": 349.0,
        "address": "Marvel Crest, Koregaon Park, Pune",
        "payment_method": "UPI",
        "latitude": 18.5362,
        "longitude": 73.8940
    }
    r = requests.post(f"{API_URL}/bookings", json=booking_payload_pune, headers=cust_headers)
    assert r.status_code == 200, f"Failed to place Pune booking: {r.text}"
    booking_data = r.json()
    pune_booking_id = booking_data["id"]
    assigned_partner_name = booking_data["partner"]["name"]
    print(f"Pune Booking created (ID: #SRV{pune_booking_id}). Assigned Partner: {assigned_partner_name}")
    assert assigned_partner_name == "Vijay Shinde", f"Expected Vijay Shinde (Pune), got {assigned_partner_name}"

    # 5b. Place booking explicitly requesting Rajesh Kumar (Bypassing Proximity Matchmaking)
    # Booking at Koregaon Park, Pune should normally match Vijay Shinde due to proximity.
    # But passing partner_id = rajesh_id should bypass it and assign Rajesh Kumar directly.
    print("\n5b. Placing booking requesting specific partner (Rajesh Kumar)...")
    r = requests.get(f"{API_URL}/partners?category=Electrician")
    assert r.status_code == 200
    rajesh_id = None
    for p in r.json():
        if p["name"] == "Rajesh Kumar":
            rajesh_id = p["id"]
            break
    assert rajesh_id is not None, "Failed to find Rajesh Kumar in partners list"

    booking_payload_specific = {
        "service_category": "Electrician",
        "booking_date": "2026-06-01",
        "time_slot": "04:00 PM - 06:00 PM",
        "details": "AC socket installation.",
        "price": 299.0,
        "address": "Marvel Crest, Koregaon Park, Pune",
        "payment_method": "UPI",
        "latitude": 18.5362,
        "longitude": 73.8940,
        "partner_id": rajesh_id
    }
    r = requests.post(f"{API_URL}/bookings", json=booking_payload_specific, headers=cust_headers)
    assert r.status_code == 200, f"Failed to place specific booking: {r.text}"
    booking_data = r.json()
    specific_booking_id = booking_data["id"]
    assigned_partner_name = booking_data["partner"]["name"]
    print(f"Specific Booking created (ID: #SRV{specific_booking_id}). Assigned Partner: {assigned_partner_name}")
    assert assigned_partner_name == "Rajesh Kumar", f"Expected Rajesh Kumar (specific requested), got {assigned_partner_name}"

    # 6. Place booking without coordinates (Fallback High-Rating Test)
    # Rajesh Kumar (Noida, rating 4.8) vs Vijay Shinde (Pune, rating 4.5) vs Test Electrician (rating 5.0).
    # Omitted coordinates should trigger fallback, picking highest rating (Test Electrician).
    print("\n6. Placing booking without coordinates (Fallback rating test)...")
    booking_payload_fallback = {
        "service_category": "Electrician",
        "booking_date": "2026-06-02",
        "time_slot": "02:00 PM - 04:00 PM",
        "details": "Fix faulty socket.",
        "price": 199.0,
        "address": "Delhi NCR address",
        "payment_method": "COD",
        "latitude": None,
        "longitude": None
    }
    r = requests.post(f"{API_URL}/bookings", json=booking_payload_fallback, headers=cust_headers)
    assert r.status_code == 200, f"Failed to place fallback booking: {r.text}"
    booking_data = r.json()
    fallback_booking_id = booking_data["id"]
    assigned_partner_name = booking_data["partner"]["name"]
    fallback_partner_id = booking_data["partner_id"]
    print(f"Fallback Booking created (ID: #SRV{fallback_booking_id}). Assigned Partner: {assigned_partner_name}")
    assert assigned_partner_name == "Test Electrician", f"Expected Test Electrician (5.0), got {assigned_partner_name}"

    # 7. Test Chat Messaging System
    print("\n7. Testing Chat Messaging system...")
    # Customer sends message to Test Electrician for fallback booking
    chat_payload_cust = {"message_text": "Hi, please bring an extra extension board."}
    r = requests.post(f"{API_URL}/bookings/{fallback_booking_id}/messages", json=chat_payload_cust, headers=cust_headers)
    assert r.status_code == 200, f"Customer chat send failed: {r.text}"
    print("Customer: Hi, please bring an extra extension board.")
    
    # Partner reads messages
    r = requests.get(f"{API_URL}/bookings/{fallback_booking_id}/messages", headers=part_headers)
    assert r.status_code == 200, f"Partner chat read failed: {r.text}"
    messages = r.json()
    assert len(messages) == 1
    assert messages[0]["message_text"] == "Hi, please bring an extra extension board."
    
    # Partner replies
    chat_payload_part = {"message_text": "Sure, I will carry one with me."}
    r = requests.post(f"{API_URL}/bookings/{fallback_booking_id}/messages", json=chat_payload_part, headers=part_headers)
    assert r.status_code == 200, f"Partner chat send failed: {r.text}"
    print("Partner (Test Electrician): Sure, I will carry one with me.")
    
    # Customer fetches updated chat history
    r = requests.get(f"{API_URL}/bookings/{fallback_booking_id}/messages", headers=cust_headers)
    assert r.status_code == 200, f"Customer chat history load failed: {r.text}"
    messages = r.json()
    assert len(messages) == 2
    print("Chat system verified: history loaded correctly.")

    # 8. Upload mock image file
    print("\n8. Customer uploading mock picture attachment to Pune booking...")
    mock_file = {"file": ("test_image.jpg", b"fake-binary-image-data-contents", "image/jpeg")}
    r = requests.post(f"{API_URL}/bookings/{pune_booking_id}/upload", files=mock_file, headers=cust_headers)
    assert r.status_code == 200, f"Failed to upload attachment: {r.text}"
    print(f"Attachment uploaded successfully! Filename: {r.json()['filename']}")

    # 9. Log in as Vijay Shinde to progress the Pune booking
    r = requests.post(f"{API_URL}/auth/login", json={"email": "vijay@purakam.in", "password": "partner123"})
    assert r.status_code == 200, "Vijay login failed"
    vijay_token = r.json()["access_token"]
    vijay_headers = {"Authorization": f"Bearer {vijay_token}"}

    # Progress States: accepted -> on_the_way -> in_progress -> completed
    print("\n9. Simulating Pune booking state progression...")
    r = requests.put(f"{API_URL}/bookings/{pune_booking_id}/status?new_status=on_the_way", headers=vijay_headers)
    assert r.status_code == 200, f"Failed to progress to 'on_the_way': {r.text}"
    print(f"Status updated: {r.json()['status']}")

    r = requests.put(f"{API_URL}/bookings/{pune_booking_id}/status?new_status=in_progress", headers=vijay_headers)
    assert r.status_code == 200, f"Failed to progress to 'in_progress': {r.text}"
    print(f"Status updated: {r.json()['status']}")

    r = requests.put(f"{API_URL}/bookings/{pune_booking_id}/status?new_status=completed", headers=vijay_headers)
    assert r.status_code == 200, f"Failed to progress to 'completed': {r.text}"
    print(f"Status updated: {r.json()['status']}")

    # 10. Customer submits review
    print("\n10. Customer submitting review for completed Pune booking...")
    review_payload = {
        "booking_id": pune_booking_id,
        "rating": 5,
        "comment": "Outstanding service! Highly recommended."
    }
    r = requests.post(f"{API_URL}/reviews", json=review_payload, headers=cust_headers)
    assert r.status_code == 200, f"Failed to submit review: {r.text}"
    print(f"Review submitted successfully! Rating: {r.json()['rating']} Stars")

    # 11. Admin Console Operations Verification
    print("\n11. Verifying Admin Console backend operations...")
    # Admin login
    r = requests.post(f"{API_URL}/auth/login", json={"email": "admin@purakam.in", "password": "admin123"})
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    admin_token = r.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("Admin logged in successfully.")

    # Audit chat history as Admin
    r = requests.get(f"{API_URL}/bookings/{fallback_booking_id}/messages", headers=admin_headers)
    assert r.status_code == 200, f"Admin failed to read chat messages: {r.text}"
    messages = r.json()
    assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"
    print("Admin successfully monitored/read the booking chat messages.")

    # Get admin stats
    r = requests.get(f"{API_URL}/admin/stats", headers=admin_headers)
    assert r.status_code == 200, f"Failed to fetch admin stats: {r.text}"
    stats_data = r.json()
    assert stats_data["total_bookings"] >= 2
    assert stats_data["total_revenue"] >= 349.0
    print(f"Admin stats verified. Total Bookings: {stats_data['total_bookings']}, Revenue: {stats_data['total_revenue']}")

    # Get admin users list
    r = requests.get(f"{API_URL}/admin/users", headers=admin_headers)
    assert r.status_code == 200, f"Failed to fetch admin users registry: {r.text}"
    users_list = r.json()
    assert len(users_list) >= 3
    print(f"Admin user list verified. Total users registered: {len(users_list)}")

    # Get admin bookings ledger
    r = requests.get(f"{API_URL}/admin/bookings", headers=admin_headers)
    assert r.status_code == 200, f"Failed to fetch admin bookings: {r.text}"
    bookings_ledger = r.json()
    assert len(bookings_ledger) >= 2
    print("Admin bookings ledger verified.")

    # Create new service category
    new_service_payload = {
        "name": "Wall Painter",
        "icon_key": "paint-brush",
        "description": "Premium internal and external wall painting services.",
        "base_price": 450.0
    }
    r = requests.post(f"{API_URL}/admin/services", json=new_service_payload, headers=admin_headers)
    assert r.status_code == 200, f"Failed to create new category: {r.text}"
    painter_cat = r.json()
    painter_id = painter_cat["id"]
    print(f"Admin created new category: {painter_cat['name']} (Base Price: ₹{painter_cat['base_price']})")

    # Update category price
    r = requests.put(f"{API_URL}/admin/services/{painter_id}", json={"base_price": 499.0}, headers=admin_headers)
    assert r.status_code == 200, f"Failed to update category price: {r.text}"
    assert r.json()["base_price"] == 499.0
    print(f"Admin updated category base price to: ₹{r.json()['base_price']}")

    # Clean up: Delete created category
    r = requests.delete(f"{API_URL}/admin/services/{painter_id}", headers=admin_headers)
    assert r.status_code == 200, f"Failed to delete category: {r.text}"
    print("Admin successfully deleted the test category to keep database clean.")

    # Security Verification: Customer cannot access admin routes
    print("\nSecurity: Verifying customer role cannot access admin routes...")
    r = requests.get(f"{API_URL}/admin/stats", headers=cust_headers)
    assert r.status_code == 403, f"Security Breach! Customer was able to query admin stats: {r.status_code}"
    print("Security block verified (HTTP 403 Forbidden returned for customers).")

    print("\n=== ALL INTEGRATION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_tests()

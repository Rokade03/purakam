import os
from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
import requests

app = Flask(__name__)
app.secret_key = "purakam_super_secret_session_key_for_india_market"

BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8000/api")

# Helper to get request headers for backend
def get_auth_headers():
    token = session.get("auth_token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

@app.context_processor
def inject_backend_url():
    base_url = BACKEND_API_URL.rsplit("/api", 1)[0]
    return {
        "BACKEND_API_URL": BACKEND_API_URL,
        "BACKEND_BASE_URL": base_url
    }

# === Web Routes ===

@app.route("/")
def index():
    # Fetch service categories from FastAPI
    categories = []
    try:
        r = requests.get(f"{BACKEND_API_URL}/services")
        if r.status_code == 200:
            categories = r.json()
    except Exception as e:
        print(f"Backend API error: {e}")
        
    return render_template("index.html", categories=categories)

@app.route("/services")
def services():
    category = request.args.get("category", "")
    categories = []
    partners = []
    
    try:
        # Get all categories for filter dropdown
        rc = requests.get(f"{BACKEND_API_URL}/services")
        if rc.status_code == 200:
            categories = rc.json()
            
        # Get partners in the category
        rp = requests.get(f"{BACKEND_API_URL}/partners", params={"category": category} if category else {})
        if rp.status_code == 200:
            partners = rp.json()
    except Exception as e:
        print(f"Backend API error: {e}")

    return render_template("services.html", categories=categories, selected_category=category, partners=partners)

@app.route("/book/<category_name>")
def book(category_name):
    if "user_id" not in session:
        flash("Please log in to book a service.", "warning")
        return redirect(url_for("login", next=request.path))
        
    if session.get("user_role") == "partner":
        flash("Partners cannot book services. Please log in with a customer account.", "danger")
        return redirect(url_for("index"))
        
    partner_id = request.args.get("partner_id")
    partner_name = ""
    
    # Get base price for this category
    base_price = 299.0
    try:
        r = requests.get(f"{BACKEND_API_URL}/services")
        if r.status_code == 200:
            for cat in r.json():
                if cat["name"] == category_name:
                    base_price = cat["base_price"]
                    break
                    
        if partner_id:
            rp = requests.get(f"{BACKEND_API_URL}/partners", params={"category": category_name})
            if rp.status_code == 200:
                for p in rp.json():
                    if str(p["id"]) == str(partner_id):
                          partner_name = p["name"]
                          break
    except Exception as e:
        print(f"Backend API error: {e}")

    return render_template(
        "book.html", 
        category_name=category_name, 
        base_price=base_price,
        partner_id=partner_id,
        partner_name=partner_name
    )

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") == "partner":
        return redirect(url_for("partner_dashboard"))
        
    bookings = []
    try:
        r = requests.get(f"{BACKEND_API_URL}/bookings", headers=get_auth_headers())
        if r.status_code == 200:
            bookings = r.json()
    except Exception as e:
        print(f"Error fetching bookings: {e}")
        
    return render_template("dashboard.html", bookings=bookings)
@app.route("/partner/dashboard")
def partner_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "partner":
        return redirect(url_for("dashboard"))
        
    bookings = []
    incoming_jobs = []
    partner_online_status = False
    try:
        ru = requests.get(f"{BACKEND_API_URL}/auth/me", headers=get_auth_headers())
        if ru.status_code == 200:
            user_info = ru.json()
            if user_info.get("partner_profile"):
                partner_online_status = user_info["partner_profile"].get("availability_status", False)

        r = requests.get(f"{BACKEND_API_URL}/bookings", headers=get_auth_headers())
        if r.status_code == 200:
            bookings = r.json()
            
        rj = requests.get(f"{BACKEND_API_URL}/partner/incoming-bookings", headers=get_auth_headers())
        if rj.status_code == 200:
            incoming_jobs = rj.json()
    except Exception as e:
        print(f"Error fetching partner data: {e}")
        
    return render_template(
        "partner.html", 
        bookings=bookings, 
        incoming_jobs=incoming_jobs, 
        partner_online_status=partner_online_status
    )

@app.route("/admin/dashboard")
def admin_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("user_role") != "admin":
        flash("Unauthorized access. Admin role required.", "danger")
        return redirect(url_for("index"))
        
    stats = {}
    users = []
    bookings = []
    categories = []
    
    try:
        headers = get_auth_headers()
        rs = requests.get(f"{BACKEND_API_URL}/admin/stats", headers=headers)
        if rs.status_code == 200:
            stats = rs.json()
            
        ru = requests.get(f"{BACKEND_API_URL}/admin/users", headers=headers)
        if ru.status_code == 200:
            users = ru.json()
            
        rb = requests.get(f"{BACKEND_API_URL}/admin/bookings", headers=headers)
        if rb.status_code == 200:
            bookings = rb.json()
            
        rc = requests.get(f"{BACKEND_API_URL}/services")
        if rc.status_code == 200:
            categories = rc.json()
    except Exception as e:
        print(f"Error loading admin dashboard data: {e}")
        
    return render_template(
        "admin.html",
        stats=stats,
        users=users,
        bookings=bookings,
        categories=categories
    )

# === Auth Routing ===

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        try:
            r = requests.post(
                f"{BACKEND_API_URL}/auth/login",
                json={"email": email, "password": password}
            )
            if r.status_code == 200:
                user_data = r.json()
                session["user_id"] = user_data["id"]
                session["user_name"] = user_data["name"]
                session["user_email"] = user_data["email"]
                session["user_role"] = user_data["role"]
                session["user_address"] = user_data.get("address")
                session["auth_token"] = user_data.get("access_token")
                
                flash(f"Welcome back, {user_data['name']}!", "success")
                next_page = request.args.get("next")
                if next_page:
                    return redirect(next_page)
                
                if user_data["role"] == "partner":
                    return redirect(url_for("partner_dashboard"))
                return redirect(url_for("dashboard"))
            else:
                error_msg = r.json().get("detail", "Login failed")
                flash(error_msg, "danger")
        except Exception as e:
            flash(f"Backend server is offline: {e}", "danger")
            
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    # Fetch service categories for partner signup
    categories = []
    try:
        r = requests.get(f"{BACKEND_API_URL}/services")
        if r.status_code == 200:
            categories = r.json()
    except Exception as e:
        print(f"Error loading categories: {e}")

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        phone = request.form.get("phone")
        address = request.form.get("address")
        role = request.form.get("role", "customer")
        
        payload = {
            "name": name,
            "email": email,
            "password": password,
            "phone": phone,
            "address": address,
            "role": role
        }
        
        # If partner, add additional profile parameters
        if role == "partner":
            payload["service_category"] = request.form.get("service_category")
            payload["hourly_rate"] = float(request.form.get("hourly_rate", 250))
            payload["bio"] = request.form.get("bio", "")
            
        try:
            r = requests.post(f"{BACKEND_API_URL}/auth/register", json=payload)
            if r.status_code == 200:
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for("login"))
            else:
                error_msg = r.json().get("detail", "Registration failed")
                flash(error_msg, "danger")
        except Exception as e:
            flash(f"Backend server error: {e}", "danger")
            
    return render_template("register.html", categories=categories)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

import os
from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
import requests

app = Flask(__name__)
app.secret_key = "purakam_super_secret_session_key_for_india_market"

BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8000/api").strip()
if BACKEND_API_URL:
    if "://" not in BACKEND_API_URL and "." not in BACKEND_API_URL and "localhost" not in BACKEND_API_URL and "127.0.0.1" not in BACKEND_API_URL:
        BACKEND_API_URL = f"https://{BACKEND_API_URL}.onrender.com"
    if not BACKEND_API_URL.startswith("http://") and not BACKEND_API_URL.startswith("https://"):
        BACKEND_API_URL = f"https://{BACKEND_API_URL}"
    if not BACKEND_API_URL.endswith("/api"):
        BACKEND_API_URL = f"{BACKEND_API_URL.rstrip('/')}/api"



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
        "BACKEND_BASE_URL": base_url,
        "RAZORPAY_KEY_ID": os.environ.get("RAZORPAY_KEY_ID", "rzp_test_dummy_key_id")
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
                if error_msg == "EMAIL_NOT_VERIFIED":
                    flash("Your email address is not verified yet. Please enter the OTP verification code.", "warning")
                    return redirect(url_for("verify_email", email=email))
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
            payload["aadhar_card"] = request.form.get("aadhar_card")
            payload["pan_card"] = request.form.get("pan_card")
            
        try:
            r = requests.post(f"{BACKEND_API_URL}/auth/register", json=payload)
            if r.status_code == 200:
                res = r.json()
                v_code = res.get("verification_code", "")
                flash("Registration successful! Please enter the 6-digit verification OTP code sent to your email.", "info")
                return redirect(url_for("verify_email", email=email, code=v_code))
            else:
                error_msg = r.json().get("detail", "Registration failed")
                flash(error_msg, "danger")
        except Exception as e:
            flash(f"Backend server error: {e}", "danger")
            
    return render_template("register.html", categories=categories)

@app.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    email = request.args.get("email") or request.form.get("email", "")
    code = request.args.get("code") or request.form.get("code", "")
    
    if request.method == "POST":
        email = request.form.get("email")
        otp_code = request.form.get("code")
        try:
            r = requests.post(f"{BACKEND_API_URL}/auth/verify-email", json={"email": email, "code": otp_code})
            if r.status_code == 200:
                user_data = r.json()
                session["auth_token"] = user_data.get("access_token")
                session["user_role"] = user_data.get("role")
                session["user_name"] = user_data.get("name")
                session["user_id"] = user_data.get("id")
                flash("Email verified successfully! Welcome to Purakam.", "success")
                return redirect(url_for("dashboard"))
            else:
                error_msg = r.json().get("detail", "Invalid verification code")
                flash(error_msg, "danger")
        except Exception as e:
            flash(f"Backend server error: {e}", "danger")
            
    return render_template("verify_email.html", email=email, code=code)


GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

@app.route("/login/google")
def login_google():
    next_page = request.args.get("next", "")
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        # Redirect to mock consent page
        return redirect(url_for("login_google_mock", next=next_page))
    
    import secrets
    state = secrets.token_hex(16)
    session["oauth_state"] = state
    session["oauth_next"] = next_page
    
    # Construct Google OAuth Authorization URL
    redirect_uri = url_for("login_google_callback", _external=True)
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"response_type=code&"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"scope=openid%20email%20profile&"
        f"state={state}"
    )
    return redirect(google_auth_url)

@app.route("/login/google/callback")
def login_google_callback():
    state = request.args.get("state")
    code = request.args.get("code")
    
    # Verify state to prevent CSRF
    if not state or state != session.pop("oauth_state", None):
        flash("Invalid state token. Possible CSRF attack detected.", "danger")
        return redirect(url_for("login"))
        
    if not code:
        flash("Authorization code not returned from Google.", "danger")
        return redirect(url_for("login"))
        
    # Exchange code for access token
    redirect_uri = url_for("login_google_callback", _external=True)
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    try:
        token_res = requests.post(token_url, data=payload)
        if token_res.status_code != 200:
            flash(f"Failed to exchange code: {token_res.text}", "danger")
            return redirect(url_for("login"))
            
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        
        # Get user info
        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        userinfo_res = requests.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
        if userinfo_res.status_code != 200:
            flash("Failed to retrieve user info from Google.", "danger")
            return redirect(url_for("login"))
            
        user_info = userinfo_res.json()
        email = user_info.get("email")
        name = user_info.get("name", "Google User")
        
        # Call backend to register/login Google user
        r = requests.post(
            f"{BACKEND_API_URL}/auth/google",
            json={"email": email, "name": name}
        )
        if r.status_code == 200:
            user_data = r.json()
            session["user_id"] = user_data["id"]
            session["user_name"] = user_data["name"]
            session["user_email"] = user_data["email"]
            session["user_role"] = user_data["role"]
            session["user_address"] = user_data.get("address")
            session["auth_token"] = user_data.get("access_token")
            
            flash(f"Welcome, {user_data['name']} (signed in with Google)!", "success")
            next_page = session.pop("oauth_next", None)
            if next_page:
                return redirect(next_page)
            if user_data["role"] == "partner":
                return redirect(url_for("partner_dashboard"))
            return redirect(url_for("dashboard"))
        else:
            error_msg = r.json().get("detail", "Google authentication failed")
            flash(error_msg, "danger")
    except Exception as e:
        flash(f"Google OAuth error: {e}", "danger")
        
    return redirect(url_for("login"))

@app.route("/login/google/mock", methods=["GET", "POST"])
def login_google_mock():
    next_page = request.args.get("next", "")
    if request.method == "POST":
        email = request.form.get("email")
        name = request.form.get("name")
        
        if not email or "@" not in email:
            flash("Please enter a valid mock email address.", "danger")
            return render_template("mock_google_consent.html", next=next_page)
            
        try:
            r = requests.post(
                f"{BACKEND_API_URL}/auth/google",
                json={"email": email, "name": name}
            )
            if r.status_code == 200:
                user_data = r.json()
                session["user_id"] = user_data["id"]
                session["user_name"] = user_data["name"]
                session["user_email"] = user_data["email"]
                session["user_role"] = user_data["role"]
                session["user_address"] = user_data.get("address")
                session["auth_token"] = user_data.get("access_token")
                
                flash(f"Welcome, {user_data['name']} (signed in with Mock Google)!", "success")
                if next_page:
                    return redirect(next_page)
                if user_data["role"] == "partner":
                    return redirect(url_for("partner_dashboard"))
                return redirect(url_for("dashboard"))
            else:
                error_msg = r.json().get("detail", "Mock Google login failed")
                flash(error_msg, "danger")
        except Exception as e:
            flash(f"Mock Google login error: {e}", "danger")
            
    return render_template("mock_google_consent.html", next=next_page)

@app.route("/logout")

def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

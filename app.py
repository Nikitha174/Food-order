import os, json, sqlite3, hashlib, uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ── Config ────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "foodrush_secret_2024"
DB_PATH = "food_order.db"
UPLOAD_FOLDER = os.path.join("static", "images", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Sentiment ─────────────────────────────────────────────────────────────────
sia = SentimentIntensityAnalyzer()

# ── NLP Intent Classifier ─────────────────────────────────────────────────────
TRAINING_DATA = [
    ("I want something spicy", "spicy"), ("Give me hot food", "spicy"),
    ("I love chilli and pepper", "spicy"), ("spicy food please", "spicy"),
    ("something with a kick", "spicy"), ("fire hot food", "spicy"),
    ("I feel like something sweet", "sweet"), ("Give me desserts", "sweet"),
    ("I want cake or ice cream", "sweet"), ("sweet food options", "sweet"),
    ("chocolate dessert", "sweet"), ("something sugary", "sweet"),
    ("Show me cheap food", "cheap"), ("budget options please", "cheap"),
    ("affordable meals", "cheap"), ("low cost food", "cheap"),
    ("something under 100 rupees", "cheap"), ("economical food", "cheap"),
    ("Suggest healthy options", "healthy"), ("I want something light", "healthy"),
    ("nutritious food", "healthy"), ("low calorie meals", "healthy"),
    ("diet friendly food", "healthy"), ("salad or healthy food", "healthy"),
    ("I want vegetarian food", "veg"), ("show me veg options", "veg"),
    ("no meat please", "veg"), ("only vegetarian", "veg"), ("veg dishes", "veg"),
    ("I want chicken", "non-veg"), ("show me non-veg food", "non-veg"),
    ("meat dishes", "non-veg"), ("I love chicken and fish", "non-veg"),
    ("non vegetarian food", "non-veg"), ("burger with chicken", "non-veg"),
    ("show me spicy veg food", "spicy_veg"), ("I want spicy vegetarian", "spicy_veg"),
    ("hot veg dishes", "spicy_veg"), ("spicy plant-based food", "spicy_veg"),
    ("show me spicy non-veg food", "spicy_nonveg"), ("hot chicken dishes", "spicy_nonveg"),
    ("spicy meat food", "spicy_nonveg"), ("spicy chicken or fish", "spicy_nonveg"),
    ("I want to buy a mobile phone", "invalid"), ("show me some clothes", "invalid"),
    ("can I buy a car here", "invalid"), ("I need a laptop", "invalid"),
    ("shoes and watches", "invalid"), ("where are the electronics", "invalid"),
    ("book a flight ticket", "invalid"), ("I want to buy furniture", "invalid"),
    ("buy a house", "invalid"), ("order a smartphone", "invalid"),
    ("t-shirts and jeans", "invalid"), ("medicine or beauty products", "invalid"),
]
_texts, _labels = zip(*TRAINING_DATA)
_vec = TfidfVectorizer(ngram_range=(1, 2))
_X   = _vec.fit_transform(_texts)
_clf = LogisticRegression(max_iter=500)
_clf.fit(_X, _labels)

def classify_intent(text: str) -> str:
    return _clf.predict(_vec.transform([text]))[0]

# ── DB Helpers ────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def get_session_id():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]

def get_cart_count(sid):
    conn = get_db()
    n = conn.execute("SELECT SUM(quantity) FROM cart WHERE session_id=?", (sid,)).fetchone()[0]
    conn.close()
    return n or 0

def get_current_user():
    uid = session.get("user_id")
    if not uid: return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return user

def get_user_prefs(user_id):
    conn = get_db()
    pref = conn.execute("SELECT * FROM user_preferences WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return pref

def today_abbr():
    return datetime.now().strftime("%a")

def allowed_file(f):
    return "." in f and f.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ── DB Init ───────────────────────────────────────────────────────────────────
def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS user_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE NOT NULL,
        display_name TEXT, address TEXT, food_pref TEXT DEFAULT 'both',
        veg_days TEXT DEFAULT '', nonveg_days TEXT DEFAULT '',
        FOREIGN KEY(user_id) REFERENCES users(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS food_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        category TEXT NOT NULL, price REAL NOT NULL, rating REAL DEFAULT 4.0,
        description TEXT, image TEXT DEFAULT 'default.png',
        is_veg INTEGER DEFAULT 1, tags TEXT DEFAULT '', is_available INTEGER DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
        food_id INTEGER NOT NULL, quantity INTEGER DEFAULT 1,
        FOREIGN KEY(food_id) REFERENCES food_items(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
        items TEXT NOT NULL, total REAL NOT NULL, name TEXT, email TEXT,
        address TEXT, phone TEXT, status TEXT DEFAULT 'Confirmed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT, food_id INTEGER NOT NULL,
        reviewer_name TEXT DEFAULT 'Anonymous', review_text TEXT NOT NULL,
        sentiment TEXT, sentiment_score REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(food_id) REFERENCES food_items(id))""")

    if c.execute("SELECT COUNT(*) FROM food_items").fetchone()[0] == 0:
        seeds = [
            ("Margherita Pizza","Pizza",249,4.5,"Classic tomato and mozzarella pizza","margherita.png",1,"veg,mild,popular"),
            ("Spicy Paneer Pizza","Pizza",299,4.3,"Loaded with spicy paneer and bell peppers","paneer_pizza.png",1,"veg,spicy"),
            ("Chicken BBQ Pizza","Pizza",349,4.6,"Smoky BBQ chicken with caramelized onions","bbq_chicken_pizza.png",0,"non-veg,spicy,popular"),
            ("Veggie Supreme Pizza","Pizza",279,4.2,"Garden vegetables on a herbed base","veggie_pizza.png",1,"veg,healthy"),
            ("Classic Veg Burger","Burger",129,4.1,"Crispy veggie patty with fresh veggies","veg_burger.png",1,"veg,cheap"),
            ("Zinger Chicken Burger","Burger",179,4.7,"Fiery fried chicken with jalapeños","zinger_burger.png",0,"non-veg,spicy,popular,chicken"),
            ("Double Beef Smash Burger","Burger",229,4.5,"Double smash patty with special sauce","beef_burger.png",0,"non-veg,popular"),
            ("Mushroom Swiss Burger","Burger",159,4.0,"Juicy mushroom patty with Swiss cheese","mushroom_burger.png",1,"veg"),
            ("Hyderabadi Chicken Biryani","Biryani",199,4.8,"Authentic Hyderabadi dum biryani","chicken_biryani.png",0,"non-veg,spicy,popular,chicken,biryani"),
            ("Veg Biryani","Biryani",149,4.2,"Fragrant basmati with garden veggies","veg_biryani.png",1,"veg,healthy,biryani"),
            ("Mutton Biryani","Biryani",279,4.6,"Slow-cooked tender mutton biryani","mutton_biryani.png",0,"non-veg,spicy,biryani"),
            ("Egg Biryani","Biryani",169,4.3,"Flavourful biryani with boiled eggs","egg_biryani.png",0,"non-veg,biryani"),
            ("Gulab Jamun","Desserts",79,4.7,"Soft dumplings soaked in rose syrup","gulab_jamun.png",1,"veg,sweet"),
            ("Chocolate Lava Cake","Desserts",129,4.8,"Warm chocolate cake with molten center","lava_cake.png",1,"veg,sweet,popular"),
            ("Mango Kulfi","Desserts",99,4.5,"Traditional Indian mango ice cream","kulfi.png",1,"veg,sweet"),
            ("Rasgulla","Desserts",69,4.4,"Soft spongy balls in sugar syrup","rasgulla.png",1,"veg,sweet,cheap"),
            ("Mango Lassi","Drinks",89,4.6,"Thick creamy mango yoghurt drink","mango_lassi.png",1,"veg,sweet,healthy"),
            ("Cold Coffee","Drinks",99,4.4,"Chilled coffee with ice cream","cold_coffee.png",1,"veg,sweet"),
            ("Virgin Mojito","Drinks",79,4.3,"Refreshing mint lime mocktail","mojito.png",1,"veg,healthy,cheap"),
            ("Spicy Chaas","Drinks",49,4.1,"Spiced buttermilk drink","chaas.png",1,"veg,spicy,cheap,healthy"),
        ]
        c.executemany("INSERT INTO food_items (name,category,price,rating,description,image,is_veg,tags) VALUES(?,?,?,?,?,?,?,?)", seeds)
    conn.commit(); conn.close()

# ── PWA Routes ────────────────────────────────────────────────────────────────
@app.route("/sw.js")
def service_worker():
    """Serve the service worker from root scope so it can control all pages."""
    from flask import send_from_directory, make_response
    response = make_response(send_from_directory("static", "sw.js"))
    response.headers["Content-Type"] = "application/javascript"
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

# ── Context Processor ─────────────────────────────────────────────────────────
@app.context_processor
def inject_globals():
    return {"current_user": get_current_user(), "cart_count": get_cart_count(get_session_id())}

# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/register", methods=["GET","POST"])
def register():
    if session.get("user_id"): return redirect(url_for("index"))
    if request.method == "POST":
        name  = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        pw    = request.form.get("password","")
        pw2   = request.form.get("confirm_password","")
        food_pref   = request.form.get("food_pref","both")
        nonveg_days = ",".join(request.form.getlist("nonveg_days"))

        if not name or not email or not pw:
            flash("All fields are required.", "error")
            return render_template("register.html")
        if pw != pw2:
            flash("Passwords do not match.", "error")
            return render_template("register.html")
        if len(pw) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html")

        conn = get_db()
        if conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            conn.close()
            flash("Email already registered. Please login.", "error")
            return render_template("register.html")

        conn.execute("INSERT INTO users (name,email,password) VALUES(?,?,?)", (name, email, hash_pw(pw)))
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("""INSERT INTO user_preferences (user_id,display_name,address,food_pref,veg_days,nonveg_days)
                        VALUES(?,?,?,?,?,?)""", (uid, name, "", food_pref, "", nonveg_days))
        conn.commit(); conn.close()

        session["user_id"] = uid
        flash(f"Welcome to FoodRush, {name}! 🎉", "success")
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET","POST"])
def login():
    if session.get("user_id"): return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        pw    = request.form.get("password","")
        conn  = get_db()
        user  = conn.execute("SELECT * FROM users WHERE email=? AND password=?",
                             (email, hash_pw(pw))).fetchone()
        conn.close()
        if not user:
            flash("Invalid email or password.", "error")
            return render_template("login.html")
        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['name']}! 👋", "success")
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))

# ═══════════════════════════════════════════════════════════════════════════════
#  PROFILE / PREFERENCES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/profile", methods=["GET","POST"])
def profile():
    user = get_current_user()
    if not user:
        flash("Please login to access your profile.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        display_name = request.form.get("display_name","").strip()
        address      = request.form.get("address","").strip()
        food_pref    = request.form.get("food_pref","both")
        veg_days     = ",".join(request.form.getlist("veg_days"))
        nonveg_days  = ",".join(request.form.getlist("nonveg_days"))
        conn = get_db()
        existing = conn.execute("SELECT id FROM user_preferences WHERE user_id=?", (user["id"],)).fetchone()
        if existing:
            conn.execute("""UPDATE user_preferences
                SET display_name=?,address=?,food_pref=?,veg_days=?,nonveg_days=?
                WHERE user_id=?""", (display_name, address, food_pref, veg_days, nonveg_days, user["id"]))
        else:
            conn.execute("""INSERT INTO user_preferences(user_id,display_name,address,food_pref,veg_days,nonveg_days)
                VALUES(?,?,?,?,?,?)""", (user["id"], display_name, address, food_pref, veg_days, nonveg_days))
        conn.commit(); conn.close()
        flash("✅ Preferences saved!", "success")
        return redirect(url_for("profile"))

    pref = get_user_prefs(user["id"])
    veg_days_list    = [d for d in (pref["veg_days"].split(",")    if pref and pref["veg_days"]    else [])]
    nonveg_days_list = [d for d in (pref["nonveg_days"].split(",") if pref and pref["nonveg_days"] else [])]
    return render_template("profile.html", user=user, pref=pref,
                           veg_days_list=veg_days_list, nonveg_days_list=nonveg_days_list)

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN PAGES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    sid      = get_session_id()
    category = request.args.get("category", "All")
    search   = request.args.get("search", "")
    override = request.args.get("override", "")

    # Day-based preference filter
    day_filter_active, day_filter_label, day_filter_type, veg_filter_sql = False, "", "", None
    user = get_current_user()
    if user and not search and not override:
        pref = get_user_prefs(user["id"])
        if pref:
            today = today_abbr()
            vd  = [d.strip() for d in pref["veg_days"].split(",")    if d.strip()]
            nvd = [d.strip() for d in pref["nonveg_days"].split(",") if d.strip()]
            fp  = pref["food_pref"]
            if fp == "veg":
                veg_filter_sql, day_filter_active, day_filter_type = "is_veg=1", True, "veg"
                day_filter_label = "🌿 Showing Veg options (your preference)"
            elif fp == "non-veg":
                veg_filter_sql, day_filter_active, day_filter_type = "is_veg=0", True, "non-veg"
                day_filter_label = "🍗 Showing Non-Veg options (your preference)"
            elif fp == "both":
                if today in vd:
                    veg_filter_sql, day_filter_active, day_filter_type = "is_veg=1", True, "veg"
                    day_filter_label = f"🌿 Veg day today ({today})"
                elif today in nvd:
                    veg_filter_sql, day_filter_active, day_filter_type = "is_veg=0", True, "non-veg"
                    day_filter_label = f"🍗 Non-Veg day today ({today})"

    conn = get_db()
    if search:
        q = f"%{search}%"
        foods = conn.execute(
            "SELECT * FROM food_items WHERE is_available=1 AND (name LIKE ? OR tags LIKE ? OR category LIKE ?)",
            (q, q, q)).fetchall()
    elif category and category != "All":
        sql = "SELECT * FROM food_items WHERE category=? AND is_available=1"
        if veg_filter_sql: sql += f" AND {veg_filter_sql}"
        foods = conn.execute(sql, (category,)).fetchall()
    else:
        sql = "SELECT * FROM food_items WHERE is_available=1"
        if veg_filter_sql: sql += f" AND {veg_filter_sql}"
        foods = conn.execute(sql).fetchall()
    conn.close()

    return render_template("index.html", foods=foods, category=category, search=search,
                           day_filter_active=day_filter_active, day_filter_label=day_filter_label,
                           day_filter_type=day_filter_type)


@app.route("/search-suggestions")
def search_suggestions():
    q = request.args.get("q","").strip()
    if len(q) < 2: return jsonify([])
    conn = get_db()
    rows = conn.execute("""SELECT DISTINCT name FROM food_items
        WHERE is_available=1 AND (name LIKE ? OR tags LIKE ? OR category LIKE ?) LIMIT 8""",
        (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    conn.close()
    return jsonify([r["name"] for r in rows])


@app.route("/food/<int:food_id>")
def food_detail(food_id):
    conn  = get_db()
    food  = conn.execute("SELECT * FROM food_items WHERE id=?", (food_id,)).fetchone()
    reviews = conn.execute("SELECT * FROM reviews WHERE food_id=? ORDER BY created_at DESC", (food_id,)).fetchall()
    conn.close()
    if not food: return redirect(url_for("index"))
    return render_template("food_detail.html", food=food, reviews=reviews)


@app.route("/submit-review", methods=["POST"])
def submit_review():
    data    = request.get_json()
    food_id = data.get("food_id")
    name    = data.get("name","Anonymous")
    text    = data.get("text","")
    if not text: return jsonify({"error":"Empty"}), 400
    sc = sia.polarity_scores(text)["compound"]
    sentiment = "Positive" if sc >= 0.05 else ("Negative" if sc <= -0.05 else "Neutral")
    conn = get_db()
    conn.execute("INSERT INTO reviews(food_id,reviewer_name,review_text,sentiment,sentiment_score) VALUES(?,?,?,?,?)",
                 (food_id, name, text, sentiment, sc))
    conn.commit(); conn.close()
    return jsonify({"sentiment": sentiment, "score": round(sc,3)})

# ═══════════════════════════════════════════════════════════════════════════════
#  CART & ORDERS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/add-to-cart", methods=["POST"])
def add_to_cart():
    sid     = get_session_id()
    food_id = request.get_json().get("food_id")
    conn    = get_db()
    existing = conn.execute("SELECT id,quantity FROM cart WHERE session_id=? AND food_id=?", (sid, food_id)).fetchone()
    if existing:
        conn.execute("UPDATE cart SET quantity=quantity+1 WHERE id=?", (existing["id"],))
    else:
        conn.execute("INSERT INTO cart(session_id,food_id,quantity) VALUES(?,?,1)", (sid, food_id))
    conn.commit()
    count = conn.execute("SELECT SUM(quantity) FROM cart WHERE session_id=?", (sid,)).fetchone()[0] or 0
    conn.close()
    return jsonify({"success": True, "cart_count": int(count)})


@app.route("/cart")
def cart():
    sid   = get_session_id()
    conn  = get_db()
    items = conn.execute("""SELECT c.id as cart_id, c.quantity,
        f.id as food_id, f.name, f.price, f.image, f.category
        FROM cart c JOIN food_items f ON c.food_id=f.id WHERE c.session_id=?""", (sid,)).fetchall()
    total = sum(i["price"] * i["quantity"] for i in items)
    conn.close()
    return render_template("cart.html", items=items, total=total)


@app.route("/update-cart", methods=["POST"])
def update_cart():
    sid     = get_session_id()
    data    = request.get_json()
    cart_id = data.get("cart_id")
    action  = data.get("action")
    conn    = get_db()
    item    = conn.execute("SELECT * FROM cart WHERE id=? AND session_id=?", (cart_id, sid)).fetchone()
    if item:
        if action == "inc":
            conn.execute("UPDATE cart SET quantity=quantity+1 WHERE id=?", (cart_id,))
        elif action == "dec":
            if item["quantity"] > 1:
                conn.execute("UPDATE cart SET quantity=quantity-1 WHERE id=?", (cart_id,))
            else:
                conn.execute("DELETE FROM cart WHERE id=?", (cart_id,))
        elif action == "del":
            conn.execute("DELETE FROM cart WHERE id=?", (cart_id,))
    conn.commit()
    items = conn.execute("SELECT c.quantity, f.price FROM cart c JOIN food_items f ON c.food_id=f.id WHERE c.session_id=?", (sid,)).fetchall()
    total = sum(i["price"]*i["quantity"] for i in items)
    count = sum(i["quantity"] for i in items)
    conn.close()
    return jsonify({"success": True, "total": round(total, 2), "cart_count": count})


@app.route("/checkout")
def checkout():
    sid   = get_session_id()
    conn  = get_db()
    items = conn.execute("""SELECT c.id as cart_id, c.quantity,
        f.id as food_id, f.name, f.price, f.image
        FROM cart c JOIN food_items f ON c.food_id=f.id WHERE c.session_id=?""", (sid,)).fetchall()
    total = sum(i["price"]*i["quantity"] for i in items)
    conn.close()
    if not items: return redirect(url_for("cart"))
    # Pre-fill from user profile if logged in
    user = get_current_user()
    pref = get_user_prefs(user["id"]) if user else None
    return render_template("checkout.html", items=items, total=total, user=user, pref=pref)


@app.route("/place-order", methods=["POST"])
def place_order():
    sid  = get_session_id()
    data = request.get_json()
    conn = get_db()
    items = conn.execute("""SELECT c.quantity, f.id, f.name, f.price
        FROM cart c JOIN food_items f ON c.food_id=f.id WHERE c.session_id=?""", (sid,)).fetchall()
    if not items:
        conn.close()
        return jsonify({"error": "Cart is empty"}), 400
    total      = sum(i["price"] * i["quantity"] for i in items)
    items_json = json.dumps([{"name": i["name"], "qty": i["quantity"], "price": i["price"]} for i in items])
    conn.execute("INSERT INTO orders(session_id,items,total,name,email,address,phone) VALUES(?,?,?,?,?,?,?)",
                 (sid, items_json, total, data.get("name"), data.get("email"), data.get("address"), data.get("phone")))
    conn.execute("DELETE FROM cart WHERE session_id=?", (sid,))
    conn.commit()
    order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return jsonify({"success": True, "order_id": order_id})


@app.route("/order-success/<int:order_id>")
def order_success(order_id):
    sid  = get_session_id()
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=? AND session_id=?", (order_id, sid)).fetchone()
    conn.close()
    if not order: return redirect(url_for("index"))
    return render_template("order_success.html", order=order, items=json.loads(order["items"]))


@app.route("/orders")
def orders():
    sid  = get_session_id()
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders WHERE session_id=? ORDER BY created_at DESC", (sid,)).fetchall()
    all_orders = []
    for o in rows:
        d = dict(o)
        d["items"] = json.loads(d["items"])
        all_orders.append(d)
    recs = conn.execute("SELECT * FROM food_items WHERE is_available=1 ORDER BY rating DESC LIMIT 6").fetchall()
    conn.close()
    return render_template("orders.html", order_history=all_orders, recommendations=recs)

# ═══════════════════════════════════════════════════════════════════════════════
#  CHATBOT
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/chatbot", methods=["POST"])
def chatbot():
    msg = (request.get_json() or {}).get("message","").strip()
    if not msg:
        return jsonify({"reply":"Please type a message!", "foods":[]})

    conn = get_db()

    # Step 1: Try to find food items by name keywords first (exact match priority)
    words = [w for w in msg.lower().split() if len(w) > 2]
    name_foods = []
    if words:
        placeholders = " OR ".join(["name LIKE ?" for _ in words])
        params = [f"%{w}%" for w in words]
        name_foods = conn.execute(
            f"SELECT * FROM food_items WHERE is_available=1 AND ({placeholders}) ORDER BY rating DESC LIMIT 4",
            params).fetchall()

    # Step 2: Use intent classifier as fallback
    intent = classify_intent(msg)

    if intent == "invalid":
        conn.close()
        return jsonify({"reply":"🚫 Invalid item! I only know about food. Try asking for biryani, pizza, or burgers! 🍔", "intent":"invalid", "foods":[]})

    foods = name_foods  # Use name matches if found

    if not foods:
        intent_sql = {
            "spicy":        "tags LIKE '%spicy%'",
            "sweet":        "tags LIKE '%sweet%'",
            "cheap":        "price < 120",
            "healthy":      "tags LIKE '%healthy%'",
            "veg":          "is_veg=1",
            "non-veg":      "is_veg=0",
            "spicy_veg":    "is_veg=1 AND tags LIKE '%spicy%'",
            "spicy_nonveg": "is_veg=0 AND tags LIKE '%spicy%'",
        }.get(intent, "1=1")
        foods = conn.execute(
            f"SELECT * FROM food_items WHERE is_available=1 AND ({intent_sql}) ORDER BY rating DESC LIMIT 4"
        ).fetchall()
    conn.close()

    replies = {
        "spicy":        "🌶️ Here are some fiery picks for you!",
        "sweet":        "🍰 Something sweet coming right up!",
        "cheap":        "💸 Great budget-friendly options:",
        "healthy":      "🥗 Here are some healthy choices:",
        "veg":          "🌿 Delicious vegetarian options:",
        "non-veg":      "🍗 Non-veg lovers, this one's for you:",
        "spicy_veg":    "🌶️🌿 Spicy veg dishes — just for you!",
        "spicy_nonveg": "🌶️🍗 Spicy non-veg dishes — hot stuff!",
    }

    if name_foods:
        reply = f"🍽️ Here's what I found for '{msg}':"
    else:
        reply = replies.get(intent, "Here are some recommendations:")

    food_list = [{"id":f["id"],"name":f["name"],"price":f["price"],
                  "rating":f["rating"],"image":f["image"],"category":f["category"]} for f in foods]
    return jsonify({"reply": reply, "intent": intent, "foods": food_list})

# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

ADMIN_PASSWORD = "admin123"

@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") != ADMIN_PASSWORD:
            flash("❌ Wrong password!", "error")
            return render_template("admin_login.html")
        session["admin"] = True
        return redirect(url_for("admin_panel"))
    if session.get("admin"): return redirect(url_for("admin_panel"))
    return render_template("admin_login.html")


@app.route("/admin/panel")
def admin_panel():
    if not session.get("admin"): return redirect(url_for("admin"))
    conn  = get_db()
    foods = conn.execute("SELECT * FROM food_items ORDER BY category, name").fetchall()
    conn.close()
    return render_template("admin.html", foods=foods)


@app.route("/admin/add", methods=["POST"])
def admin_add():
    if not session.get("admin"): return redirect(url_for("admin"))
    name        = request.form["name"]
    category    = request.form["category"]
    price       = float(request.form["price"])
    rating      = float(request.form.get("rating", 4.0))
    description = request.form.get("description","")
    is_veg      = int(request.form.get("is_veg", 1))
    tags        = request.form.get("tags","")
    image       = "default.png"
    if "image" in request.files:
        f = request.files["image"]
        if f and allowed_file(f.filename):
            fn = secure_filename(f.filename)
            f.save(os.path.join(app.config["UPLOAD_FOLDER"], fn))
            image = "uploads/" + fn
    conn = get_db()
    conn.execute("INSERT INTO food_items(name,category,price,rating,description,image,is_veg,tags) VALUES(?,?,?,?,?,?,?,?)",
                 (name, category, price, rating, description, image, is_veg, tags))
    conn.commit(); conn.close()
    flash("✅ Food item added!", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/delete/<int:food_id>", methods=["POST"])
def admin_delete(food_id):
    if not session.get("admin"): return redirect(url_for("admin"))
    conn = get_db()
    conn.execute("DELETE FROM food_items WHERE id=?", (food_id,))
    conn.commit(); conn.close()
    flash("🗑️ Item deleted.", "info")
    return redirect(url_for("admin_panel"))


@app.route("/admin/edit/<int:food_id>", methods=["POST"])
def admin_edit(food_id):
    if not session.get("admin"): return redirect(url_for("admin"))
    conn = get_db()
    conn.execute("""UPDATE food_items SET name=?,price=?,description=?,tags=?,is_available=? WHERE id=?""",
                 (request.form["name"], float(request.form["price"]),
                  request.form.get("description",""), request.form.get("tags",""),
                  int(request.form.get("is_available",1)), food_id))
    conn.commit(); conn.close()
    flash("✏️ Item updated!", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)

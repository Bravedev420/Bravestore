
from flask import Flask, render_template, g, abort, session, request, redirect, url_for, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config["SECRET_KEY"] = "supersecretkey"

DATABASE = "store.db"
EXCHANGE_RATE = 510

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


# ------------------------------
# Database Connection
# ------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ------------------------------
# Initialize Database
# ------------------------------
def init_db():
    with sqlite3.connect(DATABASE) as conn:

        # PRODUCTS TABLE
        conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT NOT NULL,
            image TEXT NOT NULL
        )
        """)

        # USERS TABLE
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
        """)

        # ORDERS TABLE (Main order information)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            customer_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            total_price REAL,
            payment_method TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)

        # ORDER ITEMS TABLE (Products inside an order)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            price REAL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
        """)

        # CONTACT MESSAGES

        conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

# ------------------------------
# Seed Products
# ------------------------------
def seed_products():
    with sqlite3.connect(DATABASE) as conn:
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            products = [
                ("Wireless Headphones", 20, "Noise cancellation, 20h battery.", "headphones.jpg"),
                ("Smart Watch", 80, "Fitness tracking and notifications.", "smartwatch.jpg"),
                ("Bluetooth Speaker", 7, "Portable with deep bass sound.", "bluethoothspeaker.jpg"),
                ("Home Fridge", 250, "Great space to store food items.", "fridge.jpg"),
                ("Micro-wave", 170, "Cook fast delicious meals conveniently.", "micro-wave.jpg"),
                ("Laundry Machine", 180, "Wash your clothes in no time.", "laundry.jpg"),
            ]
            conn.executemany("""
            INSERT INTO products (name, price, description, image)
            VALUES (?, ?, ?, ?)
            """, products)


# ------------------------------
# Auth Helpers
# ------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or not session.get("is_admin"):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ------------------------------
# Context Processor (cart count)
# ------------------------------
@app.context_processor
def inject_cart_count():
    cart = session.get("cart", {})
    count = sum(cart.values()) if isinstance(cart, dict) else 0
    return dict(cart_count=count)


# ------------------------------
# Routes
# ------------------------------
@app.route("/")
def home():
    db = get_db()
    rows = db.execute("SELECT * FROM products LIMIT 6").fetchall()
    products = []
    for row in rows:
        p = dict(row)
        p["price_fcfa"] = int(p["price"] * EXCHANGE_RATE)
        products.append(p)
    return render_template("index.html", products=products)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")
        db = get_db()
        db.execute("INSERT INTO messages (name, email, message) VALUES (?, ?, ?)",
                   (name, email, message))
        db.commit()
        flash("Message sent successfully! We'll be in touch.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")


# ------------------------------
# Product List
# ------------------------------
@app.route("/product")
def products():
    db = get_db()
    rows = db.execute("SELECT * FROM products").fetchall()
    products = []
    for row in rows:
        p = dict(row)
        p["price_fcfa"] = int(p["price"] * EXCHANGE_RATE)
        products.append(p)
    return render_template("products.html", products=products)


# ------------------------------
# Individual Product
# ------------------------------
@app.route("/product/<int:product_id>")
def product_page(product_id):
    db = get_db()
    item = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if item is None:
        abort(404)
    product = dict(item)
    product["price_fcfa"] = int(product["price"] * EXCHANGE_RATE)
    return render_template("indivproducts.html", item=product)


# ------------------------------
# Cart
# ------------------------------
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    cart = session.get("cart", {})
    key = str(product_id)
    cart[key] = cart.get(key, 0) + 1
    session["cart"] = cart
    session.modified = True
    flash("Item added to cart!", "success")
    return redirect(url_for("cart"))


@app.route("/cart")
def cart():
    db = get_db()
    cart_items = []
    total = 0
    cart = session.get("cart", {})
    if not isinstance(cart, dict):
        cart = {}
        session["cart"] = cart

    for product_id, quantity in cart.items():
        product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if product:
            p = dict(product)
            p["price_fcfa"] = int(p["price"] * EXCHANGE_RATE)
            p["quantity"] = quantity
            p["subtotal"] = p["price_fcfa"] * quantity
            total += p["subtotal"]
            cart_items.append(p)

    return render_template("cart.html", cart_items=cart_items, total=total)


@app.route("/increase/<int:product_id>")
def increase(product_id):
    cart = session.get("cart", {})
    key = str(product_id)
    cart[key] = cart.get(key, 0) + 1
    session["cart"] = cart
    return redirect(url_for("cart"))


@app.route("/decrease/<int:product_id>")
def decrease(product_id):
    cart = session.get("cart", {})
    key = str(product_id)
    if key in cart:
        cart[key] -= 1
        if cart[key] <= 0:
            del cart[key]
    session["cart"] = cart
    return redirect(url_for("cart"))


@app.route("/remove/<int:product_id>")
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    key = str(product_id)
    if key in cart:
        del cart[key]
    session["cart"] = cart
    return redirect(url_for("cart"))


# ------------------------------
# Checkout (cart-based)
# ------------------------------
@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    db = get_db()
    cart = session.get("cart", {})

    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart"))

    cart_items = []
    total = 0
    for product_id, quantity in cart.items():
        product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if product:
            p = dict(product)
            p["price_fcfa"] = int(p["price"] * EXCHANGE_RATE)
            p["quantity"] = quantity
            p["subtotal"] = p["price_fcfa"] * quantity
            total += p["subtotal"]
            cart_items.append(p)

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        payment_method = request.form.get("payment_method")
        user_id = session.get("user_id")

        # Create the main order
        cursor = db.execute("""
            INSERT INTO orders (user_id, customer_name, email, phone, total_price, payment_method)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, name, email, phone, total, payment_method))
        order_id = cursor.lastrowid

        # Insert each product into order_items
        for item in cart_items:
            db.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
            """, (order_id, item["id"], item["quantity"], item["price"]))

        db.commit()

        # Clear cart
        session["cart"] = {}
        session.modified = True

        return render_template("success.html", name=name, total=total)

    return render_template("checkout.html", cart_items=cart_items, total=total)
# ------------------------------
# Auth
# ------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        hashed = generate_password_hash(password, method='pbkdf2:sha256')
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                       (username, email, hashed))
            db.commit()
            flash("Account created! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["is_admin"] = bool(user["is_admin"])
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "info")
    return redirect(url_for("home"))


# ------------------------------
# Admin Dashboard
# ------------------------------
@app.route("/admin_dashboard")
@admin_required
def admin_dashboard():
    db = get_db()
    products = db.execute("SELECT * FROM products").fetchall()
    orders = db.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    users = db.execute("SELECT id, username, email, is_admin FROM users").fetchall()
    messages = db.execute("SELECT * FROM messages ORDER BY created_at DESC").fetchall()
    total_revenue = db.execute("SELECT SUM(total_price) FROM orders").fetchone()[0] or 0

    recent_orders = db.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 5").fetchall()
    recent_messages = db.execute("SELECT * FROM messages ORDER BY created_at DESC LIMIT 5").fetchall()
    recent_signups = db.execute("SELECT id, username, email, is_admin FROM users ORDER BY id DESC LIMIT 5").fetchall()

    pending_orders   = db.execute("SELECT * FROM orders WHERE status = 'Pending'  ORDER BY created_at DESC").fetchall()
    paid_orders      = db.execute("SELECT * FROM orders WHERE status = 'Paid'     ORDER BY created_at DESC").fetchall()
    shipped_orders   = db.execute("SELECT * FROM orders WHERE status = 'Shipped'  ORDER BY created_at DESC").fetchall()
    delivered_orders = db.execute("SELECT * FROM orders WHERE status = 'Delivered' ORDER BY created_at DESC").fetchall()

    return render_template("admin.html",
                           products=products,
                           orders=orders,
                           users=users,
                           messages=messages,
                           total_revenue=int(total_revenue),
                           recent_orders=recent_orders,
                           recent_messages=recent_messages,
                           recent_signups=recent_signups,
                           pending_orders=pending_orders,
                           paid_orders=paid_orders,
                           shipped_orders=shipped_orders,
                           delivered_orders=delivered_orders)


@app.route("/admin/delete_product/<int:product_id>", methods=["POST"])
@admin_required
def delete_product(product_id):
    db = get_db()
    db.execute("DELETE FROM products WHERE id=?", (product_id,))
    db.commit()
    flash("Product deleted.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/update_order_status/<int:order_id>", methods=["POST"])
@admin_required
def update_order_status(order_id):
    status = request.form.get("status")
    db = get_db()
    db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    db.commit()
    flash(f"Order #{order_id} status updated to {status}.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/add_product", methods=["POST"])
@admin_required
def add_product():
    name = request.form.get("name")
    price = float(request.form.get("price"))
    description = request.form.get("description")
    image = request.form.get("image")
    db = get_db()
    db.execute("INSERT INTO products (name, price, description, image) VALUES (?, ?, ?, ?)",
               (name, price, description, image))
    db.commit()
    flash("Product added!", "success")
    return redirect(url_for("admin_dashboard"))


# ------------------------------
# Error Pages
# ------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403

# Initialize database on startup
with app.app_context():
    init_db()
    seed_products()

# ------------------------------
# Run App
# ------------------------------
if __name__ == "__main__":
    init_db()
    seed_products()
    app.run(host="0.0.0.0", port=5000, debug=True)
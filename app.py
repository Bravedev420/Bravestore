from flask import Flask, render_template

app = Flask(__name__)

# ---- PRODUCT DATA (temporary database) ----
products = [
    {
        "name": "Wireless Headphones",
        "price": "49 CFA",
        "description": "Noise cancellation, 20h battery.",
        "image": "headphones.jpg",
        "link": "#"
    },
    {
        "name": "Smart Watch",
        "price": "89.99 CFA",
        "description": "Fitness tracking and notifications.",
        "image": "smartwatch.jpg",
        "link": "#"
    },
    {
        "name": "Bluethooth Speaker",
        "price": "39.99 CFA",
        "description": "Portable with deep bass sound.",
        "image": "bluethoothspeaker.jpg",  # fixed spelling
        "link": "#"
    }
]

# ---- HOME PAGE ----
@app.route("/")
def home():
    # ✅ MUST pass products to index.html
    return render_template("index.html", products=products)

# ---- PRODUCT PAGE (Customer View) ----
@app.route("/product")
def product():
    return render_template("product.html", products=products)

# ---- ABOUT PAGE ----
@app.route("/about")
def about():
    return render_template("about.html")

# ---- CONTACT PAGE ----
@app.route("/contact")
def contact():
    return render_template("contact.html")

# ---- DASHBOARD PAGE (Admin View) ----
@app.route("/dashboard")
def dashboard():
    total_products = len(products)
    return render_template(
        "dashboard.html",
        products=products,
        total=total_products
    )

# ---- RUN SERVER ----
if __name__ == "__main__":
    app.run(debug=True)
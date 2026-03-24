# 🍔 FoodRush — Smart Food Ordering Website

A fully functional, professional food ordering platform built with **Flask**, **SQLite**, and **NLP** (TF-IDF + Logistic Regression & VADER Sentiment Analysis).

---

## 🚀 Features

| Feature | Details |
|---|---|
| **Modern UI** | Swiggy/Zomato-style responsive design |
| **AI Chatbot** | TF-IDF + Logistic Regression intent classifier |
| **Sentiment Analysis** | VADER-powered review sentiment badges |
| **Smart Search** | NLP keyword-based auto-suggestions |
| **Cart & Checkout** | Full cart flow with AJAX updates |
| **Admin Panel** | Add / Edit / Delete food items with image upload |
| **Order History** | Previous orders + recommendation engine |

---

## 🛠️ Setup Instructions

### 1. Clone / Open the project

```bash
cd "nlp 2.0"
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
python app.py
```

### 5. Open in browser

```
http://127.0.0.1:5000
```

---

## 🗂️ Project Structure

```
nlp 2.0/
├── app.py                   # Flask backend (routes, NLP, DB)
├── food_order.db            # SQLite database (auto-created)
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html            # Shared layout, navbar, chatbot
│   ├── index.html           # Landing page
│   ├── cart.html            # Shopping cart
│   ├── checkout.html        # Checkout form
│   ├── food_detail.html     # Food detail + reviews
│   ├── orders.html          # Order history + recommendations
│   ├── order_success.html   # Order confirmation
│   ├── admin.html           # Admin panel
│   └── admin_login.html     # Admin login
└── static/
    ├── css/style.css        # Full stylesheet
    ├── js/main.js           # Chatbot, cart, search UI logic
    └── images/              # Food images & uploads
```

---

## 🗄️ Database Tables

| Table | Purpose |
|---|---|
| `food_items` | Menu items (name, price, category, tags, etc.) |
| `cart` | Session-based cart items |
| `orders` | Placed orders |
| `reviews` | Food reviews with sentiment scores |
| `users` | (Reserved for future user auth) |

---

## 🤖 NLP Features

### 1. Intent Classifier — TF-IDF + Logistic Regression
The chatbot classifies user messages into 6 intents:
- **spicy** → "I want something hot and spicy"
- **sweet** → "Show me desserts"
- **cheap** → "Budget options under ₹100"
- **healthy** → "Low calorie food"
- **veg** → "Vegetarian options"
- **non-veg** → "Chicken or meat dishes"

### 2. VADER Sentiment Analysis
Every review is automatically analyzed:
- Score ≥ 0.05 → 😊 **Positive**
- Score ≤ −0.05 → 😞 **Negative**
- Otherwise → 😐 **Neutral**

---

## 🔑 Admin Panel

- **URL:** `http://127.0.0.1:5000/admin`
- **Password:** `admin123`

Allows you to: Add items with image upload · Edit name/price/description · Delete items · Toggle availability.

---

## 📦 Requirements

```
Flask==2.3.3
scikit-learn==1.3.2
vaderSentiment==3.3.2
Pillow==10.1.0
Werkzeug==2.3.7
numpy==1.26.2
```

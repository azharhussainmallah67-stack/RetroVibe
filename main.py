from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json, os, uuid, shutil
from datetime import datetime

app = FastAPI(title="MyStore")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_FILE = "database/store.json"
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ─── DATABASE ────────────────────────────────────────────
def load_db():
    if not os.path.exists(DB_FILE):
        default = {
            "products": [
                {"id":"1","name":"Premium Wireless Headphones","price":2500,"original_price":3500,
                 "category":"Electronics","description":"Experience crystal-clear audio with deep bass and active noise cancellation. Perfect for music lovers and professionals alike. Up to 30 hours battery life with fast charging support.",
                 "stock":50,"images":["https://placehold.co/800x600/0f172a/38bdf8?text=Headphones+Front","https://placehold.co/800x600/1e1b4b/38bdf8?text=Headphones+Side"],
                 "tags":["wireless","audio","noise-cancellation"],"featured":True,"created_at":str(datetime.now())},
                {"id":"2","name":"Genuine Leather Wallet","price":1800,"original_price":2500,
                 "category":"Accessories","description":"Handcrafted from full-grain leather, this slim bifold wallet features 6 card slots, a bill compartment, and RFID blocking technology to keep your cards safe.",
                 "stock":100,"images":["https://placehold.co/800x600/0f172a/f59e0b?text=Wallet+Front","https://placehold.co/800x600/1a1a00/f59e0b?text=Wallet+Open"],
                 "tags":["leather","rfid","slim"],"featured":True,"created_at":str(datetime.now())},
                {"id":"3","name":"Pro Running Shoes","price":4500,"original_price":5999,
                 "category":"Footwear","description":"Engineered for performance, these lightweight running shoes feature responsive cushioning, breathable mesh upper, and durable rubber outsole for maximum grip on any surface.",
                 "stock":30,"images":["https://placehold.co/800x600/0f172a/10b981?text=Shoes+Side","https://placehold.co/800x600/022c22/10b981?text=Shoes+Bottom"],
                 "tags":["running","sports","lightweight"],"featured":False,"created_at":str(datetime.now())},
                {"id":"4","name":"Smart Watch Series X","price":8999,"original_price":12000,
                 "category":"Electronics","description":"Stay connected and track your fitness with this advanced smartwatch. Features heart rate monitoring, GPS, sleep tracking, and 50+ workout modes. Water resistant up to 50 meters.",
                 "stock":15,"images":["https://placehold.co/800x600/0f172a/a855f7?text=Watch+Face","https://placehold.co/800x600/1a0030/a855f7?text=Watch+Side"],
                 "tags":["smartwatch","fitness","gps"],"featured":True,"created_at":str(datetime.now())}
            ],
            "orders": [],
            "reviews": [],
            "settings": {
                "store_name":"MyStore","currency":"PKR","admin_password":"admin123",
                "store_tagline":"Shop the Best, Pay Less",
                "whatsapp":"+92 300 0000000","email":"info@mystore.com",
                "address":"Karachi, Pakistan","free_shipping_above":3000,
                "announcement":"🎉 Free shipping on orders above PKR 3,000!"
            }
        }
        save_db(default)
        return default
    with open(DB_FILE) as f:
        return json.load(f)

def save_db(data):
    os.makedirs("database", exist_ok=True)
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_product(db, pid):
    return next((p for p in db["products"] if p["id"] == pid), None)

def is_admin(request: Request):
    return request.cookies.get("admin_ok") == "yes"

# ─── STORE ROUTES ─────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, category: str = None, search: str = None, sort: str = None):
    db = load_db()
    products = db["products"]
    if category:
        products = [p for p in products if p["category"].lower() == category.lower()]
    if search:
        products = [p for p in products if search.lower() in p["name"].lower() or search.lower() in p.get("description","").lower()]
    if sort == "price_asc":
        products = sorted(products, key=lambda x: x["price"])
    elif sort == "price_desc":
        products = sorted(products, key=lambda x: x["price"], reverse=True)
    elif sort == "newest":
        products = sorted(products, key=lambda x: x.get("created_at",""), reverse=True)

    # Attach avg rating
    reviews = db.get("reviews", [])
    for p in products:
        pv = [r for r in reviews if r["product_id"] == p["id"]]
        p["avg_rating"] = round(sum(r["rating"] for r in pv) / len(pv), 1) if pv else 0
        p["review_count"] = len(pv)

    categories = list(set(p["category"] for p in db["products"]))
    featured = [p for p in db["products"] if p.get("featured")]
    for p in featured:
        pv = [r for r in reviews if r["product_id"] == p["id"]]
        p["avg_rating"] = round(sum(r["rating"] for r in pv) / len(pv), 1) if pv else 0
        p["review_count"] = len(pv)

    return templates.TemplateResponse("index.html", {
        "request": request, "products": products, "featured": featured,
        "categories": categories, "settings": db["settings"],
        "selected_category": category, "search": search, "sort": sort
    })

@app.get("/product/{pid}", response_class=HTMLResponse)
async def product_detail(request: Request, pid: str):
    db = load_db()
    product = get_product(db, pid)
    if not product:
        raise HTTPException(404)
    reviews = [r for r in db.get("reviews",[]) if r["product_id"] == pid]
    avg_rating = round(sum(r["rating"] for r in reviews) / len(reviews), 1) if reviews else 0
    # related products
    related = [p for p in db["products"] if p["category"] == product["category"] and p["id"] != pid][:3]
    return templates.TemplateResponse("product_detail.html", {
        "request": request, "product": product, "settings": db["settings"],
        "reviews": reviews, "avg_rating": avg_rating, "related": related
    })

# ─── CART (session via cookie-based JSON) ─────────────────

@app.get("/cart", response_class=HTMLResponse)
async def view_cart(request: Request):
    db = load_db()
    cart = _get_cart(request)
    cart_items = []
    total = 0
    for pid, qty in cart.items():
        p = get_product(db, pid)
        if p:
            subtotal = p["price"] * qty
            total += subtotal
            cart_items.append({**p, "qty": qty, "subtotal": subtotal})
    settings = db["settings"]
    shipping = 0 if total >= settings.get("free_shipping_above", 3000) else 250
    return templates.TemplateResponse("cart.html", {
        "request": request, "cart_items": cart_items,
        "total": total, "shipping": shipping,
        "grand_total": total + shipping, "settings": settings
    })

@app.post("/cart/add")
async def add_to_cart(request: Request, product_id: str = Form(...), quantity: int = Form(1)):
    cart = _get_cart(request)
    cart[product_id] = cart.get(product_id, 0) + quantity
    response = RedirectResponse("/cart", 302)
    response.set_cookie("cart", json.dumps(cart), max_age=86400*7)
    return response

@app.post("/cart/update")
async def update_cart(request: Request, product_id: str = Form(...), quantity: int = Form(...)):
    cart = _get_cart(request)
    if quantity <= 0:
        cart.pop(product_id, None)
    else:
        cart[product_id] = quantity
    response = RedirectResponse("/cart", 302)
    response.set_cookie("cart", json.dumps(cart), max_age=86400*7)
    return response

@app.post("/cart/remove")
async def remove_from_cart(request: Request, product_id: str = Form(...)):
    cart = _get_cart(request)
    cart.pop(product_id, None)
    response = RedirectResponse("/cart", 302)
    response.set_cookie("cart", json.dumps(cart), max_age=86400*7)
    return response

def _get_cart(request: Request):
    try:
        return json.loads(request.cookies.get("cart", "{}"))
    except:
        return {}

# ─── CHECKOUT & ORDER ─────────────────────────────────────

@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    db = load_db()
    cart = _get_cart(request)
    if not cart:
        return RedirectResponse("/cart", 302)
    cart_items = []
    total = 0
    for pid, qty in cart.items():
        p = get_product(db, pid)
        if p:
            subtotal = p["price"] * qty
            total += subtotal
            cart_items.append({**p, "qty": qty, "subtotal": subtotal})
    settings = db["settings"]
    shipping = 0 if total >= settings.get("free_shipping_above", 3000) else 250
    return templates.TemplateResponse("checkout.html", {
        "request": request, "cart_items": cart_items,
        "total": total, "shipping": shipping,
        "grand_total": total + shipping, "settings": settings
    })

@app.post("/checkout", response_class=HTMLResponse)
async def place_order(request: Request,
    customer_name: str = Form(...), customer_phone: str = Form(...),
    customer_email: str = Form(""), customer_address: str = Form(...),
    customer_city: str = Form(...), customer_notes: str = Form("")):
    db = load_db()
    cart = _get_cart(request)
    if not cart:
        return RedirectResponse("/cart", 302)

    cart_items = []
    total = 0
    for pid, qty in cart.items():
        p = get_product(db, pid)
        if p and p["stock"] >= qty:
            subtotal = p["price"] * qty
            total += subtotal
            cart_items.append({"product_id": pid, "product_name": p["name"],
                                "price": p["price"], "quantity": qty, "subtotal": subtotal})
            for prod in db["products"]:
                if prod["id"] == pid:
                    prod["stock"] -= qty

    settings = db["settings"]
    shipping = 0 if total >= settings.get("free_shipping_above", 3000) else 250
    grand_total = total + shipping

    order = {
        "id": str(uuid.uuid4())[:8].upper(),
        "items": cart_items,
        "total": total, "shipping": shipping, "grand_total": grand_total,
        "customer_name": customer_name, "customer_phone": customer_phone,
        "customer_email": customer_email,
        "customer_address": customer_address,
        "customer_city": customer_city,
        "customer_notes": customer_notes,
        "status": "pending",
        "created_at": datetime.now().strftime("%d %b %Y, %I:%M %p")
    }
    db["orders"].append(order)
    save_db(db)

    response = templates.TemplateResponse("order_success.html", {
        "request": request, "order": order, "settings": settings
    })
    response.delete_cookie("cart")
    return response

# ─── ORDER TRACKING ───────────────────────────────────────

@app.get("/track", response_class=HTMLResponse)
async def track_page(request: Request, order_id: str = None):
    db = load_db()
    order = None
    if order_id:
        order = next((o for o in db["orders"] if o["id"] == order_id.upper().strip()), None)
    return templates.TemplateResponse("track_order.html", {
        "request": request, "order": order,
        "order_id": order_id, "settings": db["settings"]
    })

# ─── REVIEWS ──────────────────────────────────────────────

@app.post("/product/{pid}/review")
async def add_review(request: Request, pid: str,
    reviewer_name: str = Form(...), rating: int = Form(...),
    comment: str = Form(...)):
    db = load_db()
    if not get_product(db, pid):
        raise HTTPException(404)
    review = {
        "id": str(uuid.uuid4())[:8],
        "product_id": pid,
        "reviewer_name": reviewer_name,
        "rating": max(1, min(5, rating)),
        "comment": comment,
        "created_at": datetime.now().strftime("%d %b %Y")
    }
    db["reviews"].append(review)
    save_db(db)
    return RedirectResponse(f"/product/{pid}#reviews", 302)

# ─── ADMIN ────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    db = load_db()
    return templates.TemplateResponse("admin_login.html", {"request": request, "settings": db["settings"]})

@app.post("/admin/login")
async def admin_login(password: str = Form(...)):
    db = load_db()
    if password == db["settings"]["admin_password"]:
        res = RedirectResponse("/admin/dashboard", 302)
        res.set_cookie("admin_ok", "yes", httponly=True)
        return res
    return RedirectResponse("/admin?error=1", 302)

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not is_admin(request):
        return RedirectResponse("/admin")
    db = load_db()
    orders = db["orders"]
    revenue = sum(o["grand_total"] for o in orders if o["status"] != "cancelled")
    # recent 5
    recent_orders = sorted(orders, key=lambda x: x.get("created_at",""), reverse=True)[:5]
    # low stock
    low_stock = [p for p in db["products"] if p["stock"] < 10]
    # stats by status
    status_counts = {}
    for o in orders:
        status_counts[o["status"]] = status_counts.get(o["status"], 0) + 1

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request, "products": db["products"],
        "orders": orders, "recent_orders": recent_orders,
        "settings": db["settings"],
        "total_products": len(db["products"]),
        "total_orders": len(orders), "total_revenue": revenue,
        "pending_orders": status_counts.get("pending", 0),
        "delivered_orders": status_counts.get("delivered", 0),
        "low_stock": low_stock,
        "reviews": db.get("reviews", [])
    })

@app.get("/admin/orders/{oid}", response_class=HTMLResponse)
async def order_detail(request: Request, oid: str):
    if not is_admin(request):
        return RedirectResponse("/admin")
    db = load_db()
    order = next((o for o in db["orders"] if o["id"] == oid), None)
    if not order:
        raise HTTPException(404)
    return templates.TemplateResponse("admin_order_detail.html", {
        "request": request, "order": order, "settings": db["settings"]
    })

@app.get("/admin/products/add", response_class=HTMLResponse)
async def add_product_page(request: Request):
    if not is_admin(request): return RedirectResponse("/admin")
    db = load_db()
    return templates.TemplateResponse("admin_product_form.html", {
        "request": request, "product": None, "settings": db["settings"]
    })

@app.post("/admin/products/add")
async def add_product(request: Request,
    name: str = Form(...), price: float = Form(...), original_price: float = Form(0),
    category: str = Form(...), description: str = Form(...), stock: int = Form(...),
    tags: str = Form(""), featured: str = Form("off"),
    image1: str = Form(""), image2: str = Form(""), image3: str = Form("")):
    if not is_admin(request): return RedirectResponse("/admin")
    db = load_db()
    images = [i for i in [image1, image2, image3] if i.strip()]
    if not images:
        images = ["https://placehold.co/800x600/1a1a26/64748b?text=No+Image"]
    db["products"].append({
        "id": str(uuid.uuid4())[:8], "name": name,
        "price": price, "original_price": original_price or price,
        "category": category, "description": description,
        "stock": stock, "images": images,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "featured": featured == "on",
        "created_at": datetime.now().strftime("%d %b %Y")
    })
    save_db(db)
    return RedirectResponse("/admin/dashboard", 302)

@app.get("/admin/products/edit/{pid}", response_class=HTMLResponse)
async def edit_product_page(request: Request, pid: str):
    if not is_admin(request): return RedirectResponse("/admin")
    db = load_db()
    product = get_product(db, pid)
    return templates.TemplateResponse("admin_product_form.html", {
        "request": request, "product": product, "settings": db["settings"]
    })

@app.post("/admin/products/edit/{pid}")
async def edit_product(request: Request, pid: str,
    name: str = Form(...), price: float = Form(...), original_price: float = Form(0),
    category: str = Form(...), description: str = Form(...), stock: int = Form(...),
    tags: str = Form(""), featured: str = Form("off"),
    image1: str = Form(""), image2: str = Form(""), image3: str = Form("")):
    if not is_admin(request): return RedirectResponse("/admin")
    db = load_db()
    images = [i for i in [image1, image2, image3] if i.strip()]
    for p in db["products"]:
        if p["id"] == pid:
            p.update({"name": name, "price": price, "original_price": original_price or price,
                      "category": category, "description": description, "stock": stock,
                      "images": images or p.get("images", []),
                      "tags": [t.strip() for t in tags.split(",") if t.strip()],
                      "featured": featured == "on"})
    save_db(db)
    return RedirectResponse("/admin/dashboard", 302)

@app.post("/admin/products/delete/{pid}")
async def delete_product(request: Request, pid: str):
    if not is_admin(request): return RedirectResponse("/admin")
    db = load_db()
    db["products"] = [p for p in db["products"] if p["id"] != pid]
    save_db(db)
    return RedirectResponse("/admin/dashboard", 302)

@app.post("/admin/orders/update/{oid}")
async def update_order(request: Request, oid: str, status: str = Form(...)):
    if not is_admin(request): return RedirectResponse("/admin")
    db = load_db()
    for o in db["orders"]:
        if o["id"] == oid:
            o["status"] = status
    save_db(db)
    return RedirectResponse("/admin/dashboard", 302)

@app.post("/admin/settings/update")
async def update_settings(request: Request,
    store_name: str = Form(...), currency: str = Form(...),
    admin_password: str = Form(...), store_tagline: str = Form(""),
    whatsapp: str = Form(""), email: str = Form(""),
    address: str = Form(""), announcement: str = Form(""),
    free_shipping_above: int = Form(3000)):
    if not is_admin(request): return RedirectResponse("/admin")
    db = load_db()
    db["settings"].update({"store_name": store_name, "currency": currency,
        "admin_password": admin_password, "store_tagline": store_tagline,
        "whatsapp": whatsapp, "email": email, "address": address,
        "announcement": announcement, "free_shipping_above": free_shipping_above})
    save_db(db)
    return RedirectResponse("/admin/dashboard", 302)

@app.get("/admin/logout")
async def logout():
    res = RedirectResponse("/admin")
    res.delete_cookie("admin_ok")
    return res

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
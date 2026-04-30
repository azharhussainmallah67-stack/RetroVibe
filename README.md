# 🛍️ MyStore — FastAPI E-Commerce Website

## 📁 Project Structure (File System)
```
mystore/
├── main.py               ← Main application (sabhi routes yahan hain)
├── requirements.txt      ← Python packages
├── database/
│   └── store.json        ← Aapka data (automatic ban jata hai)
├── templates/
│   ├── base.html         ← Common navbar/footer
│   ├── index.html        ← Home page (products list)
│   ├── product_detail.html  ← Product + Order form
│   ├── order_success.html   ← Order confirm page
│   ├── admin_login.html     ← Admin login
│   ├── admin_dashboard.html ← Full admin panel
│   └── admin_product_form.html ← Product add/edit
└── static/               ← CSS/JS files (extra)
```

---

## 🚀 Step-by-Step Setup (Kaise Chalayein)

### Step 1: Python Install Karein
```
Python 3.10+ download karein: https://python.org
```

### Step 2: Project Folder Mein Jao
```bash
cd mystore
```

### Step 3: Virtual Environment Banao (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 4: Packages Install Karein
```bash
pip install -r requirements.txt
```

### Step 5: Server Start Karein
```bash
python main.py
```
Ya phir:
```bash
uvicorn main:app --reload --port 8000
```

### Step 6: Browser Mein Kholein
```
Store (Customer):  http://localhost:8000
Admin Panel:       http://localhost:8000/admin
Admin Password:    admin123
```

---

## 🌟 Website Ki Features

### Customer Side:
- ✅ Home page par sab products dikhta hai
- ✅ Category filter (Electronics, Clothing, etc.)
- ✅ Search bar
- ✅ Product detail page
- ✅ Order form (naam, phone, address)
- ✅ Order confirmation page

### Admin Panel (/admin):
- ✅ Secure login (password protected)
- ✅ Dashboard — stats (products, orders, revenue)
- ✅ Products manage — Add, Edit, Delete
- ✅ Orders manage — Status update (Pending → Delivered)
- ✅ Store settings — Naam, currency, password change

---

## 🔧 Admin Password Kaise Change Karein
Admin panel → Settings tab → Naya password likhein → Save

Ya database/store.json file mein "admin_password" key change karein.

---

## 📦 Naya Product Add Karna
1. `/admin` pe login karein
2. Products tab → "+ Naya Product" button
3. Details bharein (naam, qeemat, image URL, stock)
4. Add Karein!

---

## 💡 Tips
- Image ke liye koi bhi image URL use karein (Google se bhi)
- Database `database/store.json` mein save hota hai
- `--reload` flag se code change pe auto-restart hota hai

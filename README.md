---

# 🏛️ Kilimanjaro Revival Temple (VCCT Website)

This is a web-based Church Management and Information System built using **Django**.
The system provides church information, ministries, events, gallery, and contact features.

## 📌 Features

* Home page with church overview
* About page with church vision and leadership
* Ministries listing and details
* Events management and registration
* Gallery for church activities
* Contact form for visitors
* Admin dashboard for managing content

---

## 🗂️ Project Structure

```
krt/
├── manage.py
├── requirements.txt
├── krt/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   └── admin.py
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── media/
│   ├── events/
│   ├── ministries/
│   └── profiles/
└── templates/
    ├── base.html
    ├── home.html
    └── core/
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/Patr12/kilimanjarorevaltemple.git
cd kilimanjarorevaltemple
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Configure Environment Variables

Create a `.env` file:

```
DEBUG=True
SECRET_KEY=your_secret_key
```

---

### 5️⃣ Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

### 6️⃣ Create Superuser

```bash
python manage.py createsuperuser
```

---

### 7️⃣ Run Server

```bash
python manage.py runserver
```

Open browser:

```
http://127.0.0.1:8000/
```

Admin panel:

```
http://127.0.0.1:8000/admin
```

---

## 🧩 Technologies Used

* Python 3
* Django
* HTML5
* CSS3
* Bootstrap
* JavaScript
* SQLite (default)

---

## 🏗️ Future Improvements

* Online donation system
* Sermons upload (audio/video)
* Member management system
* REST API for mobile app
* Multi-language support

---

## 🤝 Contribution

Contributions are welcome.
Fork the repository and submit a pull request.

---

## 📜 License

This project is for educational and church use only.

---

## ✝️ Developed By

**Patrice S. Mgala**
Software Engineering Student
Tanzania 🇹🇿

---

## 🚀 How to Add This README

Create file:

```bash
README.md
```

Then paste content above and push:

```bash
git add README.md
git commit -m "Add project README"
git push
```

---

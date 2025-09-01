# Tennis Kort Bron Qilish Boti

Bu loyiha tennis kortlarini Telegram orqali bron qilish uchun zamonaviy bot hisoblanadi. Bot o'zbek va rus tillarida ishlaydi.

## Xususiyatlar

### Foydalanuvchilar uchun:
- 🎾 Tennis kortlarini real vaqtda bron qilish
- 📅 Oynaviy kalendar va soat tanlash
- 💰 Avtomatik narx hisoblash (peak/off-peak, chegirma)
- 💳 Onlayn to'lov (Payme, Click, Uzum Pay)
- 🎫 QR-kodli e-ticket
- 📱 Buyurtmalar tarixi va boshqaruv
- 🔔 Avtomatik eslatmalar
- 🧪 **VAQTINCHA REJIM**: To'lov avtomatik tasdiqlash

### Adminlar uchun:
- 📊 Kuchli admin panel
- 🗓 Kundalik jadval (Gantt ko'rinish)
- ✅ QR verifikatsiya tizimi
- 📈 Hisobotlar va Excel eksport
- 👥 Foydalanuvchilarni boshqarish
- 🏟 Kortlar va narxlarni sozlash

## Texnologiyalar

- **Backend**: Python 3.11+, aiogram 3.x
- **Ma'lumotlar bazasi**: PostgreSQL
- **Kesh**: Redis
- **To'lov**: Payme, Click, Uzum Pay
- **QR kodlar**: qrcode, Pillow
- **Hisobotlar**: openpyxl, reportlab

## O'rnatish

### 1. Loyihani klonlash
```bash
git clone <repository-url>
cd teniskorbot
```

### 2. Virtual muhitni yaratish
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\\Scripts\\activate  # Windows
```

### 3. Bog'liqliklarni o'rnatish
```bash
pip install -r requirements.txt
```

### 4. PostgreSQL o'rnatish
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# PostgreSQL ni ishga tushirish
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Ma'lumotlar bazasini yaratish
sudo -u postgres psql
CREATE DATABASE tennis_bot_db;
CREATE USER tennis_bot_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE tennis_bot_db TO tennis_bot_user;
\q
```

### 5. Environment o'zgaruvchilarini sozlash
`.env` faylini yarating:
```bash
touch .env
```

`.env` faylini to'ldiring:
```env
BOT_TOKEN=your_bot_token_here
DATABASE_URL=postgresql+asyncpg://tennis_bot_user:your_password@localhost:5432/tennis_bot_db
```

### 6. Botni ishga tushirish
```bash
python run.py
```

## Konfiguratsiya

### Asosiy sozlamalar (.env fayli):

```env
# Bot
BOT_TOKEN=your_bot_token_here

# Database
DATABASE_URL=postgresql://username:password@localhost:5432/tennis_bot_db

# Redis
REDIS_URL=redis://localhost:6379/0

# To'lov tizimlari
PAYME_MERCHANT_ID=your_merchant_id
PAYME_SECRET_KEY=your_secret_key
CLICK_MERCHANT_ID=your_merchant_id
CLICK_SECRET_KEY=your_secret_key

# Admin
ADMIN_CHAT_IDS=123456789,987654321
SUPER_ADMIN_ID=123456789

# VAQTINCHA REJIM - To'lovni qo'lda tasdiqlash (True/False)
MANUAL_PAYMENT_MODE=True

# Narxlar (so'mda)
BASE_PRICE_PEAK=50000
BASE_PRICE_OFFPEAK=30000
WEEKEND_COEFFICIENT=1.2
VIP_DISCOUNT=0.15

# Vaqt sozlamalari
PEAK_START_HOUR=18
PEAK_END_HOUR=22
COURT_OPEN_HOUR=6
COURT_CLOSE_HOUR=23
```

## Foydalanish

### Foydalanuvchilar uchun:
1. Botni boshlash: `/start`
2. Telefon raqamni ulashish
3. Kort va vaqt tanlash
4. To'lovni amalga oshirish
5. QR-kodli biletni olish

### Adminlar uchun:
1. Admin panelni ochish: `/admin`
2. Bronlarni ko'rish va boshqarish
3. QR kodlarni tekshirish
4. Hisobotlarni yaratish va yuklash

## API Endpointlar

### Webhook'lar:
- `POST /webhook/payme` - Payme to'lov webhook'i
- `POST /webhook/click` - Click to'lov webhook'i
- `POST /webhook/uzum` - Uzum Pay webhook'i

## Fayl strukturasi

```
teniskorbot/
├── bot.py              # Asosiy bot logikasi
├── admin.py            # Admin panel funksiyalari
├── database.py         # Ma'lumotlar bazasi modellari
├── config.py           # Konfiguratsiya
├── localization.py     # Ko'p tillilik
├── keyboards.py        # Telegram klaviaturas
├── payments.py         # To'lov tizimlari
├── utils.py            # Yordamchi funksiyalar
├── main.py            # Ishga tushirish fayli
├── requirements.txt    # Python bog'liqliklar
├── env_example.txt    # Environment namuna
├── alembic.ini        # Database migratsiya sozlamalari
└── README.md          # Bu fayl
```

## Xususiyatlar

### 1. Bron qilish jarayoni
- Kalendar orqali sana tanlash
- Mavjud vaqt slotlarini ko'rsatish
- Avtomatik narx hisoblash
- To'lov va bilet yaratish

### ⚠️ VAQTINCHA REJIM
Hozirda bot **vaqtincha rejimda** ishlaydi:
- To'lov tizimlari qo'lda tasdiqlash rejimida
- Har qanday to'lov avtomatik muvaffaqiyatli hisoblanadi
- 5 soniya kutgandan so'ng bilet avtomatik yaratiladi
- Haqiqiy to'lov API'lari ishlamaydi

Bu rejimni o'zgartirish uchun `.env` faylidagi `MANUAL_PAYMENT_MODE=False` qilib qo'ying.

### 2. QR bilet tizimi
- Noyob QR kodlar yaratish
- PDF va rasm formatida biletlar
- Admin tomonidan tekshirish
- Bir martalik foydalanish

### 3. To'lov tizimlari
- Payme integratsiyasi
- Click integratsiyasi  
- Uzum Pay qo'llab-quvvatlash
- Webhook'lar orqali holat yangilash

### 4. Admin panel
- Real vaqt statistika
- QR verifikatsiya
- Hisobotlar va eksport
- Foydalanuvchilarni boshqarish

## Xavfsizlik

- To'lov imzolarini tekshirish
- QR kodlarni shifrlash
- Admin huquqlarini tekshirish
- SQL injection himoyasi

## Monitoring va Logging

- Barcha amallar loglanadi
- Xatolar tracking
- Performance monitoring
- Database so'rovlari optimizatsiyasi

## Qo'llab-quvvatlash

Savollar yoki muammolar bo'lsa:
- Telegram: @your_support_username
- Email: support@example.com
- Telefon: +998 90 123 45 67

## Litsenziya

Bu loyiha MIT litsenziyasi ostida tarqatiladi.

## Hissa qo'shish

1. Fork qiling
2. Feature branch yarating (`git checkout -b feature/AmazingFeature`)
3. O'zgarishlarni commit qiling (`git commit -m 'Add some AmazingFeature'`)
4. Branch'ni push qiling (`git push origin feature/AmazingFeature`)
5. Pull Request yarating

## Changelog

### v1.0.0 (2024-12-01)
- Asosiy bot funksiyalari
- Bron qilish tizimi
- To'lov integratsiyasi
- QR bilet tizimi
- Admin panel
- Ko'p tillilik qo'llab-quvvatlash

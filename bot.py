"""
Asosiy Telegram bot
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, Update
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database import async_session, User, Court, Booking, Payment, Ticket, BookingStatus, PaymentStatus, UserRole
from localization import get_text
from keyboards import *
from utils import *
from payments import payment_manager, PaymentError

# Logging sozlash
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot va dispatcher
bot = Bot(token=Config.BOT_TOKEN)

# Storage - faqat Memory storage (Redis muammolarini oldini olish uchun)
storage = MemoryStorage()

dp = Dispatcher(storage=storage)
router = Router()

# States
class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_surname = State()

class BookingStates(StatesGroup):
    selecting_date = State()
    selecting_court = State()
    selecting_time = State()
    confirming_booking = State()
    processing_payment = State()

class AdminStates(StatesGroup):
    main_menu = State()
    viewing_bookings = State()
    qr_checking = State()

# Middleware
async def get_user_language(user_id: int) -> str:
    """Foydalanuvchi tilini olish"""
    async with async_session() as session:
        result = await session.execute(
            select(User.language).where(User.telegram_id == user_id)
        )
        user_lang = result.scalar()
        return user_lang or Config.DEFAULT_LANGUAGE

async def get_or_create_user(telegram_user, session: AsyncSession) -> User:
    """Foydalanuvchini olish yoki yaratish"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Yangi foydalanuvchi yaratish
        user = User(
            telegram_id=telegram_user.id,
            first_name=telegram_user.first_name or "Noma'lum",
            last_name=telegram_user.last_name,
            username=telegram_user.username,
            phone_number="",  # Keyinchalik to'ldiriladi
            language=Config.DEFAULT_LANGUAGE
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    return user

# Handlers
@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    """Start komandasi"""
    async with async_session() as session:
        user = await get_or_create_user(message.from_user, session)
        lang = user.language
        
        if not user.phone_number:
            # Telefon raqam so'rash
            await message.answer(
                "📱 Iltimos, telefon raqamingizni yuboring:",
                reply_markup=get_contact_keyboard(lang)
            )
        elif not user.first_name or not user.last_name:
            # Ism familiya so'rash
            await state.set_state("waiting_for_name")
            await message.answer(
                "👤 Iltimos, ism va familiyangizni yuboring:\n\nMisol: Ahmad Karimov"
            )
        else:
            # Asosiy menyuni ko'rsatish
            await message.answer(
                get_text("main_menu", lang),
                reply_markup=get_main_menu_keyboard(lang)
            )

@router.message(F.contact)
async def contact_handler(message: Message, state: FSMContext):
    """Telefon raqam qabul qilish"""
    async with async_session() as session:
        user = await get_or_create_user(message.from_user, session)
        lang = user.language
        
        # Telefon raqamni saqlash
        phone = format_phone_number(message.contact.phone_number)
        user.phone_number = phone
        await session.commit()
        
        # Ism familiya so'rash
        await state.set_state("waiting_for_name")
        await message.answer(
            "👤 Iltimos, ism va familiyangizni yuboring:\n\nMisol: Ahmad Karimov"
        )

@router.message(F.text, F.state == "waiting_for_name")
async def name_handler(message: Message, state: FSMContext):
    """Ism familiya qabul qilish"""
    
    async with async_session() as session:
        user = await get_or_create_user(message.from_user, session)
        lang = user.language
        
        # Ism va familiyani ajratish
        name_parts = message.text.strip().split()
        if len(name_parts) >= 2:
            user.first_name = name_parts[0]
            user.last_name = " ".join(name_parts[1:])
        else:
            user.first_name = message.text.strip()
            user.last_name = ""
        
        await session.commit()
        await state.clear()
        
        # Asosiy menyuni ko'rsatish
        await message.answer(
            "✅ Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!\n\n🎾 Tennis kort bron qilish botiga xush kelibsiz!",
            reply_markup=get_main_menu_keyboard(lang)
        )



@router.message(F.text.in_([
    "🗓 Bron qilish", "🗓 Забронировать"
]))
async def book_court_handler(message: Message, state: FSMContext):
    """Kort bron qilish"""
    async with async_session() as session:
        user = await get_or_create_user(message.from_user, session)
        lang = user.language
        
        # Joriy oy kalendari
        now = get_uzbekistan_time()
        await message.answer(
            get_text("select_month", lang),
            reply_markup=get_calendar_keyboard(now.year, now.month, lang)
        )
        await state.set_state(BookingStates.selecting_date)

@router.callback_query(F.data.startswith("date:"))
async def date_selected_handler(callback: CallbackQuery, state: FSMContext):
    """Sana tanlandi"""
    date_str = callback.data.split(":")[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    async with async_session() as session:
        user = await get_or_create_user(callback.from_user, session)
        lang = user.language
        
        # Kortlarni olish
        result = await session.execute(
            select(Court).where(Court.is_active == True)
        )
        courts = result.scalars().all()
        
        if not courts:
            await callback.answer(get_text("error_occurred", lang))
            return
        
        # Bitta kort bo'lsa, avtomatik tanlash
        if len(courts) == 1:
            court = courts[0]
            await state.update_data(selected_date=selected_date, selected_court=court.id)
            
            # Vaqt slotlarini ko'rsatish
            await show_time_slots(callback, state, selected_date, court.id, lang)
        else:
            # Kort tanlash
            await state.update_data(selected_date=selected_date)
            courts_data = [{'id': c.id, 'name': c.name, 'is_indoor': c.is_indoor} for c in courts]
            
            await callback.message.edit_text(
                get_text("select_court", lang),
                reply_markup=get_courts_keyboard(courts_data, lang)
            )
            await state.set_state(BookingStates.selecting_court)

@router.callback_query(F.data.startswith("court:"))
async def court_selected_handler(callback: CallbackQuery, state: FSMContext):
    """Kort tanlandi"""
    court_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected_date = data.get('selected_date')
    
    if not selected_date:
        await callback.answer("Xatolik yuz berdi")
        return
    
    await state.update_data(selected_court=court_id)
    
    lang = await get_user_language(callback.from_user.id)
    await show_time_slots(callback, state, selected_date, court_id, lang)

async def show_time_slots(callback: CallbackQuery, state: FSMContext, 
                         selected_date, court_id: int, lang: str):
    """Vaqt slotlarini ko'rsatish"""
    async with async_session() as session:
        # Band vaqtlarni olish
        booking_date = datetime.combine(selected_date, datetime.min.time())
        next_day = booking_date + timedelta(days=1)
        
        result = await session.execute(
            select(Booking).where(
                and_(
                    Booking.court_id == court_id,
                    Booking.start_time >= booking_date,
                    Booking.start_time < next_day,
                    Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PAID, BookingStatus.HOLD])
                )
            )
        )
        booked_slots = result.scalars().all()
        
        # Bo'sh slotlarni olish
        booked_times = [{'start_time': b.start_time, 'end_time': b.end_time} for b in booked_slots]
        available_slots = get_available_time_slots(booking_date, court_id, booked_times)
        
        if not available_slots:
            await callback.message.edit_text(
                get_text("no_available_slots", lang),
                reply_markup=get_back_keyboard("back:main", lang)
            )
            return
        
        await callback.message.edit_text(
            get_text("select_time", lang),
            reply_markup=get_time_slots_keyboard(available_slots, lang)
        )
        await state.set_state(BookingStates.selecting_time)

@router.callback_query(F.data.startswith("time_"))
async def time_selected_handler(callback: CallbackQuery, state: FSMContext):
    """Vaqt tanlandi"""
    await callback.answer()  # Tugma bosilganini tasdiqlash
    
    # "time_10_00" -> "10:00"
    time_part = callback.data[5:]  # "time_" ni olib tashlash
    time_str = time_part.replace("_", ":")
    
    
    if time_str == "none":
        return
    
    try:
        selected_time = datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        await callback.message.answer("Noto'g'ri vaqt formati")
        return
    data = await state.get_data()
    
    selected_date = data.get('selected_date')
    court_id = data.get('selected_court')
    
    if not selected_date or not court_id:
        await callback.answer("Xatolik yuz berdi")
        return
    
    # To'liq datetime yaratish
    start_datetime = datetime.combine(selected_date, selected_time)
    start_datetime = Config.get_timezone().localize(start_datetime)
    end_datetime = start_datetime + timedelta(hours=1)
    
    async with async_session() as session:
        # Kort ma'lumotlarini olish
        court = await session.get(Court, court_id)
        user = await get_or_create_user(callback.from_user, session)
        lang = user.language
        
        if not court:
            await callback.answer(get_text("court_not_available", lang))
            return
        
        # Narxni hisoblash
        pricing = calculate_booking_price(
            court.hourly_rate_peak,
            court.hourly_rate_offpeak,
            1.0,  # 1 soat
            start_datetime,
            user.is_vip
        )
        
        # Bron ma'lumotlarini saqlash
        booking_data = {
            'court_id': court_id,
            'court_name': court.name,
            'start_time': start_datetime,
            'end_time': end_datetime,
            'date': selected_date.strftime("%d.%m.%Y"),
            'start_time_str': start_datetime.strftime("%H:%M"),
            'end_time_str': end_datetime.strftime("%H:%M"),
            'duration': 1,
            **pricing
        }
        
        await state.update_data(booking_data=booking_data)
        
        # Tasdiqlash sahifasi
        summary = create_booking_summary(booking_data, lang)
        
        await callback.message.edit_text(
            summary,
            reply_markup=get_booking_confirmation_keyboard(lang)
        )
        await state.set_state(BookingStates.confirming_booking)

@router.callback_query(F.data == "booking:confirm")
async def confirm_booking_handler(callback: CallbackQuery, state: FSMContext):
    """Bronni tasdiqlash"""
    data = await state.get_data()
    booking_data = data.get('booking_data')
    
    if not booking_data:
        await callback.answer("Xatolik yuz berdi")
        return
    
    async with async_session() as session:
        user = await get_or_create_user(callback.from_user, session)
        lang = user.language
        
        # Bron yaratish
        booking = Booking(
            user_id=user.id,
            court_id=booking_data['court_id'],
            booking_date=booking_data['start_time'].date(),
            start_time=booking_data['start_time'],
            end_time=booking_data['end_time'],
            duration_hours=booking_data['duration'],
            total_amount=booking_data['subtotal'],
            discount_amount=booking_data['discount'],
            service_fee=booking_data['service_fee'],
            final_amount=booking_data['final_amount'],
            status=BookingStatus.HOLD,
            is_peak_time=booking_data['is_peak'],
            is_weekend=booking_data['is_weekend'],
            hold_expires_at=get_uzbekistan_time() + timedelta(minutes=Config.BOOKING_HOLD_MINUTES)
        )
        
        session.add(booking)
        await session.commit()
        await session.refresh(booking)
        
        await state.update_data(booking_id=booking.id)
        
        # To'lov usulini tanlash
        await callback.message.edit_text(
            get_text("select_payment_method", lang),
            reply_markup=get_payment_methods_keyboard(lang)
        )
        await state.set_state(BookingStates.processing_payment)

@router.callback_query(F.data.startswith("payment:"))
async def payment_method_handler(callback: CallbackQuery, state: FSMContext):
    """To'lov usuli tanlandi"""
    payment_method_str = callback.data.split(":")[1]
    
    # "To'lov qilindi" tugmasi bosilganda
    if payment_method_str == "done":
        await handle_payment_done(callback, state)
        return
    
    # String qiymatni enum ga aylantirish
    from database import PaymentMethod
    payment_method_map = {
        'payme': PaymentMethod.PAYME,
        'click': PaymentMethod.CLICK,
        'uzum': PaymentMethod.UZUM,
        'cash': PaymentMethod.CASH
    }
    payment_method = payment_method_map.get(payment_method_str, PaymentMethod.PAYME)
    
    data = await state.get_data()
    booking_id = data.get('booking_id')
    
    if not booking_id:
        await callback.answer("Xatolik yuz berdi")
        return
    
    async with async_session() as session:
        booking = await session.get(Booking, booking_id)
        user = await get_or_create_user(callback.from_user, session)
        lang = user.language
        
        if not booking:
            await callback.answer(get_text("error_occurred", lang))
            return
        
        try:
            # To'lov yaratish
            payment_data = await payment_manager.create_payment(
                payment_method,
                booking.final_amount,
                str(booking.id)
            )
            
            # Payment record yaratish
            payment = Payment(
                booking_id=booking.id,
                user_id=user.id,
                payment_method=payment_method,
                amount=booking.final_amount,
                status=PaymentStatus.PENDING,
                external_payment_id=payment_data.get('payment_id'),
                payment_url=payment_data.get('payment_url')
            )
            
            session.add(payment)
            await session.commit()
            
            await callback.message.edit_text(
                get_text("payment_processing", lang)
            )
            
            # VAQTINCHA: To'lov URL o'rniga oddiy xabar
            if Config.MANUAL_PAYMENT_MODE:
                await callback.message.answer(
                    get_text("payment_manual_mode", lang) + "\n"
                    "5 soniyadan so'ng biletingiz tayyor bo'ladi..."
                )
            else:
                # Haqiqiy to'lov URL yuborish
                if payment_data.get('payment_url'):
                    await callback.message.answer(
                        f"💳 To'lov uchun havola:\n{payment_data['payment_url']}"
                    )
            
            # To'lov holatini tekshirish (background task)
            asyncio.create_task(check_payment_status(booking.id, payment_method, payment_data.get('payment_id')))
            
        except PaymentError as e:
            await callback.message.edit_text(
                get_text("payment_failed", lang) + f"\n\nXatolik: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Payment error: {e}")
            await callback.message.edit_text(
                get_text("error_occurred", lang)
            )

async def check_payment_status(booking_id: int, payment_method, payment_id: str):
    """To'lov holatini tekshirish (background task)"""
    await asyncio.sleep(5)  # 5 soniya kutish
    
    try:
        if Config.MANUAL_PAYMENT_MODE:
            # VAQTINCHA: Avtomatik to'lovni muvaffaqiyatli deb hisoblash
            status = {'status': 'paid', 'transaction_id': f'manual_{payment_id}_{int(datetime.now().timestamp())}'}
        else:
            # Haqiqiy to'lov holatini tekshirish
            # payment_method enum bo'lsa, uning value'sini olish
            payment_method_str = payment_method.value if hasattr(payment_method, 'value') else str(payment_method)
            status = await payment_manager.check_payment_status(payment_method_str, payment_id)
        
        async with async_session() as session:
            booking = await session.get(Booking, booking_id)
            if not booking:
                return
            
            payment = await session.execute(
                select(Payment).where(Payment.booking_id == booking_id)
            )
            payment = payment.scalar_one_or_none()
            
            if status['status'] == 'paid':
                # To'lov muvaffaqiyatli
                booking.status = BookingStatus.CONFIRMED
                if payment:
                    payment.status = PaymentStatus.PAID
                    payment.paid_at = get_uzbekistan_time()
                    payment.transaction_id = status.get('transaction_id')
                
                await session.commit()
                
                # Bilet yaratish
                await create_and_send_ticket(booking, session)
                
                # Foydalanuvchiga muvaffaqiyat xabarini yuborish
                await bot.send_message(
                    booking.user.telegram_id,
                    get_text("payment_success", booking.user.language)
                )
                
            elif status['status'] == 'cancelled' and not Config.MANUAL_PAYMENT_MODE:
                # To'lov bekor qilingan (faqat haqiqiy rejimda)
                booking.status = BookingStatus.CANCELLED
                if payment:
                    payment.status = PaymentStatus.FAILED
                
                await session.commit()
                
                # Foydalanuvchiga xabar yuborish
                await bot.send_message(
                    booking.user.telegram_id,
                    get_text("payment_cancelled", booking.user.language)
                )
    
    except Exception as e:
        logger.error(f"Payment status check error: {e}")

async def handle_payment_done(callback: CallbackQuery, state: FSMContext):
    """To'lov qilindi tugmasi bosilganda"""
    data = await state.get_data()
    booking_id = data.get('booking_id')
    
    if not booking_id:
        await callback.answer("Xatolik yuz berdi")
        return
    
    async with async_session() as session:
        booking = await session.get(Booking, booking_id)
        user = await get_or_create_user(callback.from_user, session)
        lang = user.language
        
        if not booking:
            await callback.answer(get_text("error_occurred", lang))
            return
        
        try:
            # To'lovni avtomatik tasdiqlash
            booking.status = BookingStatus.CONFIRMED
            
            # Payment record yaratish (cash to'lov sifatida)
            from database import PaymentMethod, PaymentStatus
            payment = Payment(
                booking_id=booking.id,
                user_id=user.id,
                payment_method=PaymentMethod.CASH,
                amount=booking.final_amount,
                status=PaymentStatus.PAID,
                external_payment_id=f"cash_manual_{booking.id}",
                paid_at=get_uzbekistan_time(),
                transaction_id=f"cash_{booking.id}_{int(datetime.now().timestamp())}"
            )
            
            session.add(payment)
            await session.commit()
            
            # Xabar yuborish
            await callback.message.edit_text(
                "✅ To'lov tasdiqlandi!\n\nBiletingiz tayyorlanmoqda..."
            )
            
            # Bilet yaratish va yuborish
            await create_and_send_ticket(booking, session)
            
            # Muvaffaqiyat xabari
            await bot.send_message(
                user.telegram_id,
                get_text("payment_success", lang)
            )
            
        except Exception as e:
            logger.error(f"Payment done error: {e}")
            await callback.message.edit_text(
                get_text("error_occurred", lang) + f"\n\nXatolik: {str(e)}"
            )

async def create_and_send_ticket(booking: Booking, session: AsyncSession):
    """Bilet yaratish va yuborish"""
    try:
        # Ticket ID yaratish
        ticket_id = generate_ticket_id(booking.id, booking.court_id, booking.start_time)
        
        # QR kod ma'lumotlari
        qr_data = {
            'ticket_id': ticket_id,
            'booking_id': booking.id,
            'user_id': booking.user_id,
            'court_id': booking.court_id,
            'start_time': booking.start_time.isoformat(),
            'amount': float(booking.final_amount)
        }
        qr_string = json.dumps(qr_data)
        
        # QR kod fayli yo'li
        qr_path = f"{Config.TICKETS_PATH}/qr_{ticket_id}.png"
        save_qr_code(qr_string, qr_path)
        
        # Ticket record yaratish
        ticket = Ticket(
            booking_id=booking.id,
            ticket_id=ticket_id,
            qr_code_data=qr_string,
            qr_code_path=qr_path
        )
        
        session.add(ticket)
        await session.commit()
        
        # Foydalanuvchiga bilet yuborish
        # User va Court ma'lumotlarini olish
        from sqlalchemy import select
        user_result = await session.execute(select(User).where(User.id == booking.user_id))
        user = user_result.scalar_one()
        
        court_result = await session.execute(select(Court).where(Court.id == booking.court_id))
        court = court_result.scalar_one()
        
        ticket_info = get_text("ticket_generated", user.language).format(
            ticket_id=ticket_id,
            date=booking.booking_date.strftime("%d.%m.%Y"),
            start_time=booking.start_time.strftime("%H:%M"),
            end_time=booking.end_time.strftime("%H:%M"),
            court_name=court.name,
            amount=booking.final_amount
        )
        
        # Bilet rasmini yaratish va yuborish
        from utils import create_ticket_image
        ticket_image_path = f"{Config.TICKETS_PATH}/ticket_{ticket_id}.png"
        ticket_data = {
            'ticket_id': ticket_id,
            'user_name': f"{user.first_name} {user.last_name or ''}".strip(),
            'phone': user.phone_number or "N/A",
            'date': booking.booking_date.strftime("%d.%m.%Y"),
            'start_time': booking.start_time.strftime("%H:%M"),
            'end_time': booking.end_time.strftime("%H:%M"),
            'court_name': court.name,
            'amount': booking.final_amount,
            'payment_status': 'To\'langan',
            'created_at': get_uzbekistan_time().strftime("%d.%m.%Y %H:%M"),
            'qr_code_path': qr_path
        }
        
        create_ticket_image(ticket_data, qr_path, ticket_image_path)
        
        # Bilet rasmini yuborish
        from aiogram.types import FSInputFile
        ticket_photo = FSInputFile(ticket_image_path)
        await bot.send_photo(
            user.telegram_id,
            photo=ticket_photo,
            caption=f"🎫 Sizning biletingiz tayyor!\n\nBilet ID: {ticket_id}\nKort: {court.name}\nSana: {booking.booking_date.strftime('%d.%m.%Y')}\nVaqt: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\nSumma: {booking.final_amount:,.0f} so'm\n\nQR kodni kirish vaqtida ko'rsating!"
        )
        
    except Exception as e:
        logger.error(f"Ticket creation error: {e}")

@router.message(F.text.in_([
    "🎫 Buyurtmalarim", "🎫 Мои заказы"
]))
async def my_bookings_handler(message: Message):
    """Buyurtmalarni ko'rsatish"""
    async with async_session() as session:
        user = await get_or_create_user(message.from_user, session)
        lang = user.language
        
        await message.answer(
            get_text("my_bookings_menu", lang),
            reply_markup=get_my_bookings_keyboard(lang)
        )

# Calendar navigation handlers
@router.callback_query(F.data.startswith("cal:"))
async def calendar_navigation_handler(callback: CallbackQuery, state: FSMContext):
    """Kalendar navigatsiyasi"""
    await callback.answer()  # Tugma bosilganini tasdiqlash
    
    action = callback.data.split(":")[1]
    
    if action == "ignore":
        return
    
    if action in ["prev", "next"]:
        year = int(callback.data.split(":")[2])
        month = int(callback.data.split(":")[3])
        
        if action == "prev":
            if month == 1:
                month = 12
                year -= 1
            else:
                month -= 1
        else:  # next
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1
        
        lang = await get_user_language(callback.from_user.id)
        
        try:
            await callback.message.edit_reply_markup(
                reply_markup=get_calendar_keyboard(year, month, lang)
            )
        except Exception as e:
            # Agar xabar o'zgarmagan bo'lsa, xatoni ignore qilamiz
            logger.warning(f"Calendar edit failed: {e}")
            pass

# Back button handlers
@router.callback_query(F.data.startswith("back:"))
async def back_button_handler(callback: CallbackQuery, state: FSMContext):
    """Orqaga tugmalari"""
    destination = callback.data.split(":")[1]
    lang = await get_user_language(callback.from_user.id)
    
    if destination == "main":
        await callback.message.edit_text(
            get_text("main_menu", lang),
            reply_markup=None
        )
        await callback.message.answer(
            get_text("main_menu", lang),
            reply_markup=get_main_menu_keyboard(lang)
        )
        await state.clear()
    elif destination == "date":
        # Kalendarga qaytish
        now = get_uzbekistan_time()
        await callback.message.edit_text(
            get_text("select_month", lang),
            reply_markup=get_calendar_keyboard(now.year, now.month, lang)
        )
        await state.set_state(BookingStates.selecting_date)
    
    await callback.answer()

@router.callback_query(F.data == "bookings:active")
async def active_bookings_handler(callback: CallbackQuery):
    """Faol bronlarni ko'rsatish"""
    async with async_session() as session:
        user = await get_or_create_user(callback.from_user, session)
        lang = user.language
        
        now = get_uzbekistan_time()
        result = await session.execute(
            select(Booking).join(Court).where(
                and_(
                    Booking.user_id == user.id,
                    Booking.start_time > now,
                    Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PAID])
                )
            ).order_by(Booking.start_time)
        )
        
        bookings = result.scalars().all()
        
        if not bookings:
            await callback.message.edit_text(
                get_text("no_active_bookings", lang),
                reply_markup=get_back_keyboard("back:main", lang)
            )
            return
        
        # Birinchi bronni ko'rsatish
        booking = bookings[0]
        await show_booking_details(callback, booking, lang, can_cancel=True)

# Language change handler
@router.callback_query(F.data.startswith("lang:"))
async def language_change_handler(callback: CallbackQuery):
    """Tilni o'zgartirish"""
    new_lang = callback.data.split(":")[1]
    
    async with async_session() as session:
        user = await get_or_create_user(callback.from_user, session)
        user.language = new_lang
        await session.commit()
        
        await callback.message.edit_text(
            get_text("main_menu", new_lang),
            reply_markup=None
        )
        await callback.message.answer(
            get_text("main_menu", new_lang),
            reply_markup=get_main_menu_keyboard(new_lang)
        )
    
    await callback.answer()

async def show_booking_details(callback: CallbackQuery, booking: Booking, 
                             lang: str, can_cancel: bool = False):
    """Bron tafsilotlarini ko'rsatish"""
    status_emoji = get_booking_status_emoji(booking.status.value)
    
    booking_text = get_text("booking_info", lang).format(
        booking_id=booking.id,
        date=booking.booking_date.strftime("%d.%m.%Y"),
        start_time=booking.start_time.strftime("%H:%M"),
        end_time=booking.end_time.strftime("%H:%M"),
        court_name=booking.court.name,
        amount=booking.final_amount,
        status=f"{status_emoji} {booking.status.value}",
        additional_info=""
    )
    
    await callback.message.edit_text(
        booking_text,
        reply_markup=get_booking_actions_keyboard(booking.id, can_cancel, lang)
    )

# Admin handlers
@router.message(Command("admin"))
async def admin_panel_handler(message: Message):
    """Admin panel"""
    async with async_session() as session:
        user = await get_or_create_user(message.from_user, session)
        
        # Admin huquqlarini tekshirish
        if user.role not in [UserRole.ADMIN, UserRole.OWNER, UserRole.MANAGER]:
            return
        
        lang = user.language
        await message.answer(
            get_text("admin_panel", lang),
            reply_markup=get_admin_main_keyboard(lang)
        )

# Main menu handlers
@router.message(F.text.in_([
    "👤 Mening profilim", "👤 Мой профиль"
]))
async def my_profile_handler(message: Message):
    """Profil ma'lumotlari"""
    async with async_session() as session:
        user = await get_or_create_user(message.from_user, session)
        lang = user.language
        
        profile_text = f"""
👤 **Sizning profilingiz:**

📱 **Telefon:** {user.phone_number or 'Kiritilmagan'}
👤 **Ism:** {user.first_name or 'Kiritilmagan'}
👤 **Familiya:** {user.last_name or 'Kiritilmagan'}
🌐 **Til:** {user.language.upper()}
📅 **Ro'yxatdan o'tgan:** {user.created_at.strftime('%d.%m.%Y')}
        """
        
        await message.answer(profile_text)

@router.message(F.text.in_([
    "ℹ️ Qoidalar", "ℹ️ Правила"
]))
async def rules_handler(message: Message):
    """Qoidalar"""
    async with async_session() as session:
        user = await get_or_create_user(message.from_user, session)
        lang = user.language
        
        rules_text = get_text("rules_text", lang)
        await message.answer(rules_text)

@router.message(F.text.in_([
    "❓ Yordam", "❓ Помощь"
]))
async def help_handler(message: Message):
    """Yordam"""
    async with async_session() as session:
        user = await get_or_create_user(message.from_user, session)
        lang = user.language
        
        help_text = get_text("help_text", lang)
        await message.answer(help_text)

@router.message(F.text.in_([
    "🌐 Til", "🌐 Язык"
]))
async def language_handler(message: Message):
    """Til tanlash"""
    async with async_session() as session:
        user = await get_or_create_user(message.from_user, session)
        lang = user.language
        
        await message.answer(
            "🌐 Tilni tanlang:",
            reply_markup=get_language_keyboard()
        )

# Error handler
@dp.error()
async def error_handler(event, exception: Exception):
    """Xatolarni boshqarish"""
    logger.error(f"Error occurred: {exception}")
    
    try:
        # Agar callback query bo'lsa
        if hasattr(event, 'callback_query') and event.callback_query:
            await event.callback_query.answer("❌ Xatolik yuz berdi", show_alert=False)
        # Agar oddiy message bo'lsa
        elif hasattr(event, 'message') and event.message:
            await event.message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
    except Exception as e:
        logger.error(f"Error in error_handler: {e}")
    
    return True

# Dispatcher sozlash
dp.include_router(router)

async def main():
    """Asosiy funksiya"""
    try:
        # Ma'lumotlar bazasini boshlang'ich holatga keltirish
        from database import init_database
        await init_database()
        
        logger.info("Bot ishga tushirilmoqda...")
        
        # Bot ma'lumotlarini olish
        bot_info = await bot.get_me()
        logger.info(f"Bot @{bot_info.username} ishga tushdi")
        
        # Polling boshlanishi
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Bot ishga tushishda xatolik: {e}")
    finally:
        await bot.session.close()
        await payment_manager.close_all_sessions()

if __name__ == "__main__":
    asyncio.run(main())

"""
Admin panel funksiyalari
"""

import json
import asyncio
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
from io import BytesIO

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session, User, Court, Booking, Payment, Ticket, Settings
from database import BookingStatus, PaymentStatus, UserRole, TicketStatus
from config import Config
from localization import get_text
from keyboards import get_admin_main_keyboard, get_back_keyboard, get_pagination_keyboard
from utils import create_excel_report, get_uzbekistan_time, format_currency

admin_router = Router()

class AdminStates(StatesGroup):
    main_menu = State()
    viewing_bookings = State()
    viewing_users = State()
    qr_checking = State()
    court_management = State()
    reports_menu = State()
    settings_menu = State()

@admin_router.message(Command("admin"))
async def admin_panel_handler(message: Message, state: FSMContext):
    """Admin panel asosiy sahifa"""
    async with async_session() as session:
        # Foydalanuvchini tekshirish
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user or user.role not in [UserRole.ADMIN, UserRole.OWNER, UserRole.MANAGER]:
            await message.answer("❌ Sizda admin huquqlari yo'q!")
            return
        
        lang = user.language
        await message.answer(
            get_text("admin_panel", lang),
            reply_markup=get_admin_main_keyboard(lang)
        )
        await state.set_state(AdminStates.main_menu)

@admin_router.callback_query(F.data == "admin:bookings", AdminStates.main_menu)
async def admin_bookings_handler(callback: CallbackQuery, state: FSMContext):
    """Bronlarni boshqarish"""
    async with async_session() as session:
        user = await get_admin_user(callback.from_user.id, session)
        if not user:
            return
        
        lang = user.language
        
        # Bugungi bronlar
        today = get_uzbekistan_time().date()
        result = await session.execute(
            select(Booking, Court, User).join(Court).join(User).where(
                Booking.booking_date == today
            ).order_by(Booking.start_time)
        )
        
        bookings_data = result.all()
        
        if not bookings_data:
            await callback.message.edit_text(
                "📊 Bugun bronlar yo'q",
                reply_markup=get_back_keyboard("back:admin", lang)
            )
            return
        
        # Bronlar ro'yxatini yaratish
        bookings_text = "📊 Bugungi bronlar:\n\n"
        for booking, court, booking_user in bookings_data:
            status_emoji = get_booking_status_emoji(booking.status.value)
            bookings_text += f"{status_emoji} {booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')} | {court.name}\n"
            bookings_text += f"👤 {booking_user.first_name} {booking_user.last_name or ''}\n"
            bookings_text += f"💰 {format_currency(booking.final_amount)}\n\n"
        
        await callback.message.edit_text(
            bookings_text,
            reply_markup=get_admin_bookings_keyboard(lang)
        )
        await state.set_state(AdminStates.viewing_bookings)

def get_admin_bookings_keyboard(lang: str = "uz"):
    """Admin bronlar klaviaturasi"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📅 Sana bo'yicha", callback_data="bookings:by_date"),
        InlineKeyboardButton(text="🏟 Kort bo'yicha", callback_data="bookings:by_court")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Mijoz bo'yicha", callback_data="bookings:by_user"),
        InlineKeyboardButton(text="📊 Holat bo'yicha", callback_data="bookings:by_status")
    )
    builder.row(
        InlineKeyboardButton(text="📈 Statistika", callback_data="bookings:stats"),
        InlineKeyboardButton(text="📋 Eksport", callback_data="bookings:export")
    )
    builder.row(
        InlineKeyboardButton(text=get_text("back", lang), callback_data="back:admin")
    )
    
    return builder.as_markup()

@admin_router.callback_query(F.data == "admin:users", AdminStates.main_menu)
async def admin_users_handler(callback: CallbackQuery, state: FSMContext):
    """Foydalanuvchilarni boshqarish"""
    async with async_session() as session:
        user = await get_admin_user(callback.from_user.id, session)
        if not user:
            return
        
        lang = user.language
        
        # Foydalanuvchilar statistikasi
        total_users = await session.execute(select(func.count(User.id)))
        total_users = total_users.scalar()
        
        active_users = await session.execute(
            select(func.count(User.id)).where(User.is_blocked == False)
        )
        active_users = active_users.scalar()
        
        vip_users = await session.execute(
            select(func.count(User.id)).where(User.is_vip == True)
        )
        vip_users = vip_users.scalar()
        
        # Bugun ro'yxatdan o'tganlar
        today = get_uzbekistan_time().date()
        today_users = await session.execute(
            select(func.count(User.id)).where(
                func.date(User.created_at) == today
            )
        )
        today_users = today_users.scalar()
        
        stats_text = f"""
👥 Foydalanuvchilar statistikasi:

📊 Jami: {total_users}
✅ Faol: {active_users}
⭐ VIP: {vip_users}
🆕 Bugun qo'shilgan: {today_users}
🚫 Bloklangan: {total_users - active_users}
        """
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_admin_users_keyboard(lang)
        )
        await state.set_state(AdminStates.viewing_users)

def get_admin_users_keyboard(lang: str = "uz"):
    """Admin foydalanuvchilar klaviaturasi"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔍 Qidirish", callback_data="users:search"),
        InlineKeyboardButton(text="⭐ VIP qilish", callback_data="users:make_vip")
    )
    builder.row(
        InlineKeyboardButton(text="🚫 Bloklash", callback_data="users:block"),
        InlineKeyboardButton(text="✅ Blokni ochish", callback_data="users:unblock")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Ro'yxat", callback_data="users:list"),
        InlineKeyboardButton(text="📊 Hisobot", callback_data="users:report")
    )
    builder.row(
        InlineKeyboardButton(text=get_text("back", lang), callback_data="back:admin")
    )
    
    return builder.as_markup()

@admin_router.callback_query(F.data == "admin:courts", AdminStates.main_menu)
async def admin_courts_handler(callback: CallbackQuery, state: FSMContext):
    """Kortlarni boshqarish"""
    async with async_session() as session:
        user = await get_admin_user(callback.from_user.id, session)
        if not user:
            return
        
        lang = user.language
        
        # Kortlar ro'yxati
        result = await session.execute(
            select(Court).order_by(Court.id)
        )
        courts = result.scalars().all()
        
        courts_text = "🏟 Kortlar ro'yxati:\n\n"
        for court in courts:
            status = "✅" if court.is_active else "❌"
            court_type = "🏢" if court.is_indoor else "🌤"
            
            courts_text += f"{status} {court_type} {court.name}\n"
            courts_text += f"💰 Peak: {format_currency(court.hourly_rate_peak)}\n"
            courts_text += f"💰 Off-peak: {format_currency(court.hourly_rate_offpeak)}\n\n"
        
        await callback.message.edit_text(
            courts_text,
            reply_markup=get_admin_courts_keyboard(lang)
        )
        await state.set_state(AdminStates.court_management)

def get_admin_courts_keyboard(lang: str = "uz"):
    """Admin kortlar klaviaturasi"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="➕ Kort qo'shish", callback_data="courts:add"),
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="courts:edit")
    )
    builder.row(
        InlineKeyboardButton(text="🔧 Ta'mirlash", callback_data="courts:maintenance"),
        InlineKeyboardButton(text="💰 Narxlar", callback_data="courts:prices")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Statistika", callback_data="courts:stats"),
        InlineKeyboardButton(text="🗓 Jadval", callback_data="courts:schedule")
    )
    builder.row(
        InlineKeyboardButton(text=get_text("back", lang), callback_data="back:admin")
    )
    
    return builder.as_markup()

@admin_router.callback_query(F.data == "admin:reports", AdminStates.main_menu)
async def admin_reports_handler(callback: CallbackQuery, state: FSMContext):
    """Hisobotlar"""
    async with async_session() as session:
        user = await get_admin_user(callback.from_user.id, session)
        if not user:
            return
        
        lang = user.language
        
        await callback.message.edit_text(
            "📈 Hisobotlar bo'limi",
            reply_markup=get_admin_reports_keyboard(lang)
        )
        await state.set_state(AdminStates.reports_menu)

def get_admin_reports_keyboard(lang: str = "uz"):
    """Admin hisobotlar klaviaturasi"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📊 Kunlik", callback_data="reports:daily"),
        InlineKeyboardButton(text="📅 Haftalik", callback_data="reports:weekly")
    )
    builder.row(
        InlineKeyboardButton(text="🗓 Oylik", callback_data="reports:monthly"),
        InlineKeyboardButton(text="📆 Yillik", callback_data="reports:yearly")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Moliyaviy", callback_data="reports:financial"),
        InlineKeyboardButton(text="👥 Mijozlar", callback_data="reports:customers")
    )
    builder.row(
        InlineKeyboardButton(text="🏟 Kortlar", callback_data="reports:courts"),
        InlineKeyboardButton(text="📋 Barchasi", callback_data="reports:full")
    )
    builder.row(
        InlineKeyboardButton(text=get_text("back", lang), callback_data="back:admin")
    )
    
    return builder.as_markup()

@admin_router.callback_query(F.data.startswith("reports:"))
async def generate_report_handler(callback: CallbackQuery, state: FSMContext):
    """Hisobot yaratish"""
    report_type = callback.data.split(":")[1]
    
    async with async_session() as session:
        user = await get_admin_user(callback.from_user.id, session)
        if not user:
            return
        
        lang = user.language
        
        await callback.answer("📊 Hisobot tayyorlanmoqda...")
        
        try:
            report_data = await generate_report(session, report_type)
            
            if report_data['format'] == 'text':
                await callback.message.edit_text(
                    report_data['content'],
                    reply_markup=get_back_keyboard("back:admin_reports", lang)
                )
            elif report_data['format'] == 'excel':
                # Excel faylini yuborish
                file_buffer = BytesIO()
                file_buffer.write(report_data['content'])
                file_buffer.seek(0)
                
                file_name = f"hisobot_{report_type}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                document = BufferedInputFile(file_buffer.getvalue(), filename=file_name)
                
                await callback.message.answer_document(
                    document=document,
                    caption=f"📊 {report_data['title']}"
                )
                
        except Exception as e:
            await callback.message.edit_text(
                f"❌ Hisobot yaratishda xatolik: {str(e)}",
                reply_markup=get_back_keyboard("back:admin_reports", lang)
            )

async def generate_report(session: AsyncSession, report_type: str) -> Dict:
    """Hisobot yaratish"""
    now = get_uzbekistan_time()
    
    if report_type == "daily":
        # Kunlik hisobot
        today = now.date()
        result = await session.execute(
            select(
                func.count(Booking.id).label('total_bookings'),
                func.sum(Booking.final_amount).label('total_revenue'),
                func.count(func.distinct(Booking.user_id)).label('unique_customers')
            ).where(
                and_(
                    Booking.booking_date == today,
                    Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PAID])
                )
            )
        )
        stats = result.first()
        
        content = f"""
📊 Kunlik hisobot - {today.strftime('%d.%m.%Y')}

🎾 Bronlar: {stats.total_bookings or 0}
💰 Daromad: {format_currency(stats.total_revenue or 0)}
👥 Mijozlar: {stats.unique_customers or 0}
        """
        
        return {
            'format': 'text',
            'content': content,
            'title': 'Kunlik hisobot'
        }
    
    elif report_type == "monthly":
        # Oylik hisobot (Excel)
        start_date = now.replace(day=1).date()
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        result = await session.execute(
            select(Booking, Court, User).join(Court).join(User).where(
                and_(
                    Booking.booking_date >= start_date,
                    Booking.booking_date <= end_date,
                    Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PAID])
                )
            ).order_by(Booking.booking_date, Booking.start_time)
        )
        
        bookings_data = result.all()
        
        # Excel uchun ma'lumotlar
        excel_data = []
        headers = ['Sana', 'Vaqt', 'Kort', 'Mijoz', 'Telefon', 'Narx', 'Holat']
        
        for booking, court, booking_user in bookings_data:
            excel_data.append({
                'Sana': booking.booking_date.strftime('%d.%m.%Y'),
                'Vaqt': f"{booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')}",
                'Kort': court.name,
                'Mijoz': f"{booking_user.first_name} {booking_user.last_name or ''}".strip(),
                'Telefon': booking_user.phone_number,
                'Narx': booking.final_amount,
                'Holat': booking.status.value
            })
        
        # Excel fayl yaratish
        file_path = f"/tmp/monthly_report_{now.strftime('%Y%m')}.xlsx"
        create_excel_report(excel_data, headers, file_path)
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        return {
            'format': 'excel',
            'content': content,
            'title': f'Oylik hisobot - {now.strftime("%m.%Y")}'
        }
    
    # Boshqa hisobot turlari...
    return {
        'format': 'text',
        'content': 'Hisobot mavjud emas',
        'title': 'Xatolik'
    }

@admin_router.message(F.photo, AdminStates.qr_checking)
async def qr_check_handler(message: Message, state: FSMContext):
    """QR kod tekshirish"""
    async with async_session() as session:
        user = await get_admin_user(message.from_user.id, session)
        if not user:
            return
        
        lang = user.language
        
        try:
            # QR kodni dekodlash (bu yerda qrcode kutubxonasi kerak)
            # Hozircha mock implementation
            
            # Faraz qilamiz QR kod to'g'ri dekodlandi
            qr_data = {
                'ticket_id': 'TNS-20241201-CRT1-ABCD',
                'booking_id': 123,
                'user_id': 456
            }
            
            # Biletni database dan tekshirish
            result = await session.execute(
                select(Ticket, Booking, Court, User).join(Booking).join(Court).join(User).where(
                    Ticket.ticket_id == qr_data['ticket_id']
                )
            )
            
            ticket_data = result.first()
            
            if not ticket_data:
                await message.answer("❌ Bilet topilmadi!")
                return
            
            ticket, booking, court, ticket_user = ticket_data
            
            if ticket.status == TicketStatus.USED:
                await message.answer(
                    f"⚠️ Bilet allaqachon foydalanilgan!\n"
                    f"Foydalanilgan vaqt: {ticket.used_at.strftime('%d.%m.%Y %H:%M')}"
                )
                return
            
            if ticket.status != TicketStatus.ACTIVE:
                await message.answer(f"❌ Bilet holati: {ticket.status.value}")
                return
            
            # Vaqtni tekshirish
            now = get_uzbekistan_time()
            booking_time = booking.start_time
            
            # Check-in oralig'i (1 soat oldin va 15 daqiqa keyin)
            checkin_start = booking_time - timedelta(hours=1)
            checkin_end = booking_time + timedelta(minutes=15)
            
            if now < checkin_start:
                await message.answer(
                    f"⏰ Check-in vaqti hali kelmagan!\n"
                    f"Check-in: {checkin_start.strftime('%H:%M')} dan"
                )
                return
            
            if now > checkin_end:
                await message.answer(
                    f"⏰ Check-in vaqti o'tib ketgan!\n"
                    f"Bron vaqti: {booking_time.strftime('%H:%M')}"
                )
                return
            
            # Biletni foydalanilgan deb belgilash
            ticket.status = TicketStatus.USED
            ticket.used_at = now
            ticket.checked_in_by = user.id
            
            await session.commit()
            
            success_text = f"""
✅ Bilet muvaffaqiyatli tekshirildi!

🎫 Bilet ID: {ticket.ticket_id}
👤 Mijoz: {ticket_user.first_name} {ticket_user.last_name or ''}
📱 Telefon: {ticket_user.phone_number}
🏟 Kort: {court.name}
📅 Sana: {booking.booking_date.strftime('%d.%m.%Y')}
⏰ Vaqt: {booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')}
💰 Narx: {format_currency(booking.final_amount)}

✅ Check-in: {now.strftime('%H:%M')}
            """
            
            await message.answer(success_text)
            
        except Exception as e:
            await message.answer(f"❌ QR kod tekshirishda xatolik: {str(e)}")

async def get_admin_user(telegram_id: int, session: AsyncSession) -> Optional[User]:
    """Admin foydalanuvchini olish"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or user.role not in [UserRole.ADMIN, UserRole.OWNER, UserRole.MANAGER]:
        return None
    
    return user

def get_booking_status_emoji(status: str) -> str:
    """Bron holati uchun emoji"""
    status_emojis = {
        'pending': '⏳',
        'hold': '🔒',
        'paid': '💳',
        'confirmed': '✅',
        'cancelled': '❌',
        'completed': '✅',
        'no_show': '🚫'
    }
    return status_emojis.get(status, '❓')

# Back button handlers
@admin_router.callback_query(F.data == "back:admin")
async def back_to_admin_handler(callback: CallbackQuery, state: FSMContext):
    """Admin panelga qaytish"""
    async with async_session() as session:
        user = await get_admin_user(callback.from_user.id, session)
        if not user:
            return
        
        lang = user.language
        await callback.message.edit_text(
            get_text("admin_panel", lang),
            reply_markup=get_admin_main_keyboard(lang)
        )
        await state.set_state(AdminStates.main_menu)

@admin_router.callback_query(F.data == "back:admin_reports")
async def back_to_admin_reports_handler(callback: CallbackQuery, state: FSMContext):
    """Admin hisobotlarga qaytish"""
    await admin_reports_handler(callback, state)

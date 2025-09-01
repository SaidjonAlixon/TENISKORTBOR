"""
Telegram bot uchun klaviaturalar
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from datetime import datetime, timedelta
from typing import List, Optional
from localization import get_text, get_available_languages
import calendar

def get_main_menu_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Asosiy menyu klaviaturasi"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text=get_text("book_court", lang)),
        KeyboardButton(text=get_text("my_bookings", lang))
    )
    builder.row(
        KeyboardButton(text=get_text("my_profile", lang)),
        KeyboardButton(text=get_text("rules", lang))
    )
    builder.row(
        KeyboardButton(text=get_text("help", lang)),
        KeyboardButton(text=get_text("language", lang))
    )
    
    return builder.as_markup(resize_keyboard=True)

def get_contact_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Telefon raqam ulashish klaviaturasi"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(
            text=get_text("share_contact", lang),
            request_contact=True
        )
    )
    
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Til tanlash klaviaturasi"""
    builder = InlineKeyboardBuilder()
    
    languages = get_available_languages()
    for code, name in languages.items():
        builder.row(
            InlineKeyboardButton(
                text=name,
                callback_data=f"lang:{code}"
            )
        )
    
    return builder.as_markup()

def get_calendar_keyboard(year: int, month: int, lang: str = "uz", 
                         booked_dates: List[str] = None) -> InlineKeyboardMarkup:
    """Kalendar klaviaturasi"""
    builder = InlineKeyboardBuilder()
    
    if booked_dates is None:
        booked_dates = []
    
    # Oy nomi va yil
    from localization import TEXTS
    month_names = TEXTS[lang]["months"] if lang in TEXTS else TEXTS["uz"]["months"]
    month_name = month_names[month - 1] if month <= len(month_names) else str(month)
    
    # Oy navigatsiyasi
    builder.row(
        InlineKeyboardButton(text="◀️", callback_data=f"cal:prev:{year}:{month}"),
        InlineKeyboardButton(text=f"{month_name} {year}", callback_data="cal:ignore"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal:next:{year}:{month}")
    )
    
    # Hafta kunlari
    weekdays = TEXTS[lang]["weekdays"] if lang in TEXTS else TEXTS["uz"]["weekdays"]
    weekday_buttons = [InlineKeyboardButton(text=day, callback_data="cal:ignore") for day in weekdays]
    builder.row(*weekday_buttons)
    
    # Kunlar
    cal = calendar.monthcalendar(year, month)
    today = datetime.now().date()
    
    for week in cal:
        week_buttons = []
        for day in week:
            if day == 0:
                week_buttons.append(InlineKeyboardButton(text=" ", callback_data="cal:ignore"))
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                # O'tmish sanalarni bloklash
                if date_obj < today:
                    week_buttons.append(InlineKeyboardButton(text="❌", callback_data="cal:ignore"))
                # Band sanalar
                elif date_str in booked_dates:
                    week_buttons.append(InlineKeyboardButton(text=f"🚫{day}", callback_data="cal:ignore"))
                # Bo'sh sanalar
                else:
                    week_buttons.append(InlineKeyboardButton(
                        text=str(day), 
                        callback_data=f"date:{date_str}"
                    ))
        
        builder.row(*week_buttons)
    
    # Bugun tugmasi
    builder.row(
        InlineKeyboardButton(text=get_text("today", lang), callback_data=f"date:{today}")
    )
    
    # Orqaga tugmasi
    builder.row(
        InlineKeyboardButton(text=get_text("back", lang), callback_data="back:main")
    )
    
    return builder.as_markup()

def get_time_slots_keyboard(available_slots: List[dict], lang: str = "uz") -> InlineKeyboardMarkup:
    """Vaqt slotlari klaviaturasi"""
    builder = InlineKeyboardBuilder()
    
    if not available_slots:
        builder.row(
            InlineKeyboardButton(
                text=get_text("no_available_slots", lang),
                callback_data="time:none"
            )
        )
    else:
        # Slotlarni 3 tadan qilib qo'yish
        for i in range(0, len(available_slots), 3):
            row_slots = available_slots[i:i+3]
            buttons = []
            
            for slot in row_slots:
                start_time_str = slot['start_time'].strftime('%H:%M')
                end_time_str = slot['end_time'].strftime('%H:%M')
                time_text = f"{start_time_str}-{end_time_str}"
                
                if slot.get('is_peak'):
                    time_text += " 🔥"
                
                # Callback data'ni to'g'ri formatda yaratish
                # "10:00" -> "time_10_00" (: belgisi muammo qilishi mumkin)
                safe_time = start_time_str.replace(":", "_")
                
                buttons.append(
                    InlineKeyboardButton(
                        text=time_text,
                        callback_data=f"time_{safe_time}"
                    )
                )
            
            builder.row(*buttons)
    
    # Orqaga tugmasi
    builder.row(
        InlineKeyboardButton(text=get_text("back", lang), callback_data="back:date")
    )
    
    return builder.as_markup()

def get_courts_keyboard(courts: List[dict], lang: str = "uz") -> InlineKeyboardMarkup:
    """Kortlar klaviaturasi"""
    builder = InlineKeyboardBuilder()
    
    for court in courts:
        court_name = court['name']
        if court.get('is_indoor'):
            court_name += " 🏢"
        
        builder.row(
            InlineKeyboardButton(
                text=court_name,
                callback_data=f"court:{court['id']}"
            )
        )
    
    # Orqaga tugmasi
    builder.row(
        InlineKeyboardButton(text=get_text("back", lang), callback_data="back:main")
    )
    
    return builder.as_markup()

def get_booking_confirmation_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Bron tasdiqlash klaviaturasi"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("confirm_booking", lang),
            callback_data="booking:confirm"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("cancel_booking", lang),
            callback_data="booking:cancel"
        )
    )
    
    return builder.as_markup()

def get_payment_methods_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """To'lov usullari klaviaturasi"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("payment_payme", lang),
            callback_data="payment:payme"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("payment_click", lang),
            callback_data="payment:click"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("payment_uzum", lang),
            callback_data="payment:uzum"
        )
    )
    
    # To'lov qilindi tugmasi
    builder.row(
        InlineKeyboardButton(
            text="✅ To'lov qilindi",
            callback_data="payment:done"
        )
    )
    
    # Orqaga tugmasi
    builder.row(
        InlineKeyboardButton(text=get_text("back", lang), callback_data="back:booking")
    )
    
    return builder.as_markup()

def get_my_bookings_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Buyurtmalarim klaviaturasi"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("active_bookings", lang),
            callback_data="bookings:active"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("booking_history", lang),
            callback_data="bookings:history"
        )
    )
    
    # Orqaga tugmasi
    builder.row(
        InlineKeyboardButton(text=get_text("back", lang), callback_data="back:main")
    )
    
    return builder.as_markup()

def get_booking_actions_keyboard(booking_id: int, can_cancel: bool = True, 
                                lang: str = "uz") -> InlineKeyboardMarkup:
    """Bron amallar klaviaturasi"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("show_ticket", lang),
            callback_data=f"ticket:show:{booking_id}"
        )
    )
    
    if can_cancel:
        builder.row(
            InlineKeyboardButton(
                text=get_text("cancel_booking_btn", lang),
                callback_data=f"booking:cancel:{booking_id}"
            )
        )
    
    # Orqaga tugmasi
    builder.row(
        InlineKeyboardButton(text=get_text("back", lang), callback_data="back:bookings")
    )
    
    return builder.as_markup()

def get_profile_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Profil klaviaturasi"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("edit_profile", lang),
            callback_data="profile:edit"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("change_language", lang),
            callback_data="profile:language"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("toggle_notifications", lang),
            callback_data="profile:notifications"
        )
    )
    
    # Orqaga tugmasi
    builder.row(
        InlineKeyboardButton(text=get_text("back", lang), callback_data="back:main")
    )
    
    return builder.as_markup()

def get_admin_main_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Admin asosiy klaviaturasi"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("admin_bookings", lang),
            callback_data="admin:bookings"
        ),
        InlineKeyboardButton(
            text=get_text("admin_users", lang),
            callback_data="admin:users"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("admin_courts", lang),
            callback_data="admin:courts"
        ),
        InlineKeyboardButton(
            text=get_text("admin_reports", lang),
            callback_data="admin:reports"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("admin_settings", lang),
            callback_data="admin:settings"
        )
    )
    
    return builder.as_markup()

def get_pagination_keyboard(current_page: int, total_pages: int, 
                           callback_prefix: str, lang: str = "uz") -> InlineKeyboardMarkup:
    """Sahifalash klaviaturasi"""
    builder = InlineKeyboardBuilder()
    
    buttons = []
    
    # Oldingi sahifa
    if current_page > 1:
        buttons.append(
            InlineKeyboardButton(
                text=get_text("previous", lang),
                callback_data=f"{callback_prefix}:page:{current_page - 1}"
            )
        )
    
    # Sahifa raqami
    buttons.append(
        InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data="pagination:ignore"
        )
    )
    
    # Keyingi sahifa
    if current_page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text=get_text("next", lang),
                callback_data=f"{callback_prefix}:page:{current_page + 1}"
            )
        )
    
    if buttons:
        builder.row(*buttons)
    
    return builder.as_markup()

def get_back_keyboard(callback_data: str, lang: str = "uz") -> InlineKeyboardMarkup:
    """Oddiy orqaga tugmasi"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("back", lang),
            callback_data=callback_data
        )
    )
    
    return builder.as_markup()

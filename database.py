import os
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, DateTime, Boolean, Text, Float, ForeignKey, Enum
from datetime import datetime
from typing import Optional, List
import enum
from dotenv import load_dotenv

load_dotenv()

# Database URL - PostgreSQL
from config import Config
DATABASE_URL = Config.get_database_url()

# SQLAlchemy engine va session
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# Enum'lar
class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MANAGER = "manager"
    GUARD = "guard"
    OWNER = "owner"

class BookingStatus(enum.Enum):
    PENDING = "pending"
    HOLD = "hold"
    PAID = "paid"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"

class PaymentStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentMethod(enum.Enum):
    PAYME = "payme"
    CLICK = "click"
    UZUM = "uzum"
    CASH = "cash"

class TicketStatus(enum.Enum):
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

# Models
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(5), default="uz")
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bookings: Mapped[List["Booking"]] = relationship("Booking", back_populates="user")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="user")

class Court(Base):
    __tablename__ = "courts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_indoor: Mapped[bool] = mapped_column(Boolean, default=False)
    hourly_rate_peak: Mapped[float] = mapped_column(Float, nullable=False)
    hourly_rate_offpeak: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    bookings: Mapped[List["Booking"]] = relationship("Booking", back_populates="court")
    maintenance_schedules: Mapped[List["MaintenanceSchedule"]] = relationship("MaintenanceSchedule", back_populates="court")

class Booking(Base):
    __tablename__ = "bookings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    court_id: Mapped[int] = mapped_column(Integer, ForeignKey("courts.id"), nullable=False)
    booking_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_hours: Mapped[float] = mapped_column(Float, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    service_fee: Mapped[float] = mapped_column(Float, default=0.0)
    final_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.PENDING)
    is_peak_time: Mapped[bool] = mapped_column(Boolean, default=False)
    is_weekend: Mapped[bool] = mapped_column(Boolean, default=False)
    promo_code: Mapped[Optional[str]] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    hold_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="bookings")
    court: Mapped["Court"] = relationship("Court", back_populates="bookings")
    payment: Mapped[Optional["Payment"]] = relationship("Payment", back_populates="booking", uselist=False)
    ticket: Mapped[Optional["Ticket"]] = relationship("Ticket", back_populates="booking", uselist=False)

class Payment(Base):
    __tablename__ = "payments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    external_payment_id: Mapped[Optional[str]] = mapped_column(String(255))
    transaction_id: Mapped[Optional[str]] = mapped_column(String(255))
    payment_url: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    booking: Mapped["Booking"] = relationship("Booking", back_populates="payment")
    user: Mapped["User"] = relationship("User", back_populates="payments")

class Ticket(Base):
    __tablename__ = "tickets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    ticket_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    qr_code_data: Mapped[str] = mapped_column(Text, nullable=False)
    qr_code_path: Mapped[Optional[str]] = mapped_column(String(255))
    pdf_path: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus), default=TicketStatus.ACTIVE)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    checked_in_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    booking: Mapped["Booking"] = relationship("Booking", back_populates="ticket")

class PromoCode(Base):
    __tablename__ = "promo_codes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)  # percentage, fixed
    discount_value: Mapped[float] = mapped_column(Float, nullable=False)
    max_uses: Mapped[Optional[int]] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MaintenanceSchedule(Base):
    __tablename__ = "maintenance_schedules"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    court_id: Mapped[int] = mapped_column(Integer, ForeignKey("courts.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    court: Mapped["Court"] = relationship("Court", back_populates="maintenance_schedules")

class Settings(Base):
    __tablename__ = "settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database funksiyalari
async def create_tables():
    """Ma'lumotlar bazasi jadvallarini yaratish"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session():
    """Database session olish"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_database():
    """Ma'lumotlar bazasini boshlang'ich ma'lumotlar bilan to'ldirish"""
    await create_tables()
    
    async with async_session() as session:
        # Standart kortlarni yaratish
        from sqlalchemy import text
        existing_courts = await session.execute(
            text("SELECT COUNT(*) FROM courts")
        )
        if existing_courts.scalar() == 0:
            courts = [
                Court(
                    name="Kort 1",
                    description="Asosiy tennis korti",
                    hourly_rate_peak=50000,
                    hourly_rate_offpeak=30000,
                    is_indoor=False
                ),
                Court(
                    name="Kort 2", 
                    description="Ikkinchi tennis korti",
                    hourly_rate_peak=50000,
                    hourly_rate_offpeak=30000,
                    is_indoor=False
                ),
                Court(
                    name="Yopiq zal",
                    description="Yopiq tennis zali",
                    hourly_rate_peak=70000,
                    hourly_rate_offpeak=50000,
                    is_indoor=True
                )
            ]
            
            for court in courts:
                session.add(court)
            
            await session.commit()
            
        # Standart sozlamalarni yaratish
        settings = [
            Settings(key="peak_start_hour", value="18", description="Peak vaqt boshlanishi"),
            Settings(key="peak_end_hour", value="22", description="Peak vaqt tugashi"),
            Settings(key="court_open_hour", value="6", description="Kort ochilish vaqti"),
            Settings(key="court_close_hour", value="23", description="Kort yopilish vaqti"),
            Settings(key="weekend_coefficient", value="1.2", description="Dam olish kunlari koeffitsienti"),
            Settings(key="vip_discount", value="0.15", description="VIP chegirma"),
            Settings(key="service_fee", value="0.03", description="Xizmat haqi"),
            Settings(key="booking_hold_minutes", value="5", description="Bron ushlab turish vaqti (daqiqa)"),
            Settings(key="cancellation_hours", value="6", description="Bekor qilish uchun minimal vaqt (soat)"),
        ]
        
        for setting in settings:
            from sqlalchemy import select
            existing = await session.execute(
                select(Settings).where(Settings.key == setting.key)
            )
            if not existing.scalar_one_or_none():
                session.add(setting)
        
        await session.commit()

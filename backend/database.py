from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, Index
from datetime import datetime
from typing import Optional
import os
from utils import now_argentina

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./database.sqlite")
print(f"🗄️ Database URL: {DATABASE_URL}")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base class for models
class Base(DeclarativeBase):
    pass

# ============================================
# MODELOS
# ============================================

class Device(Base):
    __tablename__ = "devices"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(100))
    location: Mapped[Optional[str]] = mapped_column(String(100))
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Device(device_id='{self.device_id}', name='{self.name}')>"


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=now_argentina, index=True)
    
    __table_args__ = (
        Index('idx_device_timestamp', 'device_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<Measurement(device_id='{self.device_id}', temp={self.temperature}, hum={self.humidity})>"


class MeasurementAverage(Base):
    __tablename__ = "measurement_averages"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    avg_temperature: Mapped[float] = mapped_column(Float, nullable=False)
    avg_humidity: Mapped[float] = mapped_column(Float, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer)
    period_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime)
    
    def __repr__(self):
        return f"<MeasurementAverage(device_id='{self.device_id}', avg_temp={self.avg_temperature})>"


class AcEvent(Base):
    __tablename__ = "ac_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # 'on' or 'off'
    triggered_by: Mapped[Optional[str]] = mapped_column(String(50))  # 'manual', 'scheduled', 'automation'
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=now_argentina, index=True)
    
    def __repr__(self):
        return f"<AcEvent(device_id='{self.device_id}', action='{self.action}')>"


class Schedule(Base):
    __tablename__ = "schedules"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # 'on' or 'off'
    days_of_week: Mapped[Optional[str]] = mapped_column(Text)  # JSON: [1,2,3,4,5]
    time: Mapped[str] = mapped_column(String(10))  # "08:00"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Schedule(device_id='{self.device_id}', name='{self.name}', time='{self.time}')>"


class LedConfig(Base):
    __tablename__ = "led_config"

    device_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    mode: Mapped[str] = mapped_column(String(20), default='manual')  # 'manual', 'temperature', 'off'
    manual_color: Mapped[Optional[str]] = mapped_column(Text)  # JSON: {"r": 255, "g": 0, "b": 0}

    def __repr__(self):
        return f"<LedConfig(device_id='{self.device_id}', mode='{self.mode}')>"


class SleepTimer(Base):
    __tablename__ = "sleep_timers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # 'on' or 'off'
    execute_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_argentina)
    is_executed: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self):
        return f"<SleepTimer(device_id='{self.device_id}', action='{self.action}', execute_at='{self.execute_at}')>"


class AlertSettings(Base):
    __tablename__ = "alert_settings"

    device_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    threshold_high: Mapped[Optional[float]] = mapped_column(Float)  # Alert if temperature > threshold_high
    threshold_low: Mapped[Optional[float]] = mapped_column(Float)   # Alert if temperature < threshold_low
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_alert_sent: Mapped[Optional[datetime]] = mapped_column(DateTime)  # To avoid spam

    def __repr__(self):
        return f"<AlertSettings(device_id='{self.device_id}', high={self.threshold_high}, low={self.threshold_low})>"


# ============================================
# DATABASE FUNCTIONS
# ============================================

async def init_db():
    """Initialize database tables"""
    try:
        print("🔄 Iniciando creación de tablas...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✓ Database initialized")

        # Verificar que las tablas se crearon
        from sqlalchemy import text
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = result.fetchall()
            print(f"📊 Tablas creadas: {[table[0] for table in tables]}")

    except Exception as e:
        print(f"✗ Error inicializando base de datos: {e}")
        import traceback
        traceback.print_exc()
        raise


async def get_session() -> AsyncSession:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        yield session
from sqlalchemy import Column, Integer, String, Float, DateTime, Index, UniqueConstraint ,BigInteger, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.sql import func
from database import Base, engine
from datetime import datetime
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class TeamUser(Base):
    """Stores team login credentials, administrative roles, and page access flags."""
    __tablename__ = "team_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(150), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="member")  # admin, supervisor, lineman, operator
    
    # Geographic scope (optional for role-based filtering)
    circle = Column(String(100), nullable=True)
    division = Column(String(100), nullable=True)
    sub_division = Column(String(100), nullable=True)
    section = Column(String(100), nullable=True)

    # Permission flags
    can_access_dc_entry = Column(Boolean, default=False)
    can_access_data_upload = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class LoadBooking(Base):
    __tablename__ = "load_bookings"

    id = Column(Integer, primary_key=True, index=True)
    vcr_no = Column(String(50), nullable=False, unique=True, index=True)
    scno = Column(String(50), nullable=False, index=True)
    inspection_date = Column(String(30), nullable=True)
    circle = Column(String(100), nullable=True, index=True)
    division = Column(String(100), nullable=True, index=True)
    sub_division = Column(String(100), nullable=True, index=True)
    section = Column(String(100), nullable=True, index=True)
    inspected_officer_name = Column(String(150), nullable=True, index=True)
    user_name = Column(String(200), nullable=True)
    address = Column(String(255), nullable=True)
    defect_name = Column(String(100), nullable=True)
    connected_category = Column(String(100), nullable=True)
    connected_load = Column(Float, default=0.0)
    fy = Column(String(20), nullable=True, index=True)
    qtr = Column(String(10), nullable=True)
    month = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    vcr_no = Column(String(50), nullable=False, index=True)
    scno = Column(String(50), nullable=False, index=True)
    pr_no = Column(String(100), nullable=False, unique=True, index=True)
    circle = Column(String(100), nullable=True, index=True)
    div = Column(String(100), nullable=True, index=True)
    sub_div = Column(String(100), nullable=True, index=True)
    section = Column(String(100), nullable=True, index=True)
    inspected_officer_name = Column(String(150), nullable=True)
    user_name = Column(String(200), nullable=True)
    status = Column(String(50), default="Open")
    theft_typ = Column(String(100), nullable=True)
    defect_name = Column(String(100), nullable=True)
    connected_categor = Column(String(100), nullable=True)
    amount_paid = Column(Float, default=0.0)
    collection_dat = Column(String(30), nullable=True)
    mode_of_paymen = Column(String(50), nullable=True)
    amount_collected_b = Column(String(150), nullable=True, index=True)
    fy = Column(String(20), nullable=True, index=True)
    qtr = Column(String(10), nullable=True)
    month = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Disconnection(Base):
    __tablename__ = "disconnections"

    id = Column(Integer, primary_key=True, index=True)
    vcr_no = Column(String(50), nullable=False, index=True)
    scno = Column(String(50), nullable=False, index=True)
    circle = Column(String(100), nullable=True, index=True)
    division = Column(String(100), nullable=True, index=True)
    sub_division = Column(String(100), nullable=True, index=True)
    section = Column(String(100), nullable=True, index=True)
    dc_date = Column(String(30), nullable=False)
    consumer_name = Column(String(200), nullable=True)
    address = Column(String(255), nullable=True)
    outstanding_amount = Column(Float, default=0.0)
    dc_type = Column(String(50), default="Temporary")
    meter_reading = Column(String(50), nullable=True)
    lineman_name = Column(String(150), nullable=True)
    supervising_officer = Column(String(150), nullable=True, index=True)
    remarks = Column(String(255), nullable=True)
    fy = Column(String(20), nullable=True, index=True)
    qtr = Column(String(10), nullable=True)
    month = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Target(Base):
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True, index=True)
    fy = Column(String(20), nullable=False, index=True)
    entity_level = Column(String(50), nullable=False, index=True)  # Section, Sub-Division, Division, Circle
    entity_name = Column(String(150), nullable=False, index=True)
    circle = Column(String(100), nullable=True, index=True)
    division = Column(String(100), nullable=True, index=True)
    sub_division = Column(String(100), nullable=True, index=True)
    section = Column(String(100), nullable=True, index=True)
    target_load_kw = Column(Float, default=0.0)
    target_collection_amount = Column(Float, default=0.0)
    target_dc_count = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint('fy', 'entity_level', 'entity_name', name='uq_target_fy_level_entity'),
    )

class DisconnectingOfficer(Base):
    __tablename__ = "disconnecting_officers"

    id = Column(Integer, primary_key=True, index=True)
    circle = Column(String(100), nullable=False, index=True)
    officer_name = Column(String(150), nullable=False, index=True)
    designation = Column(String(100), nullable=True)  # e.g., Lineman, SDO, Junior Engineer
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('circle', 'officer_name', name='uq_circle_officer_name'),
    )

# Composite performance indexes
Index('idx_lb_agg', LoadBooking.circle, LoadBooking.division, LoadBooking.sub_division, LoadBooking.section, LoadBooking.fy, LoadBooking.month)
Index('idx_col_agg', Collection.circle, Collection.div, Collection.sub_div, Collection.section, Collection.fy, Collection.month)
Index('idx_dc_agg', Disconnection.circle, Disconnection.division, Disconnection.sub_division, Disconnection.section, Disconnection.fy, Disconnection.month)

Base.metadata.create_all(bind=engine)
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, Date
from sqlalchemy.orm import relationship
from app import db
import os
import qrcode

# Association tables
event_sponsor = db.Table('event_sponsor',
    db.Column('event_id', db.Integer, db.ForeignKey('events.id'), primary_key=True),
    db.Column('sponsor_id', db.Integer, db.ForeignKey('sponsors.id'), primary_key=True)
)

class Organizer(db.Model):
    __tablename__ = 'organizers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    phone = db.Column(db.String(20), nullable=False)
    logo = db.Column(db.String(255))  # Path to logo image
    website = db.Column(db.String(255))
    description = db.Column(db.Text)
    speciality = db.Column(db.String(100))
    contact_email = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    events = db.relationship('Event', backref='organizer', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'speciality': self.speciality,
            'description': self.description,
            'logo': self.logo,
            'website': self.website,
            'contact_email': self.contact_email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Sponsor(db.Model):
    __tablename__ = 'sponsors'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    logo = db.Column(db.String(255))  # Path to logo image
    website = db.Column(db.String(255))
    contact_email = db.Column(db.String(100))
    sponsorship_level = db.Column(db.String(50))  # e.g., "Gold", "Silver"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'logo': self.logo,
            'website': self.website,
            'contact_email': self.contact_email,
            'sponsorship_level': self.sponsorship_level
        }

class Venue(db.Model):
    __tablename__ = 'venues'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer)
    
    events = db.relationship('Event', backref='venue', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'capacity': self.capacity
        }

class Event(db.Model):
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'))
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('organizers.id'), nullable=False)
    image = db.Column(db.String(255))  # Path to event image
    category = db.Column(db.String(100))
    capacity = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    sponsors = db.relationship('Sponsor', secondary=event_sponsor, lazy='subquery',
                             backref=db.backref('events', lazy=True))
    ticket_types = db.relationship('TicketType', backref='event', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'venue_id': self.venue_id,
            'start_datetime': self.start_datetime.isoformat(),
            'end_datetime': self.end_datetime.isoformat(),
            'organizer_id': self.organizer_id,
            'image': self.image,
            'capacity': self.capacity,
            'category': self.category,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class TicketType(db.Model):
    __tablename__ = 'ticket_types'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity_available = db.Column(db.Integer, nullable=False)
    sales_start = db.Column(db.DateTime, nullable=False)
    sales_end = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'name': self.name,
            'price': self.price,
            'quantity_available': self.quantity_available,
            'sales_start': self.sales_start.isoformat(),
            'sales_end': self.sales_end.isoformat(),
            'description': self.description,
            'is_active': self.is_active
        }

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'organizer', 'customer'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    orders = db.relationship('Order', backref='user', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    customer_email = db.Column(db.String(100), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed, cancelled
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(20))
    billing_address = db.Column(db.Text)
    
    tickets = db.relationship('Ticket', backref='order', lazy=True)
    discounts = db.relationship('Discount', backref='order', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'customer_email': self.customer_email,
            'order_date': self.order_date.isoformat(),
            'total_amount': self.total_amount,
            'status': self.status,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'billing_address': self.billing_address
        }

class Discount(db.Model):
    __tablename__ = 'discounts'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_type = db.Column(db.String(20), nullable=False)  # 'percentage' or 'fixed'
    value = db.Column(db.Float, nullable=False)
    valid_from = db.Column(db.DateTime, nullable=False)
    valid_to = db.Column(db.DateTime, nullable=False)
    max_uses = db.Column(db.Integer)
    current_uses = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'discount_type': self.discount_type,
            'value': self.value,
            'valid_from': self.valid_from.isoformat(),
            'valid_to': self.valid_to.isoformat(),
            'max_uses': self.max_uses,
            'current_uses': self.current_uses,
            'is_active': self.is_active,
            'order_id': self.order_id
        }

class Ticket(db.Model):
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_type_id = db.Column(db.Integer, db.ForeignKey('ticket_types.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    attendee_name = db.Column(db.String(100), nullable=False)
    attendee_email = db.Column(db.String(100), nullable=False)
    unique_code = db.Column(db.String(50), unique=True, nullable=False)
    qr_code_path = db.Column(db.String(255))  # Path to QR code image
    is_redeemed = db.Column(db.Boolean, default=False)
    redemption_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    refund_request = db.relationship('RefundRequest', backref='ticket', uselist=False, lazy=True)
    
    def generate_qr_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.unique_code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        filename = f"qr_{self.unique_code}.png"
        img_path = os.path.join('static/qr_codes', filename)
        img.save(img_path)
        
        self.qr_code_path = img_path
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticket_type_id': self.ticket_type_id,
            'order_id': self.order_id,
            'attendee_name': self.attendee_name,
            'attendee_email': self.attendee_email,
            'unique_code': self.unique_code,
            'qr_code_path': self.qr_code_path,
            'is_redeemed': self.is_redeemed,
            'redemption_date': self.redemption_date.isoformat() if self.redemption_date else None,
            'created_at': self.created_at.isoformat()
        }

class RefundRequest(db.Model):
    __tablename__ = 'refund_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    processed_date = db.Column(db.DateTime)
    admin_notes = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'request_date': self.request_date.isoformat(),
            'reason': self.reason,
            'status': self.status,
            'processed_date': self.processed_date.isoformat() if self.processed_date else None,
            'admin_notes': self.admin_notes
        }
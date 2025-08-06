from ast import parse
from mailbox import Message
import uuid
from flask import Flask, jsonify, request, make_response,jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from config import Config
from sqlalchemy import func
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import BadSignature, URLSafeTimedSerializer

# Initialize serializer
serializer = URLSafeTimedSerializer(Config.SECRET_KEY)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app, supports_credentials=True, origins=['http://localhost:3000', 'https://tikiti-1-all3n0s-projects.vercel.app'])

# Import models after db initialization to avoid circular imports
from models import Management, Organizer, Event, Venue, Sponsor, TicketType, User, Order, Discount, Ticket, RefundRequest
#organizer dashboard
@app.route('/organizers/<int:organizer_id>/dashboard')
def organizer_dashboard(organizer_id):
    organizer = Organizer.query.get_or_404(organizer_id)

    # Get all events by this organizer
    events = Event.query.filter_by(organizer_id=organizer_id).all()
    event_ids = [event.id for event in events]

    # Total revenue from orders of those events
    total_revenue = db.session.query(func.coalesce(func.sum(Order.total_amount), 0))\
        .filter(Order.event_id.in_(event_ids)).scalar()

    # Total attendees (number of tickets sold)
    total_attendees = db.session.query(func.count(Ticket.id))\
        .join(Order).filter(Order.event_id.in_(event_ids)).scalar()

    # Average rating from all events
    average_rating = db.session.query(func.coalesce(func.avg(Event.rating), 0))\
        .filter(Event.organizer_id == organizer_id).scalar()

    # Get upcoming event for display
    today_event = Event.query.filter(
        Event.organizer_id == organizer_id,
        Event.start_datetime >= datetime.utcnow()
    ).order_by(Event.start_datetime).first()

    return jsonify({
        'organizer': {
            'id': organizer.id,
            'name': organizer.name,
            'email': organizer.email
        },
        'total_revenue': float(total_revenue),
        'total_attendees': total_attendees,
        'average_rating': round(average_rating, 1),
        'today_event': {
            'id': today_event.id,
            'title': today_event.title,
            'start_datetime': today_event.start_datetime.isoformat()
        } if today_event else None
    })
#upcoming events
@app.route('/organiser/<int:organiser_id>/upcoming', methods=['GET'])
def get_upcoming_events(organiser_id):
    now = datetime.utcnow()
    upcoming_events = Event.query.filter(
        Event.organizer_id == organiser_id,
        Event.start_datetime > now
    ).order_by(Event.start_datetime.asc()).all()

    upcoming_data = []
    for event in upcoming_events:
        orders = Order.query.filter_by(event_id=event.id, status='completed').all()
        total_attendees = sum(len(order.tickets) for order in orders)
        total_revenue = sum(order.total_amount for order in orders)

        event_data = {
            'id': event.id,
            'title': event.title,
            'start_datetime': event.start_datetime.isoformat(),
            'image': event.image,
            'status': 'Published' if event.is_active else 'Draft',
            'attendees': total_attendees,
            'revenue': total_revenue,
            'rating': round(event.rating, 1) if event.rating else 0.0
        }

        if event.venue_id:
            venue = Venue.query.get(event.venue_id)
            event_data['venue'] = venue.to_dict() if venue else None

        upcoming_data.append(event_data)

    return jsonify(upcoming_data), 200

#organizers
@app.route('/organizers')
def get_organizers():
    search = request.args.get('search', '', type=str).lower()
    min_events = request.args.get('min_events', 0, type=int)

    query = db.session.query(Organizer).outerjoin(Event).group_by(Organizer.id)

    if search:
        query = query.filter(
            func.lower(Organizer.name).like(f'%{search}%') |
            func.lower(Organizer.website).like(f'%{search}%')
        )

    organizers = query.all()

    result = []
    for organizer in organizers:
        event_count = len(organizer.events)
        if event_count >= min_events:
            result.append({
                'id': organizer.id,
                'name': organizer.name,
                'avatar': organizer.logo,
                'specialty': organizer.website,
                'eventsCount': event_count,
                'rating': 4.7  # placeholder
            })

    return jsonify(result)
@app.route('/organizers/<int:organizer_id>')
def get_organizer(organizer_id):
    # Get organizer with stats
    organizer_data = db.session.query(
        Organizer,
        func.count(Event.id).label('total_events'),
        func.sum(Event.capacity).label('total_capacity'),
        func.avg(Event.capacity).label('avg_attendance')
    ).join(Event, Organizer.id == Event.organizer_id
     ).filter(Organizer.id == organizer_id
     ).group_by(Organizer.id).first()

    if not organizer_data:
        return jsonify({'error': 'Organizer not found'}), 404

    organizer, total_events, total_capacity, avg_attendance = organizer_data

    # Get upcoming events
    upcoming_events = Event.query.filter(
        Event.organizer_id == organizer_id,
        Event.end_datetime >= datetime.now(),
        Event.is_active == True
    ).join(Venue).order_by(Event.start_datetime.asc()).all()

    # Get past events count
    past_events_count = Event.query.filter(
        Event.organizer_id == organizer_id,
        Event.end_datetime < datetime.now(),
        Event.is_active == True
    ).count()

    # Build response
    response = {
        'organizer': organizer.to_dict(),
        'stats': {
            'total_events': total_events,
            'past_events': past_events_count,
            'upcoming_events': len(upcoming_events),
            'total_capacity': total_capacity or 0,
            'avg_attendance': round(float(avg_attendance or 0), 2),
            'rating': 4.5  # Placeholder - you might want to calculate actual ratings
        },
        'upcoming_events': [{
            'id': event.id,
            'title': event.title,
            'start_datetime': event.start_datetime.isoformat(),
            'end_datetime': event.end_datetime.isoformat(),
            'venue': event.venue.to_dict() if event.venue else None,
            'image': event.image,
            'category': event.category,
            'capacity': event.capacity,
            'status': event.status
        } for event in upcoming_events],
        'contact': {
            'email': organizer.contact_email,
            'phone': organizer.phone,
            'website': organizer.website
        }
    }

    return jsonify(response)


@app.route('/organizers/featured/detailed')
def featured_organizers_detailed():
    organizers = db.session.query(
        Organizer,
        func.count(Event.id).label('event_count'),
        func.avg(Event.capacity).label('avg_attendance')
    ).join(Event).group_by(Organizer.id
    ).order_by(func.count(Event.id).desc()).limit(4).all()
    
    result = []
    for organizer, event_count, avg_attendance in organizers:
        org_data = organizer.to_dict()
        org_data['event_count'] = event_count
        org_data['avg_attendance'] = round(float(avg_attendance or 0), 2)
        org_data['rating'] = 4.5  # Default rating
        
        # Get first upcoming event for category
        upcoming = Event.query.filter(
            Event.organizer_id == organizer.id,
            Event.end_datetime >= datetime.now()
        ).order_by(Event.start_datetime.asc()).first()
        
        if upcoming:
            org_data['next_event'] = {
                'category': upcoming.category,
                'date': upcoming.start_datetime.isoformat()
            }
        result.append(org_data)
    
    return jsonify(result)


@app.route('/organizers/search')
def search_organizers():
    search_term = request.args.get('q', '')
    min_events = request.args.get('min_events', 0, type=int)
    
    query = db.session.query(
        Organizer,
        func.count(Event.id).label('event_count')
    ).join(Event).group_by(Organizer.id)
    
    if search_term:
        query = query.filter(Organizer.name.ilike(f'%{search_term}%'))
    
    if min_events > 0:
        query = query.having(func.count(Event.id) >= min_events)
    
    organizers = query.order_by(Organizer.name.asc()).all()
    
    result = []
    for organizer, event_count in organizers:
        org_data = organizer.to_dict()
        org_data['event_count'] = event_count
        result.append(org_data)
    
    return jsonify(result)
#ticket-purchase
from uuid import uuid4

@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.json
    user_id = data.get('user_id')
    quantities = data.get('quantities')  # {ticket_type_id: quantity}
    attendee_name = data.get('attendee_name')
    attendee_email = data.get('attendee_email')
    billing_address = data.get('billing_address')
    payment_method = data.get('payment_method')

    if not user_id or not quantities:
        return jsonify({'error': 'Missing user or quantities'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    total = 0
    tickets_created = []
    event_id = None

    # Calculate total and confirm availability
    for ticket_type_id, qty in quantities.items():
        ticket_type = TicketType.query.get(ticket_type_id)
        if not ticket_type or ticket_type.quantity_available < qty:
            return jsonify({'error': f'Invalid or unavailable ticket type ID: {ticket_type_id}'}), 400

        if event_id and ticket_type.event_id != event_id:
            return jsonify({'error': 'Cannot purchase tickets for multiple events in one order.'}), 400
        event_id = ticket_type.event_id

        total += ticket_type.price * qty

    # Create order
    transaction_ref = f"TXN-{uuid4().hex[:10].upper()}"
    order = Order(
        user_id=user_id,
        customer_email=attendee_email,
        event_id=event_id,
        total_amount=total,
        status='completed',
        payment_method=payment_method,
        payment_status='paid',
        billing_address=billing_address,
        transaction_reference=transaction_ref
    )
    db.session.add(order)
    db.session.flush()  # To get order.id

    # Create tickets
    for ticket_type_id, qty in quantities.items():
        ticket_type = TicketType.query.get(ticket_type_id)

        for _ in range(qty):
            ticket = Ticket(
                ticket_type_id=ticket_type_id,
                order_id=order.id,
                attendee_name=attendee_name,
                attendee_email=attendee_email,
                unique_code=str(uuid4())
            )
            ticket.generate_qr_code()
            db.session.add(ticket)
            tickets_created.append(ticket)

        ticket_type.quantity_available -= qty

    db.session.commit()

    return jsonify({
        'message': 'Checkout successful',
        'order_id': order.id,
        'total': total,
        'transaction_reference': transaction_ref,
        'tickets': [t.to_dict() for t in tickets_created]
    })

@app.route('/profile/tickets', methods=['GET'])
def get_user_tickets():
    try:
        token = request.cookies.get('user_session')
        if not token:
            return jsonify({'error': 'Not logged in'}), 401

        token_data = serializer.loads(token, max_age=3600)
        user_id = token_data['id']

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        orders = Order.query.filter_by(user_id=user_id).order_by(Order.order_date.desc()).all()

        result = []
        for order in orders:
            order_data = order.to_dict_full()
            order_data['event'] = order.event.to_dict() if order.event else None
            order_data['tickets'] = [ticket.to_dict() for ticket in order.tickets]
            result.append(order_data)

        return jsonify(result), 200

    except BadSignature:
        return jsonify({'error': 'Invalid or expired session'}), 401
    except Exception as e:
        print("Error fetching tickets:", e)
        return jsonify({'error': 'Internal server error'}), 500


# Routes
@app.route('/organizers/featured/summary')
def featured_organizers_summary():
    organizers = db.session.query(
        Organizer,
        func.count(Event.id).label('event_count')
    ).join(Event).group_by(Organizer.id).order_by(func.count(Event.id).desc()).limit(4).all()
    
    result = []
    for organizer, event_count in organizers:
        org_data = organizer.to_dict()
        org_data['event_count'] = event_count
        org_data['rating'] = 4.5  # Default rating
        if organizer.events:
            org_data['events'] = [organizer.events[0].to_dict()]  # Get first event for category
        result.append(org_data)
    
    return jsonify(result)
@app.route('/organizer/profile', methods=['PATCH'])
def update_organizer_profile():
    try:
        token = request.cookies.get('user_session')
        if not token:
            return jsonify({'error': 'Not logged in'}), 401
        
        data = serializer.loads(token, max_age=3600)
        user_id = data['id']
        user = User.query.get(user_id)

        if not user or user.role != 'organizer':
            return jsonify({'error': 'Unauthorized'}), 403

        organizer = Organizer.query.filter_by(email=user.email).first()
        if not organizer:
            return jsonify({'error': 'Organizer not found'}), 404

        payload = request.json
        # Update fields if present in payload
        for field in ['name', 'email', 'phone', 'logo', 'website', 'description', 'speciality', 'contact_email']:
            if field in payload:
                setattr(organizer, field, payload[field])

        db.session.commit()
        return jsonify(organizer.to_dict()), 200

    except Exception as e:
        print("Error updating organizer profile:", e)
        return jsonify({'error': 'Server error'}), 500

@app.route('/organizer/profile', methods=['GET'])
def get_organizer_profile():
    try:
        token = request.cookies.get('user_session')
        if not token:
            return jsonify({'error': 'Not logged in'}), 401
        
        data = serializer.loads(token, max_age=3600)
        user_id = data['id']
        user = User.query.get(user_id)

        if not user or user.role != 'organizer':
            return jsonify({'error': 'Unauthorized'}), 403

        organizer = Organizer.query.filter_by(email=user.email).first()
        if not organizer:
            return jsonify({'error': 'Organizer profile not found'}), 404

        return jsonify(organizer.to_dict()), 200
    except Exception as e:
        print("Error getting organizer profile:", e)
        return jsonify({'error': 'Server error'}), 500

@app.route('/events/counts')
def event_counts_by_category():
    counts = db.session.query(
        Event.category,
        func.count(Event.id)
    ).filter(Event.is_active == True).group_by(Event.category).all()
    
    result = [{'name': cat, 'count': cnt} for cat, cnt in counts if cat is not None]
    return jsonify(result)

@app.route('/event-categories')
def event_categories():
    cats = db.session.query(Event.category, func.count(Event.id)) \
                   .group_by(Event.category).all()
    return jsonify([{'name': c[0], 'count': c[1]} for c in cats])
#events
@app.route('/events')
def get_events():
    search = request.args.get('search', '', type=str).lower()
    category = request.args.get('category', '', type=str).lower()

    # Start with active AND approved events
    query = Event.query.filter_by(is_active=True, status='approved')

    if search:
        query = query.filter(Event.title.ilike(f'%{search}%'))

    if category:
        query = query.filter(Event.category.ilike(f'%{category}%'))

    events = query.order_by(Event.start_datetime).all()

    results = []
    for e in events:
        venue = Venue.query.get(e.venue_id)
        results.append({
            'id': e.id,
            'title': e.title,
            'image': e.image,
            'date': e.start_datetime.strftime('%b %d, %Y'),
            'time': e.start_datetime.strftime('%I:%M %p'),
            'location': f"{venue.city}, {venue.state}" if venue else "TBD",
            'category': e.category,
            'rating': 4.5,
            'capacity': venue.capacity if venue else 0
        })

    return jsonify(results)

@app.route('/events/<int:id>/details')
def get_event_details(id):
    event = Event.query.get_or_404(id)
    venue = Venue.query.get(event.venue_id)
    return {
        'id': event.id,
        'title': event.title,
        'description': event.description,
        'image': event.image,
        'start_datetime': event.start_datetime.isoformat(),
        'end_datetime': event.end_datetime.isoformat(),
        'capacity': venue.capacity,
        'rating': 4.8,  # Optional mock
        'venue': {
            'name': venue.name,
            'address': venue.address
        },
        'ticket_types': [t.to_dict() for t in event.ticket_types]
    }

@app.route('/featured-events')
def featured_events():
    events = Event.query.filter_by(is_active=True, status='approved') \
                      .order_by(Event.created_at.desc()).limit(8).all()
    
    out = []
    for e in events:
        venue = Venue.query.get(e.venue_id)
        out.append({
            'id': e.id,
            'title': e.title,
            'image': e.image,
            'category': e.category,
            'date': e.start_datetime.strftime('%b %d, %Y'),
            'time': e.start_datetime.strftime('%I:%M %p'),
            'location': f"{venue.city}, {venue.state}" if venue else "",
            'rating': 4.5,
            'attendees': 1500
        })
    
    return jsonify(out)


@app.route('/organizers/featured/summary')
def featured_organizers():
    organizers = Organizer.query.filter_by(is_featured=True).limit(8).all()
    out = []
    for o in organizers:
        events = Event.query.filter_by(organizer_id=o.id, is_active=True, status='approved').all()
        out.append({
            'id': o.id,
            'name': o.name,
            'image': o.image,
            'rating': o.rating,
            'events': [{
                'id': e.id,
                'title': e.title,
                'start_datetime': e.start_datetime.isoformat()
            } for e in events]
        })
    return jsonify(out)

#organizer-event routes
# Create event
@app.route('/organiser/<int:organiser_id>/events', methods=['POST'])
def create_event(organiser_id):
    data = request.json
    try:
        event = Event(
            title=data['title'],
            description=data['description'],
            venue_id=data['venue_id'],
            start_datetime=datetime.fromisoformat(data['start_datetime']),
            end_datetime=datetime.fromisoformat(data['end_datetime']),
            organizer_id=organiser_id,
            image=data.get('image'),
            category=data.get('category'),
            capacity=data.get('capacity', 0),
            is_active=True
        )
        db.session.add(event)
        db.session.flush()  # So we get event.id before commit

        # Create associated ticket types
        ticket_types = data.get('ticket_types', [])
        for ticket in ticket_types:
            new_ticket = TicketType(
    name=ticket['name'],
    price=ticket['price'],
    quantity_available=ticket['quantity'],  # ✅ Map correctly
    event_id=event.id,
    sales_start=datetime.fromisoformat(ticket['sales_start']),
    sales_end=datetime.fromisoformat(ticket['sales_end']),
    description=ticket.get('description', '')
)

            db.session.add(new_ticket)
        sponsor_ids = data.get('sponsor_ids', [])
        if sponsor_ids:
            sponsors = Sponsor.query.filter(Sponsor.id.in_(sponsor_ids)).all()
            event.sponsors.extend(sponsors)

        db.session.commit()
        return jsonify(event.to_dict()), 201
        db.session.commit()
        return jsonify(event.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        print("Error creating event:", e)
        return jsonify({'error': 'Event creation failed'}), 500


# Update event
@app.route('/events/<int:event_id>', methods=['PATCH'])
def update_event(event_id):
    data = request.json
    event = Event.query.get_or_404(event_id)

    # Update basic fields
    for key in ['title', 'description', 'venue_id', 'start_datetime', 'end_datetime', 'image', 'category', 'capacity']:
        if key in data:
            setattr(event, key, data[key] if key not in ['start_datetime', 'end_datetime'] else datetime.fromisoformat(data[key]))

    # 🔥 Update sponsors (clear then add)
    if 'sponsor_ids' in data:
        sponsor_ids = data['sponsor_ids']
        sponsors = Sponsor.query.filter(Sponsor.id.in_(sponsor_ids)).all()
        event.sponsors = sponsors  # replaces the old list

    db.session.commit()
    return jsonify(event.to_dict()), 200

#event stats
@app.route('/events/<int:event_id>/stats')
def get_event_stats(event_id):
    event = Event.query.get_or_404(event_id)

    # Total revenue
    total_revenue = sum(order.total_amount for order in event.orders if order.status == 'completed')

    # Tickets sold by type
    ticket_counts = (
        db.session.query(Ticket.ticket_type_id, TicketType.name, db.func.count(Ticket.id))
        .join(TicketType)
        .filter(TicketType.event_id == event_id)
        .group_by(Ticket.ticket_type_id, TicketType.name)
        .all()
    )

    tickets_by_type = [
        {'ticket_type_id': t[0], 'name': t[1], 'count': t[2]} for t in ticket_counts
    ]

    return {
        'total_revenue': total_revenue,
        'tickets_by_type': tickets_by_type
    }

# Delete event
@app.route('/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)

    # Manually delete associated ticket types first
    for ticket in event.ticket_types:
        db.session.delete(ticket)

    db.session.delete(event)
    db.session.commit()

    return jsonify({'message': 'Event and tickets deleted'}), 200

@app.route('/events/<int:event_id>', methods=['GET'])
def get_event_by_id(event_id):
    event = Event.query.get_or_404(event_id)
    venue = Venue.query.get(event.venue_id)

    return {
        'id': event.id,
        'title': event.title,
        'description': event.description,
        'image': event.image,
        'start_datetime': event.start_datetime.isoformat(),
        'end_datetime': event.end_datetime.isoformat(),
        'capacity': event.capacity,
        'category': event.category,
        'venue': {
            'name': venue.name,
            'city': venue.city,
            'state': venue.state,
        } if venue else None,
        'organizer_id': event.organizer_id,  # also needed in frontend
        'sponsors': [
            {
                'id': s.id,
                'name': s.name,
                'logo': s.logo,
                'website': s.website,
                'contact_email': s.contact_email,
                'sponsorship_level': s.sponsorship_level
            } for s in event.sponsors
        ]
    }

# Enhanced event route to include venue details
@app.route('/organiser/<int:organiser_id>/events', methods=['GET'])
def get_organiser_events(organiser_id):
    events = Event.query.filter_by(organizer_id=organiser_id).order_by(Event.start_datetime.asc()).all()
    events_data = []

    for event in events:
        orders = Order.query.filter_by(event_id=event.id, status='completed').all()
        total_attendees = sum(len(order.tickets) for order in orders)
        total_revenue = sum(order.total_amount for order in orders)

        event_data = {
            'id': event.id,
            'title': event.title,
            'start_datetime': event.start_datetime.isoformat(),
            'end_datetime': event.end_datetime.isoformat(),
            'image': event.image,
            'status': 'Published' if event.is_active else 'Draft',
            'attendees': total_attendees,
            'revenue': total_revenue,
            'rating': round(event.rating, 1) if event.rating else 0.0
        }

        if event.venue_id:
            venue = Venue.query.get(event.venue_id)
            event_data['venue'] = venue.to_dict() if venue else None

        events_data.append(event_data)

    return jsonify(events_data), 200

#organiser-sponsor-routes
@app.route('/sponsors', methods=['GET'])
def get_sponsors():
    sponsors = Sponsor.query.all()
    return jsonify([s.to_dict() for s in sponsors]), 200
@app.route('/sponsors/<int:id>', methods=['GET'])
def get_sponsor(id):
    sponsor = Sponsor.query.get_or_404(id)
    return jsonify(sponsor.to_dict()), 200

@app.route('/sponsors', methods=['POST'])
def create_sponsor():
    data = request.get_json()
    sponsor = Sponsor(
        name=data['name'],
        logo=data.get('logo'),
        website=data.get('website'),
        contact_email=data.get('contact_email'),
        sponsorship_level=data.get('sponsorship_level')
    )
    db.session.add(sponsor)
    db.session.commit()
    return jsonify(sponsor.to_dict()), 201

@app.route('/sponsors/<int:id>', methods=['PATCH'])
def update_sponsor(id):
    sponsor = Sponsor.query.get_or_404(id)
    data = request.get_json()
    for field in ['name', 'logo', 'website', 'contact_email', 'sponsorship_level']:
        if field in data:
            setattr(sponsor, field, data[field])
    db.session.commit()
    return jsonify(sponsor.to_dict()), 200
@app.route('/sponsors/<int:id>', methods=['DELETE'])
def delete_sponsor(id):
    sponsor = Sponsor.query.get_or_404(id)
    db.session.delete(sponsor)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 204
#organiser-venue-routes

@app.route('/venues', methods=['GET'])
def get_venues():
    venues = Venue.query.all()
    return jsonify([v.to_dict() for v in venues]), 200

@app.route('/venues/<int:venue_id>', methods=['GET'])
def get_venue(venue_id):
    venue = Venue.query.get_or_404(venue_id)
    return jsonify(venue.to_dict()), 200
@app.route('/venues', methods=['POST'])
def create_venue():
    data = request.get_json()
    venue = Venue(
        name=data['name'],
        address=data.get('address'),
        city=data.get('city'),
        state=data.get('state'),
        zip_code=data.get('zip_code'),
        status="pending",
        capacity=data.get('capacity')
    )
    db.session.add(venue)
    db.session.commit()
    return jsonify(venue.to_dict()), 201

@app.route('/venues/<int:id>', methods=['PATCH'])
def update_venue(id):
    venue = Venue.query.get_or_404(id)
    data = request.get_json()
    for field in ['name', 'address', 'city', 'state', 'zip_code', 'capacity']:
        if field in data:
            setattr(venue, field, data[field])
    db.session.commit()
    return jsonify(venue.to_dict()), 200

@app.route('/venues/<int:id>', methods=['DELETE'])
def delete_venue(id):
    venue = Venue.query.get_or_404(id)
    db.session.delete(venue)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 204
@app.route('/')
def home():
    return jsonify({
        'message': 'EventHub API is running',
        'endpoints': {
            'featured_organizers': '/organizers/featured',
            'event_counts': '/events/counts',
            'event_categories': '/event-categories',
            'featured_events': '/featured-events'
        }
    })
#organizer-ticket-routes
# List ticket types with sold count for an organizer
from sqlalchemy import func

@app.route('/organiser/<int:organiser_id>/ticket-types', methods=['GET'])
def get_ticket_types_for_organiser(organiser_id):
    results = (
        db.session.query(
            TicketType,
            Event.title.label('event_title'),
            func.count(Ticket.id).label('sold')
        )
        .join(Event, TicketType.event_id == Event.id)
        .outerjoin(Ticket, Ticket.ticket_type_id == TicketType.id)
        .filter(Event.organizer_id == organiser_id)
        .group_by(TicketType.id, Event.title)
        .all()
    )

    output = []
    for ticket_type, event_title, sold in results:
        data = ticket_type.to_dict()
        data['event_title'] = event_title
        data['sold'] = sold
        output.append(data)

    return output, 200


# Create ticket type
from datetime import datetime
from dateutil.parser import parse

@app.route('/ticket-types', methods=['POST'])
def create_ticket_type():
    data = request.json
    
    # Validate required fields
    required_fields = ['name', 'price', 'quantity_available', 'event_id']
    for field in required_fields:
        if field not in data or data[field] is None:
            return jsonify({'error': f'{field} is required'}), 400

    try:
        sales_start = parse(str(data['sales_start'])) if 'sales_start' in data else None
        sales_end = parse(str(data['sales_end'])) if 'sales_end' in data else None
        
        # Ensure event_id is valid
        if not db.session.get(Event, data['event_id']):
            return jsonify({'error': 'Invalid event_id'}), 400

        tt = TicketType(
            event_id=data['event_id'],
            name=data['name'],
            price=float(data['price']),
            quantity_available=int(data['quantity_available']),
            sales_start=sales_start,
            sales_end=sales_end,
            description=data.get('description', ''),
            is_active=data.get('is_active', True)
        )
        db.session.add(tt)
        db.session.commit()
        return jsonify(tt.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error creating ticket type: {e}\nData received: {data}")
        return jsonify({'error': str(e)}), 400

# Edit ticket type
@app.route('/ticket-types/<int:id>', methods=['PATCH'])
def update_ticket_type(id):
    tt = TicketType.query.get_or_404(id)
    data = request.json
    for key in ['name','price','quantity_available','sales_start','sales_end','description','is_active']:
        if key in data:
            val = datetime.fromisoformat(data[key]) if 'start' in key or 'end' in key else data[key]
            setattr(tt, key, val)
    db.session.commit()
    return jsonify(tt.to_dict()), 200

# Delete ticket type
@app.route('/ticket-types/<int:id>', methods=['DELETE'])
def delete_ticket_type(id):
    tt = TicketType.query.get_or_404(id)
    db.session.delete(tt)
    db.session.commit()
    return jsonify({'message':'Deleted'}), 204

#UserLogins/AUTH-ROUTES
def set_user_cookie(response, user, extra_data=None):
    print("🔐 Setting user cookie")
    data = {
        'id': user.id,
        'email': user.email,
        'role': user.role
    }
    if extra_data:
        data.update(extra_data)
    token = serializer.dumps(data)
    print("🔐 Cookie token:", token)
    response.set_cookie(
        'user_session',
        value=token,
        httponly=True,
        secure=True,
        samesite='None',
          # Critical for production
        max_age=3600
    )

# auth.py (backend)

from flask import make_response, jsonify
from werkzeug.security import generate_password_hash
from datetime import datetime

@app.route('/auth/register', methods=['POST'])
def register():
    try:
        data = request.json
        
        # Check if username exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400
            
        # Check if email exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
            
        # Create new user
        user = User(
            username=data['username'],
            email=data['email'],
            password_hash=generate_password_hash(data['password']),
            role='user',
            created_at=datetime.utcnow()
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Create response with success message
        response = make_response(jsonify({
            'message': 'Registered',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        }), 200)
        
        # Set the cookie
        set_user_cookie(response, user)

        
        return response
        
    except Exception as e:
        db.session.rollback()
        print(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500
@app.route('/auth/login', methods=['POST'])
def login():
    print("🔐 Login attempt")
    data = request.json
    print("🔐 Login data:", data)
    user = User.query.filter_by(email=data['email']).first()
    print("🔐 User found:", user)
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error':'Invalid'}), 401
    resp = make_response(jsonify({'message':'Logged in'}))
    print("🔐 User authenticated, setting cookie")
    set_user_cookie(resp, user)
    return resp


@app.route('/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')
    frontend_url = data.get('frontend_url')

    if not email or not frontend_url:
        return jsonify({'error': 'Invalid request'}), 400

    user = User.query.filter_by(email=email).first()

    # Always return a generic message for security
    if not user:
        return jsonify({'message': 'If an account exists with this email, a reset link has been sent'}), 200

    # Generate token
    token = serializer.dumps(user.id)
    reset_link = f"{frontend_url}/reset-password/{token}"

    # Send email (production logic)
    try:
        msg = Message(subject="Password Reset Request",
                      recipients=[email],
                      body=f"Hello,\n\nClick the link below to reset your password:\n{reset_link}\n\nIf you didn't request this, please ignore this email.")
        email.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")
        return jsonify({'error': 'Failed to send reset email'}), 500

    return jsonify({'message': 'If an account exists with this email, a reset link has been sent'}), 200


@app.route('/auth/reset-password/<token>', methods=['POST'])
def reset_password(token):
    try:
        uid = serializer.loads(token, max_age=3600)
    except:
        return jsonify({'error':'Invalid/expired'}), 400
    user = User.query.get(uid)
    data = request.json
    user.password_hash = generate_password_hash(data['password'])
    db.session.commit()
    resp = make_response(jsonify({'message':'Password set'}))
    set_user_cookie(resp, user)
    return resp
@app.route('/auth/session', methods=['GET'])
def get_session():
    try:
        print("🔐 Checking session")
        token = request.cookies.get('user_session')
        print("🔐 Cookie value:", token)

        if not token:
            print("🚫 No token found in cookies")
            return jsonify(None), 200

        token_data = serializer.loads(token, max_age=3600)
        print("✅ Token data:", token_data)

        user_id = token_data['id']
        role = token_data.get('role', 'user')

        user = User.query.get(user_id)
        if not user:
            print("🚫 User not found in DB")
            return jsonify(None), 200

        return jsonify({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': role
            }
        }), 200
    except Exception as e:
        print("❌ Session check failed:", e)
        return jsonify(None), 200


@app.route('/auth/switch-to-organizer', methods=['POST'])
def switch_to_organizer():
    try:
        token = request.cookies.get('user_session')
        if not token:
            return jsonify({'error': 'No session found'}), 401

        token_data = serializer.loads(token)
        user_id = token_data.get('id')

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Check if already organizer
        existing_organizer = Organizer.query.filter_by(email=user.email).first()
        if existing_organizer:
            return jsonify({'error': 'Already an organizer'}), 400

        # Create organizer record
        organizer = Organizer(
            name=user.username,
            email=user.email,
            phone='Not Provided',
            contact_email=user.email
        )
        db.session.add(organizer)

        # Change user role
        user.role = 'organizer'

        db.session.commit()

        # Update cookie
        response = make_response(jsonify({'message': 'Switched to organizer', 'organizer_id': organizer.id}))
        set_user_cookie(response, user, extra_data={'organizer_id': organizer.id})  # Update helper function
        return response

    except Exception as e:
        db.session.rollback()
        print(f"Switch error: {e}")
        return jsonify({'error': 'Failed to switch to organizer'}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    try:
        response = make_response(jsonify({'success': True, 'message': 'Logged out successfully'}))
        response.delete_cookie('user_session')
        return response
    except Exception as e:
        print(f"Logout error: {e}")
        return jsonify({'success': False, 'error': 'Logout failed'}), 500
@app.route('/management/login', methods=['POST'])
def login_management():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    manager = Management.query.filter_by(email=email).first()

    if manager and check_password_hash(manager.password_hash, password):
        session['management_id'] = manager.id
        return jsonify(manager.to_dict()), 200
    return jsonify({'error': 'Invalid credentials'}), 401
@app.route('/management/register', methods=['POST'])
def register_management():
    data = request.json
    email = data.get('email')
    name = data.get('username')
    password = data.get('password')

    if Management.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400

    hashed_password = generate_password_hash(password)
    new_manager = Management(email=email, name=name, password_hash=hashed_password)
    db.session.add(new_manager)
    db.session.commit()

    session['management_id'] = new_manager.id
    return jsonify(new_manager.to_dict()), 201
@app.route('/management/session')
def management_session():
    manager_id = session.get('management_id')
    if not manager_id:
        return jsonify({'error': 'Not logged in'}), 401

    manager = Management.query.get(manager_id)
    if not manager:
        return jsonify({'error': 'Manager not found'}), 404

    return jsonify(manager.to_dict()), 200

@app.route('/management/logout', methods=['DELETE'])
def management_logout():
    session.pop('management_id', None)
    return '', 204
@app.route('/management/dashboard/stats')
def dashboard_stats():
    # Verify management session
    manager_id = session.get('management_id')
    if not manager_id:
        return jsonify({'error': 'Not logged in'}), 401

    # Get counts for dashboard
    total_organizers = Organizer.query.count()
    active_events = Event.query.filter_by(status='approved').count()
    print(f"Active events: {active_events}")  # Add this line to print active_events)
    pending_events = Event.query.filter_by(status='pending').count()
    print(f"Pending events: {pending_events}")
    return jsonify({
        'total_organizers': total_organizers,
        'active_events': active_events,
        'pending_events': pending_events
    })

@app.route('/management/events/pending')
def pending_events():
    # Verify management session
    manager_id = session.get('management_id')
    if not manager_id:
        return jsonify({'error': 'Not logged in'}), 401

    # Get pending events with organizer and venue info
    pending_events = Event.query.filter_by(status='pending').options(
        db.joinedload(Event.organizer),
        db.joinedload(Event.venue)
    ).all()

    events_data = []
    for event in pending_events:
        event_data = event.to_dict()
        event_data['organizer_name'] = event.organizer.name if event.organizer else None
        event_data['venue_name'] = event.venue.name if event.venue else None
        events_data.append(event_data)

    return jsonify(events_data)

@app.route('/management/events/<int:event_id>/approve', methods=['POST'])
def approve_event(event_id):
    # Verify management session
    manager_id = session.get('management_id')
    if not manager_id:
        return jsonify({'error': 'Not logged in'}), 401

    event = Event.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404

    event.status = 'approved'
    event.is_active = True
    db.session.commit()

    return jsonify({'message': 'Event approved successfully'})

@app.route('/management/events/<int:event_id>/reject', methods=['POST'])
def reject_event(event_id):
    # Verify management session
    manager_id = session.get('management_id')
    if not manager_id:
        return jsonify({'error': 'Not logged in'}), 401

    event = Event.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404

    event.status = 'rejected'
    event.is_active = False
    db.session.commit()

    return jsonify({'message': 'Event rejected successfully'})
@app.route('/management/venues/pending')
def pending_venues():
    # Verify management session
    manager_id = session.get('management_id')
    if not manager_id:
        return jsonify({'error': 'Not logged in'}), 401

    # Get pending venues (we'll add status field to Venue model later)
    pending_venues = Venue.query.all()  # Temporary - will filter by status later
    venues_data = [venue.to_dict() for venue in pending_venues]

    return jsonify(venues_data)

@app.route('/management/organizers')
def all_organizers():
    # Verify management session
    manager_id = session.get('management_id')
    if not manager_id:
        return jsonify({'error': 'Not logged in'}), 401

    organizers = Organizer.query.all()
    organizers_data = [org.to_dict() for org in organizers]

    return jsonify(organizers_data)
# Get all events (for management view)
@app.route('/management/events')
def all_events():
    manager_id = session.get('management_id')
    if not manager_id:
        return jsonify({'error': 'Not logged in'}), 401

    events = Event.query.options(
        db.joinedload(Event.organizer),
        db.joinedload(Event.venue)
    ).all()

    events_data = []
    for event in events:
        event_data = event.to_dict()
        event_data['organizer_name'] = event.organizer.name if event.organizer else None
        event_data['venue_name'] = event.venue.name if event.venue else None
        event_data['status'] = event.status
        events_data.append(event_data)

    return jsonify(events_data)

# Get single event details
@app.route('/management/events/<int:event_id>')
def get_event_details_for_management(event_id):
    manager_id = session.get('management_id')
    if not manager_id:
        return jsonify({'error': 'Not logged in'}), 401

    event = Event.query.options(
        db.joinedload(Event.organizer),
        db.joinedload(Event.venue),
        db.joinedload(Event.ticket_types),
        db.joinedload(Event.sponsors)
    ).get(event_id)

    if not event:
        return jsonify({'error': 'Event not found'}), 404

    event_data = {
        **event.to_dict(),
        'organizer': event.organizer.to_dict() if event.organizer else None,
        'venue': event.venue.to_dict() if event.venue else None,
        'ticket_types': [tt.to_dict() for tt in event.ticket_types],
        'sponsors': [s.to_dict() for s in event.sponsors],
        'status': event.status
    }

    return jsonify(event_data)

# Contact organizer endpoint
@app.route('/management/organizers/<int:organizer_id>')
def get_organizer_details(organizer_id):
    manager_id = session.get('management_id')
    if not manager_id:
        return jsonify({'error': 'Not logged in'}), 401

    organizer = Organizer.query.get(organizer_id)
    if not organizer:
        return jsonify({'error': 'Organizer not found'}), 404

    # Get count of events created by this organizer
    events_count = Event.query.filter_by(organizer_id=organizer.id).count()

    organizer_data = organizer.to_dict()
    organizer_data['events_count'] = events_count
    
    return jsonify(organizer_data)
@app.route('/events/<int:event_id>/tickets-summary')
def tickets_summary(event_id):
    event = Event.query.get_or_404(event_id)

    summary = []
    for ticket_type in event.ticket_types:
        # Count tickets that are part of completed orders (not pending or cancelled)
        sold_count = db.session.query(Ticket).join(Order).filter(
            Ticket.ticket_type_id == ticket_type.id,
            Order.status == 'completed'  # Only count tickets from completed orders
        ).count()
        
        total_quantity = ticket_type.quantity_available
        remaining = max(0, total_quantity - sold_count)  # Ensure remaining isn't negative

        summary.append({
            'ticket_type_id': ticket_type.id,
            'sold': sold_count,
            'remaining': remaining,
            'total': total_quantity,
            'sales_percentage': (sold_count / total_quantity * 100) if total_quantity > 0 else 0
        })

    return jsonify(summary)
@app.route('/management/organizers', methods=['GET'])
def get_organizers_for_management():
    organizers = Organizer.query.all()
    organizers_data = []
    for org in organizers:
        print(f"Organizer: {org}")
        org_data = {
            'id': org.id,
            'name': org.name,
            'email': org.email,
            'phone': org.phone,
            'logo': org.logo,
            'website': org.website,
            'description': org.description,
            'speciality': org.speciality,  # ✅ make sure this line is correct
            'contact_email': org.contact_email,
            'created_at': org.created_at.isoformat() if org.created_at else None,
            'rating': org.rating,
            'eventsCount': len(org.events)
        }
        organizers_data.append(org_data)
        print (f"Organizer data: {org_data}")
    return jsonify(organizers_data), 200

@app.route('/management/organizers/<int:organizer_id>', methods=['GET'])
def get_organizer_details_for_management(organizer_id):
    organizer = Organizer.query.get_or_404(organizer_id)
    
    organizer_data = {
        'id': organizer.id,
        'name': organizer.name,
        'email': organizer.email,
        'phone': organizer.phone,
        'logo': organizer.logo,
        'website': organizer.website,
        'description': organizer.description,
        'speciality': organizer.speciality,
        'contact_email': organizer.contact_email,
        'created_at': organizer.created_at.isoformat() if organizer.created_at else None,
        'rating': organizer.rating,
        'events_count': len(organizer.events)
    }
    
    return jsonify(organizer_data), 200

@app.route('/management/organizers/<int:organizer_id>/events', methods=['GET'])
def get_organizer_events_for_management(organizer_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    events = Event.query.filter_by(organizer_id=organizer_id)\
                       .order_by(Event.start_datetime.desc())\
                       .paginate(page=page, per_page=per_page, error_out=False)
    
    events_data = []
    for event in events.items:
        event_data = {
            'id': event.id,
            'title': event.title,
            'description': event.description,
            'start_datetime': event.start_datetime.isoformat(),
            'end_datetime': event.end_datetime.isoformat(),
            'image': event.image,
            'status': event.status,
            'created_at': event.created_at.isoformat() if event.created_at else None,
            'venue': {
                'name': event.venue.name if event.venue else None,
                'city': event.venue.city if event.venue else None
            }
        }
        events_data.append(event_data)
    
    return jsonify({
        'events': events_data,
        'total': events.total,
        'pages': events.pages,
        'current_page': events.page
    }), 200

@app.route('/management/organizers/<int:organizer_id>/sponsors', methods=['GET'])
def get_organizer_sponsors(organizer_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    sponsors = Sponsor.query.filter_by(organizer_id=organizer_id)\
                           .order_by(Sponsor.name.asc())\
                           .paginate(page=page, per_page=per_page, error_out=False)
    
    sponsors_data = []
    for sponsor in sponsors.items:
        sponsor_data = {
            'id': sponsor.id,
            'name': sponsor.name,
            'logo': sponsor.logo,
            'website': sponsor.website,
            'sponsorship_level': sponsor.sponsorship_level,
            'contact_email': sponsor.contact_email,
            'contact_phone': sponsor.contact_phone
        }
        sponsors_data.append(sponsor_data)
    
    return jsonify({
        'sponsors': sponsors_data,
        'total': sponsors.total,
        'pages': sponsors.pages,
        'current_page': sponsors.page
    }), 200
@app.route('/management/venues/<int:venue_id>/approve', methods=['PATCH', 'POST'])
def approve_venue(venue_id):
    manager_id = session.get('management_id')
    if not manager_id:
        return jsonify({'error': 'Not logged in'}), 401

    venue = Venue.query.get(venue_id)
    if not venue:
        return jsonify({'error': 'Venue not found'}), 404

    venue.status = 'approved'
    db.session.commit()
    return jsonify({
        'message': 'Venue approved successfully',
        'venue': {
            'id': venue.id,
            'name': venue.name,
            'status': venue.status
        }
    }), 200

@app.route('/management/venues/<int:venue_id>/reject', methods=['PATCH', 'POST'])
def reject_venue(venue_id):
    manager_id = session.get('management_id')
    if not manager_id:
        return jsonify({'error': 'Not logged in'}), 401

    venue = Venue.query.get(venue_id)
    if not venue:
        return jsonify({'error': 'Venue not found'}), 404

    venue.status = 'rejected'
    db.session.commit()
    return jsonify({
        'message': 'Venue rejected successfully',
        'venue': {
            'id': venue.id,
            'name': venue.name,
            'status': venue.status
        }
    }), 200
@app.route('/management/venues', methods=['GET'])
def get_all_venues():
    manager_id = session.get('management_id')
    if not manager_id:
        return jsonify({'error': 'Not logged in'}), 401

    venues = Venue.query.all()
    venues_data = [
        {
            'id': venue.id,
            'name': venue.name,
            'address': venue.address,
            'city': venue.city,
            'state': venue.state,
            'zip_code': venue.zip_code,
            'capacity': venue.capacity,
            'status': venue.status,
            'created_at': venue.created_at.isoformat() if venue.created_at else None
        }
        for venue in venues
    ]

    return jsonify(venues_data), 200
@app.route('/management/venues/<int:venue_id>', methods=['GET'])
def get_venue_details(venue_id):
    manager_id = session.get('management_id')
    if not manager_id:
        return jsonify({'error': 'Not logged in'}), 401

    venue = Venue.query.get_or_404(venue_id)
    venue_data = {
        'id': venue.id,
        'name': venue.name,
        'address': venue.address,
        'city': venue.city,
        'state': venue.state,
        'zip_code': venue.zip_code,
        'capacity': venue.capacity,
        'status': venue.status,
        'created_at': venue.created_at.isoformat() if venue.created_at else None,
        'updated_at': venue.updated_at.isoformat() if venue.updated_at else None
    }
    return jsonify(venue_data), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5557, debug=True)
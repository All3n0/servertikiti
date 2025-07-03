from flask import Flask, jsonify, request, make_response,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from config import Config
from sqlalchemy import func
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer

# Initialize serializer
serializer = URLSafeTimedSerializer(Config.SECRET_KEY)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app, supports_credentials=True)

# Import models after db initialization to avoid circular imports
from models import Organizer, Event, Venue, Sponsor, TicketType, User, Order, Discount, Ticket, RefundRequest
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
            'capacity': event.capacity
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

    query = Event.query.filter_by(is_active=True)

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
    events = Event.query.filter_by(is_active=True) \
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

@app.route('/featured-organizers')
def featured_organizers_alt():
    orgs = Organizer.query.order_by(Organizer.created_at.desc()).limit(8).all()
    return jsonify([{
        'id': o.id,
        'name': o.name,
        'avatar': o.logo,
        'specialty': o.website or "",
        'eventsCount': len(o.events),
        'rating': 4.7
    } for o in orgs])

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
#UserLogins
def set_user_cookie(resp, user):
    token = serializer.dumps(user.id)
    resp.set_cookie('user_session', token, httponly=True, secure=True, max_age=3600)

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
        token = serializer.dumps(user.id)
        response.set_cookie(
            'user_session',
            token,
            httponly=True,
            secure=False,  # Use False in development if not using HTTPS
            samesite='Lax',
            max_age=3600  # 1 hour expiration
        )
        
        return response
        
    except Exception as e:
        db.session.rollback()
        print(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500
@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error':'Invalid'}), 401
    resp = make_response(jsonify({'message':'Logged in'}))
    set_user_cookie(resp, user)
    return resp

@app.route('/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if not user:
        return jsonify({}), 200
    token = serializer.dumps(user.id)
    reset_link = f"{data['frontend_url']}/reset-password/{token}"
    print('Reset link:', reset_link)  # or email it
    return jsonify({'message':'If exists, reset sent'})

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
        token = request.cookies.get('user_session')
        if not token:
            return jsonify({'user': None}), 200
        user_id = serializer.loads(token, max_age=3600)
        user = User.query.get(user_id)
        if not user:
            return jsonify({'user': None}), 200
        return jsonify({'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email
        }}), 200
    except Exception as e:
        print("Session check failed:", e)
        return jsonify({'user': None}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5557, debug=True)
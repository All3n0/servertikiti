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

# Routes
@app.route('/organizers/featured')
def featured_organizers():
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

@app.route('/auth/register', methods=['POST'])
def register():
    try:
        data = request.json
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error':'Email exists'}), 400
        user = User(
            username=data['username'], 
            email=data['email'], 
            password_hash=generate_password_hash(data['password']), 
            role='user'
        )
        db.session.add(user)
        print(user)
        db.session.commit()
        resp = make_response(jsonify({'message':'Registered'}))
        set_user_cookie(resp, user)
        return resp
    except Exception as e:
        db.session.rollback()
        print(f"Registration error: {str(e)}")  # Check your console
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
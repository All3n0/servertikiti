from app import app, db
from models import *

with app.app_context():
    # Clear existing data
    db.drop_all()
    db.create_all()

    # --- Organizers ---
    organizer1 = Organizer(name="Allan Events", email="allan@example.com", phone="0700000001",
                           logo="logos/allan.png", website="https://allan.com", contact_email="contact@allan.com")
    organizer2 = Organizer(name="Moringa Live", email="moringa@example.com", phone="0700000002",
                           logo="logos/moringa.png", website="https://moringa.com", contact_email="events@moringa.com")
    organizer3 = Organizer(name="Nairobi Nights", email="nairobi@example.com", phone="0700000003",
                           logo="logos/nairobi.png", website="https://nairobilive.com", contact_email="info@nairobi.com")
    organizer4 = Organizer(name="TechFest", email="techfest@example.com", phone="0700000004",
                           logo="logos/techfest.png", website="https://techfest.io", contact_email="support@techfest.io")
    organizer5 = Organizer(name="KenyaBuzz", email="buzz@example.com", phone="0700000005",
                           logo="logos/buzz.png", website="https://kenyabuzz.com", contact_email="admin@buzz.com")
    db.session.add_all([organizer1, organizer2, organizer3, organizer4, organizer5])

    # --- Sponsors ---
    sponsor1 = Sponsor(name="Safaricom", logo="sponsors/safaricom.png", website="https://safaricom.co.ke", contact_email="sponsor@safaricom.com", sponsorship_level="Gold")
    sponsor2 = Sponsor(name="Jumia", logo="sponsors/jumia.png", website="https://jumia.co.ke", contact_email="partner@jumia.com", sponsorship_level="Silver")
    sponsor3 = Sponsor(name="Equity Bank", logo="sponsors/equity.png", website="https://equitybank.co.ke", contact_email="equity@sponsor.com", sponsorship_level="Gold")
    sponsor4 = Sponsor(name="Airtel", logo="sponsors/airtel.png", website="https://airtel.co.ke", contact_email="sponsor@airtel.com", sponsorship_level="Bronze")
    sponsor5 = Sponsor(name="Tusker", logo="sponsors/tusker.png", website="https://tusker.com", contact_email="events@tusker.com", sponsorship_level="Silver")
    db.session.add_all([sponsor1, sponsor2, sponsor3, sponsor4, sponsor5])

    # --- Venues ---
    venue1 = Venue(name="KICC", address="City Hall Way", city="Nairobi", state="Nairobi", zip_code="00100", capacity=5000)
    venue2 = Venue(name="Sarit Expo", address="Sarit Centre", city="Nairobi", state="Nairobi", zip_code="00100", capacity=3000)
    venue3 = Venue(name="The Alchemist", address="Westlands", city="Nairobi", state="Nairobi", zip_code="00100", capacity=1000)
    venue4 = Venue(name="Kenyatta University Amphitheatre", address="Thika Rd", city="Nairobi", state="Nairobi", zip_code="00100", capacity=2000)
    venue5 = Venue(name="Nyayo Stadium", address="Langata Rd", city="Nairobi", state="Nairobi", zip_code="00100", capacity=15000)
    db.session.add_all([venue1, venue2, venue3, venue4, venue5])

    # --- Events ---
    event1 = Event(title="Nairobi Music Fest", description="Annual music festival", venue=venue1,
                   start_datetime=datetime(2025, 8, 1, 16, 0), end_datetime=datetime(2025, 8, 1, 22, 0),
                   organizer=organizer1, image="events/musicfest.jpg", category="Music" )
    event2 = Event(title="Tech Conference 2025", description="Tech talks and innovation", venue=venue2,
                   start_datetime=datetime(2025, 9, 12, 10, 0), end_datetime=datetime(2025, 9, 12, 17, 0),
                   organizer=organizer2, image="events/techconf.jpg", category="Technology")
    event3 = Event(title="Food Expo", description="Taste the world", venue=venue3,
                   start_datetime=datetime(2025, 10, 5, 12, 0), end_datetime=datetime(2025, 10, 5, 20, 0),
                   organizer=organizer3, image="events/foodexpo.jpg", category="Food")
    event4 = Event(title="Startup Demo Day", description="Pitch and fund startups", venue=venue4,
                   start_datetime=datetime(2025, 11, 3, 9, 0), end_datetime=datetime(2025, 11, 3, 13, 0),
                   organizer=organizer4, image="events/demoday.jpg", category="Business")
    event5 = Event(title="Comedy Night", description="Stand-up comedy special", venue=venue5,
                   start_datetime=datetime(2025, 12, 15, 19, 0), end_datetime=datetime(2025, 12, 15, 22, 0),
                   organizer=organizer5, image="events/comedy.jpg", category="Entertainment")
    db.session.add_all([event1, event2, event3, event4, event5])

    # --- Ticket Types ---
    ticket1 = TicketType(event=event1, name="General", price=1000, quantity_available=100, sales_start=datetime(2025, 7, 1), sales_end=datetime(2025, 8, 1))
    ticket2 = TicketType(event=event2, name="Student Pass", price=500, quantity_available=200, sales_start=datetime(2025, 7, 10), sales_end=datetime(2025, 9, 10))
    ticket3 = TicketType(event=event3, name="VIP", price=2500, quantity_available=50, sales_start=datetime(2025, 8, 1), sales_end=datetime(2025, 10, 1))
    ticket4 = TicketType(event=event4, name="Investor", price=3000, quantity_available=30, sales_start=datetime(2025, 9, 1), sales_end=datetime(2025, 11, 1))
    ticket5 = TicketType(event=event5, name="Regular", price=800, quantity_available=150, sales_start=datetime(2025, 10, 1), sales_end=datetime(2025, 12, 14))
    db.session.add_all([ticket1, ticket2, ticket3, ticket4, ticket5])
    db.session.commit()
    # --- Users ---
    user1 = User(username="allan", email="allan@event.com", password_hash="hashed1", role="admin")
    user2 = User(username="jane", email="jane@event.com", password_hash="hashed2", role="organizer")
    user3 = User(username="peter", email="peter@event.com", password_hash="hashed3", role="customer")
    user4 = User(username="lucy", email="lucy@event.com", password_hash="hashed4", role="customer")
    user5 = User(username="mike", email="mike@event.com", password_hash="hashed5", role="customer")
    db.session.add_all([user1, user2, user3, user4, user5])

    # --- Orders ---
    order1 = Order(user=user3, customer_email=user3.email, total_amount=1000, event_id=event1.id, transaction_reference='TXN-10001')
    order2 = Order(user=user4, customer_email=user4.email, total_amount=500, event_id=event2.id, transaction_reference='TXN-10002')
    order3 = Order(user=user5, customer_email=user5.email, total_amount=2500, event_id=event1.id, transaction_reference='TXN-10003')
    order4 = Order(user=user3, customer_email=user3.email, total_amount=3000, event_id=event3.id, transaction_reference='TXN-10004')
    order5 = Order(user=user4, customer_email=user4.email, total_amount=800, event_id=event2.id, transaction_reference='TXN-10005')

    db.session.add_all([order1, order2, order3, order4, order5])
    


    # --- Discounts ---
    discount1 = Discount(code="DISC10", discount_type="percentage", value=10, valid_from=datetime(2025, 7, 1), valid_to=datetime(2025, 12, 1), max_uses=100, order=order1)
    discount2 = Discount(code="VIP50", discount_type="fixed", value=50, valid_from=datetime(2025, 7, 1), valid_to=datetime(2025, 12, 1), max_uses=50, order=order2)
    discount3 = Discount(code="EARLY20", discount_type="percentage", value=20, valid_from=datetime(2025, 7, 1), valid_to=datetime(2025, 12, 1), max_uses=80, order=order3)
    discount4 = Discount(code="STUDENT30", discount_type="fixed", value=30, valid_from=datetime(2025, 7, 1), valid_to=datetime(2025, 12, 1), max_uses=30, order=order4)
    discount5 = Discount(code="COMEDY5", discount_type="fixed", value=5, valid_from=datetime(2025, 7, 1), valid_to=datetime(2025, 12, 1), max_uses=10, order=order5)
    db.session.add_all([discount1, discount2, discount3, discount4, discount5])

    # --- Tickets ---
    ticket_inst1 = Ticket(ticket_type_id=ticket1.id, order=order1, attendee_name="Peter Maina", attendee_email="peter@event.com", unique_code="TICKET12345")
    ticket_inst2 = Ticket(ticket_type_id=ticket2.id, order=order2, attendee_name="Lucy M", attendee_email="lucy@event.com", unique_code="TICKET22345")
    ticket_inst3 = Ticket(ticket_type_id=ticket3.id, order=order3, attendee_name="Mike O", attendee_email="mike@event.com", unique_code="TICKET32345")
    ticket_inst4 = Ticket(ticket_type_id=ticket4.id, order=order4, attendee_name="Peter Maina", attendee_email="peter@event.com", unique_code="TICKET42345")
    ticket_inst5 = Ticket(ticket_type_id=ticket5.id, order=order5, attendee_name="Lucy M", attendee_email="lucy@event.com", unique_code="TICKET52345")
    db.session.add_all([ticket_inst1, ticket_inst2, ticket_inst3, ticket_inst4, ticket_inst5])

    # --- Refund Requests ---
    refund1 = RefundRequest(ticket=ticket_inst1, reason="Can't attend")
    refund2 = RefundRequest(ticket=ticket_inst2, reason="Event moved")
    refund3 = RefundRequest(ticket=ticket_inst3, reason="Double booking")
    refund4 = RefundRequest(ticket=ticket_inst4, reason="Illness")
    refund5 = RefundRequest(ticket=ticket_inst5, reason="Change of plans")
    db.session.add_all([refund1, refund2, refund3, refund4, refund5])

    db.session.commit()
    print("✅ Seeded 5 records in each table successfully!")

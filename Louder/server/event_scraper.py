import sqlite3
import datetime
import schedule
import time
import logging
import requests
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from icalendar import Calendar
from dateutil.parser import parse as date_parse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("sydney_events_scraper")

def setup_database():
    logger.info("Connecting to database...")
    conn = sqlite3.connect('sydney_events.db')
    logger.info("Connected.")
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        date TEXT,
        time TEXT,
        venue TEXT,
        image_url TEXT,
        ticket_url TEXT UNIQUE,
        price TEXT,
        category TEXT,
        source_site TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database setup complete")

def store_event(event_data):
    logger.info(f"Storing event: {event_data['title']}")
    conn = sqlite3.connect('sydney_events.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT OR IGNORE INTO events 
        (title, description, date, time, venue, image_url, ticket_url, price, category, source_site)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event_data['title'], event_data['description'], event_data['date'], event_data['time'],
            event_data['venue'], event_data['image_url'], event_data['ticket_url'],
            event_data['price'], event_data['category'], event_data['source_site']
        ))
        conn.commit()
        logger.info(f"Stored event: {event_data['title']}")
    except Exception as e:
        logger.error(f"Error storing event {event_data['title']}: {e}")
    finally:
        conn.close()

def fetch_predicthq_events():
    logger.info("Fetching events from PredictHQ API")
    api_key = "YOUR_API_KEY"
    if api_key == "YOUR_API_KEY":
        logger.error("PredictHQ API key not set.")
        return
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    params = {
        "location.around.origin": "-33.8688,151.2093",
        "location.around.radius": "20km",
        "active.gte": datetime.datetime.utcnow().isoformat() + 'Z',
        "limit": 20
    }
    try:
        response = requests.get("https://api.predicthq.com/v1/events/", headers=headers, params=params)
        if response.status_code == 200:
            for event in response.json().get("results", []):
                title = event["title"]
                description = event.get("description", "No description available")[:500]
                start = event.get("start")
                date_obj = datetime.datetime.fromisoformat(start.replace('Z', '+00:00')) if start else None
                date_str = date_obj.strftime("%Y-%m-%d") if date_obj else "TBA"
                time_str = date_obj.strftime("%H:%M") if date_obj else "TBA"
                venue = next((e.get("name") for e in event.get("entities", []) if e.get("type") == "venue"), "Sydney")
                category = event.get("category", "General")
                ticket_url = next((e.get("formatted_url") for e in event.get("entities", []) if e.get("type") == "website"), f"predicthq-event-{event['id']}")
                store_event({
                    'title': title,
                    'description': description,
                    'date': date_str,
                    'time': time_str,
                    'venue': venue,
                    'image_url': '',
                    'ticket_url': ticket_url,
                    'price': 'Check site',
                    'category': category,
                    'source_site': 'PredictHQ'
                })
        else:
            logger.error(f"PredictHQ API error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Failed to fetch PredictHQ events: {e}")

def fetch_google_calendar_ics():
    logger.info("Fetching from Google Calendar ICS")
    url = "https://calendar.google.com/calendar/ical/en.australian%23holiday%40group.v.calendar.google.com/public/basic.ics"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            cal = Calendar.from_ical(response.text)
            for component in cal.walk():
                if component.name == "VEVENT":
                    dt = component.get('dtstart').dt
                    event_data = {
                        'title': str(component.get('summary', 'No Title')),
                        'description': 'Holiday event from Google Calendar',
                        'date': dt.strftime("%Y-%m-%d") if isinstance(dt, datetime.date) else "TBA",
                        'time': dt.strftime("%H:%M") if isinstance(dt, datetime.datetime) else "TBA",
                        'venue': 'Australia',
                        'image_url': '',
                        'ticket_url': url,
                        'price': 'Free',
                        'category': 'Holiday',
                        'source_site': 'Google Calendar ICS'
                    }
                    store_event(event_data)
        else:
            logger.error(f"Google Calendar ICS fetch failed: HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching Google Calendar ICS: {e}")

def fetch_eventful():
    logger.info("Fetching events from Eventful API")
    api_key = "YOUR_EVENTFUL_API_KEY"
    if not api_key or api_key == "YOUR_EVENTFUL_API_KEY":
        logger.warning("Eventful API key missing")
        return
    params = {
        'app_key': api_key,
        'location': 'Sydney',
        'date': 'Future',
        'page_size': 10,
        'sort_order': 'date'
    }
    try:
        response = requests.get("http://api.eventful.com/json/events/search", params=params)
        if response.status_code == 200:
            events = response.json().get("events", {}).get("event", [])
            for ev in events:
                store_event({
                    'title': ev.get("title", "No Title"),
                    'description': ev.get("description", "Eventful event"),
                    'date': ev.get("start_time", "TBA")[:10],
                    'time': ev.get("start_time", "TBA")[11:16],
                    'venue': ev.get("venue_name", "Sydney"),
                    'image_url': ev.get("image", {}).get("medium", {}).get("url", ""),
                    'ticket_url': ev.get("url", ""),
                    'price': 'Check site',
                    'category': ev.get("category", "General"),
                    'source_site': 'Eventful'
                })
        else:
            logger.error(f"Eventful API error: {response.status_code}")
    except Exception as e:
        logger.error(f"Eventful API fetch error: {e}")

def run_all_scrapers():
    logger.info("Running all scrapers")
    fetch_google_calendar_ics()
    fetch_predicthq_events()
    fetch_eventful()
    logger.info("All scrapers finished")

def schedule_scraping():
    run_all_scrapers()
    schedule.every().day.at("02:00").do(run_all_scrapers)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    setup_database()
    run_all_scrapers()

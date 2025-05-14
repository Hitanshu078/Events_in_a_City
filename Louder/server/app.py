"""
Sydney Events Backend Server

This Flask application serves event data from the database
and handles user interactions like email collection.
"""
import sys
print("Python executable:", sys.executable)
print("Python path:", sys.path)
from flask import Flask, jsonify, request, render_template, redirect, abort
from flask_cors import CORS
import sqlite3
import os
import json
import logging
from datetime import datetime
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("sydney_events_server")

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)  # Enable CORS for all routes

def get_db_connection():
    """Create a connection to the SQLite database."""
    conn = sqlite3.connect('sydney_events.db')
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/api/events')
def get_events():
    """API endpoint to get all events."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get query parameters for filtering
        category = request.args.get('category')
        date = request.args.get('date')
        search = request.args.get('search')
        
        # Base query
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        # Add filters if provided
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if date:
            query += " AND date LIKE ?"
            params.append(f"%{date}%")
        
        if search:
            query += " AND (title LIKE ? OR description LIKE ? OR venue LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        # Order by date
        query += " ORDER BY date ASC"
        
        cursor.execute(query, params)
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(events)
    except Exception as e:
        logger.error(f"Error fetching events: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/events/<int:event_id>')
def get_event(event_id):
    """API endpoint to get a specific event."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        event = cursor.fetchone()
        conn.close()
        
        if event:
            return jsonify(dict(event))
        else:
            return jsonify({"error": "Event not found"}), 404
    except Exception as e:
        logger.error(f"Error fetching event {event_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/categories')
def get_categories():
    """API endpoint to get all unique categories."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM events ORDER BY category")
        categories = [row['category'] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(categories)
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/venues')
def get_venues():
    """API endpoint to get all unique venues."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT venue FROM events ORDER BY venue")
        venues = [row['venue'] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(venues)
    except Exception as e:
        logger.error(f"Error fetching venues: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ticket-redirect', methods=['POST'])
def ticket_redirect():
    """Handle ticket redirection with email collection."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        email = data.get('email')
        event_id = data.get('event_id')
        opt_in = data.get('opt_in', False)
        
        # Validate email
        if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify({"error": "Invalid email address"}), 400
        
        # Get the ticket URL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ticket_url FROM events WHERE id = ?", (event_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({"error": "Event not found"}), 404
        
        ticket_url = result['ticket_url']
        
        # Store the user interaction
        cursor.execute('''
        INSERT INTO user_interactions (email, event_id, opted_in)
        VALUES (?, ?, ?)
        ''', (email, event_id, 1 if opt_in else 0))
        conn.commit()
        conn.close()
        
        return jsonify({"redirect_url": ticket_url})
    except Exception as e:
        logger.error(f"Error in ticket redirect: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Create templates and static directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('static/images', exist_ok=True)
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
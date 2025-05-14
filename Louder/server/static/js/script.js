/**
 * Sydney Events - Main JavaScript
 * Handles event loading, filtering, and ticket reservation
 */

// Global variables
let allEvents = [];
let filteredEvents = [];
let categories = [];
let venues = [];

// DOM elements
const eventsGrid = document.getElementById('eventsGrid');
const noEvents = document.getElementById('noEvents');
const categoryFilter = document.getElementById('categoryFilter');
const dateFilter = document.getElementById('dateFilter');
const venueFilter = document.getElementById('venueFilter');
const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const clearFiltersBtn = document.getElementById('clearFilters');
const eventCardTemplate = document.getElementById('eventCardTemplate');
const ticketModal = document.getElementById('ticketModal');
const emailInput = document.getElementById('emailInput');
const optInCheckbox = document.getElementById('optInCheckbox');
const ticketSubmitBtn = document.getElementById('ticketSubmitBtn');
const modalClose = document.querySelector('.close');

let currentEventId = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    init();
});

// Initialize the application
async function init() {
    try {
        await Promise.all([
            fetchEvents(),
            fetchCategories(),
            fetchVenues()
        ]);
        
        setupEventListeners();
        renderEvents(allEvents);
    } catch (error) {
        console.error('Initialization error:', error);
        showError('Failed to load event data. Please try again later.');
    }
}

// Fetch all events from the API
async function fetchEvents() {
    try {
        const response = await fetch('/api/events');
        if (!response.ok) throw new Error('Failed to fetch events');
        
        allEvents = await response.json();
        filteredEvents = [...allEvents];
        
        return allEvents;
    } catch (error) {
        console.error('Error fetching events:', error);
        throw error;
    }
}

// Fetch all categories
async function fetchCategories() {
    try {
        const response = await fetch('/api/categories');
        if (!response.ok) throw new Error('Failed to fetch categories');
        
        categories = await response.json();
        populateCategoryFilter(categories);
        
        return categories;
    } catch (error) {
        console.error('Error fetching categories:', error);
        throw error;
    }
}

// Fetch all venues
async function fetchVenues() {
    try {
        const response = await fetch('/api/venues');
        if (!response.ok) throw new Error('Failed to fetch venues');
        
        venues = await response.json();
        populateVenueFilter(venues);
        
        return venues;
    } catch (error) {
        console.error('Error fetching venues:', error);
        throw error;
    }
}

// Populate category filter dropdown
function populateCategoryFilter(categories) {
    categoryFilter.innerHTML = '<option value="">All Categories</option>';
    
    categories.forEach(category => {
        if (category) {  // Ensure the category is not null or empty
            const option = document.createElement('option');
            option.value = category;
            option.textContent = category;
            categoryFilter.appendChild(option);
        }
    });
}

// Populate venue filter dropdown
function populateVenueFilter(venues) {
    venueFilter.innerHTML = '<option value="">All Venues</option>';
    
    venues.forEach(venue => {
        if (venue) {  // Ensure the venue is not null or empty
            const option = document.createElement('option');
            option.value = venue;
            option.textContent = venue;
            venueFilter.appendChild(option);
        }
    });
}

// Setup event listeners
function setupEventListeners() {
    // Filter change events
    categoryFilter.addEventListener('change', applyFilters);
    dateFilter.addEventListener('change', applyFilters);
    venueFilter.addEventListener('change', applyFilters);
    
    // Search events
    searchButton.addEventListener('click', applyFilters);
    searchInput.addEventListener('keypress', event => {
        if (event.key === 'Enter') {
            applyFilters();
        }
    });
    
    // Clear filters
    clearFiltersBtn.addEventListener('click', clearFilters);
    
    // Navigation filter clicks
    document.querySelectorAll('nav ul li a').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all nav links
            document.querySelectorAll('nav ul li a').forEach(item => {
                item.classList.remove('active');
            });
            
            // Add active class to clicked link
            this.classList.add('active');
            
            // Apply category filter based on data-filter attribute
            const filter = this.getAttribute('data-filter');
            if (filter === 'all') {
                categoryFilter.value = '';
            } else {
                categoryFilter.value = filter;
            }
            
            applyFilters();
        });
    });
    
    // Modal events
    modalClose.addEventListener('click', closeModal);
    window.addEventListener('click', event => {
        if (event.target === ticketModal) {
            closeModal();
        }
    });
    
    ticketSubmitBtn.addEventListener('click', handleTicketSubmit);
    
    // Add event delegation for ticket buttons (added dynamically)
    eventsGrid.addEventListener('click', event => {
        if (event.target.classList.contains('get-tickets')) {
            const eventId = event.target.getAttribute('data-event-id');
            openTicketModal(eventId);
        }
    });
}

// Apply all filters
function applyFilters() {
    const categoryValue = categoryFilter.value;
    const dateValue = dateFilter.value;
    const venueValue = venueFilter.value;
    const searchValue = searchInput.value.trim().toLowerCase();
    
    // Filter events based on selected criteria
    filteredEvents = allEvents.filter(event => {
        // Category filter
        if (categoryValue && event.category !== categoryValue) {
            return false;
        }
        
        // Venue filter
        if (venueValue && event.venue !== venueValue) {
            return false;
        }
        
        // Date filter
        if (dateValue) {
            const eventDate = new Date(event.date);
            const today = new Date();
            
            if (dateValue === 'today') {
                if (!isSameDay(eventDate, today)) return false;
            } else if (dateValue === 'tomorrow') {
                const tomorrow = new Date();
                tomorrow.setDate(today.getDate() + 1);
                if (!isSameDay(eventDate, tomorrow)) return false;
            } else if (dateValue === 'this-weekend') {
                if (!isWeekend(eventDate) || !isWithinNextDays(eventDate, 7)) return false;
            } else if (dateValue === 'this-week') {
                if (!isWithinNextDays(eventDate, 7)) return false;
            } else if (dateValue === 'this-month') {
                if (eventDate.getMonth() !== today.getMonth() || 
                    eventDate.getFullYear() !== today.getFullYear()) return false;
            }
        }
        
        // Search filter
        if (searchValue) {
            const title = event.title?.toLowerCase() || '';
            const description = event.description?.toLowerCase() || '';
            const venue = event.venue?.toLowerCase() || '';
            
            return title.includes(searchValue) || 
                   description.includes(searchValue) || 
                   venue.includes(searchValue);
        }
        
        return true;
    });
    
    renderEvents(filteredEvents);
}

// Clear all filters
function clearFilters() {
    categoryFilter.value = '';
    dateFilter.value = '';
    venueFilter.value = '';
    searchInput.value = '';
    
    // Remove active class from all nav links except "All Events"
    document.querySelectorAll('nav ul li a').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector('nav ul li a[data-filter="all"]').classList.add('active');
    
    filteredEvents = [...allEvents];
    renderEvents(filteredEvents);
}

// Render events to the DOM
function renderEvents(events) {
    // Clear current events
    eventsGrid.innerHTML = '';
    
    if (events.length === 0) {
        noEvents.style.display = 'block';
        return;
    }
    
    noEvents.style.display = 'none';
    
    // Create and append event cards
    events.forEach(event => {
        const eventCard = document.importNode(eventCardTemplate.content, true);
        
        // Set event data
        const imgElement = eventCard.querySelector('.event-image img');
        imgElement.src = event.image_url || '/static/images/default-event.jpg';
        imgElement.alt = event.title;
        
        // Parse and format date
        let eventDate;
        try {
            eventDate = new Date(event.date);
        } catch (e) {
            eventDate = new Date();
        }
        
        const day = eventDate.getDate();
        const month = eventDate.toLocaleString('default', { month: 'short' });
        
        eventCard.querySelector('.day').textContent = day;
        eventCard.querySelector('.month').textContent = month;
        eventCard.querySelector('.event-title').textContent = event.title;
        eventCard.querySelector('.event-venue').textContent = event.venue || 'TBA';
        eventCard.querySelector('.event-time').textContent = event.time || 'Check website for time';
        eventCard.querySelector('.event-description').textContent = event.description || 'No description available';
        eventCard.querySelector('.event-price').textContent = event.price || 'Check website for price';
        
        const ticketButton = eventCard.querySelector('.get-tickets');
        ticketButton.setAttribute('data-event-id', event.id);
        
        eventsGrid.appendChild(eventCard);
    });
}

// Open the ticket modal
function openTicketModal(eventId) {
    currentEventId = eventId;
    emailInput.value = '';
    optInCheckbox.checked = false;
    ticketModal.style.display = 'block';
}

// Close the ticket modal
function closeModal() {
    ticketModal.style.display = 'none';
    currentEventId = null;
}

// Handle ticket submission
async function handleTicketSubmit() {
    if (!currentEventId) return;
    
    const email = emailInput.value.trim();
    const optIn = optInCheckbox.checked;
    
    // Validate email
    if (!email || !validateEmail(email)) {
        alert('Please enter a valid email address.');
        return;
    }
    
    try {
        const response = await fetch('/api/ticket-redirect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email,
                event_id: currentEventId,
                opt_in: optIn
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to process ticket request');
        }
        
        const data = await response.json();
        
        // Close modal and redirect to ticket provider
        closeModal();
        
        // Short delay before redirecting
        setTimeout(() => {
            window.location.href = data.redirect_url;
        }, 300);
    } catch (error) {
        console.error('Error processing ticket request:', error);
        alert('There was an error processing your request. Please try again.');
    }
}

// Validate email format
function validateEmail(email) {
    const re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    return re.test(email);
}

// Helper function to show error messages
function showError(message) {
    eventsGrid.innerHTML = `
        <div class="error-message">
            <i class="fas fa-exclamation-circle"></i>
            <p>${message}</p>
        </div>
    `;
}

// Helper function to check if two dates are the same day
function isSameDay(date1, date2) {
    return date1.getDate() === date2.getDate() &&
           date1.getMonth() === date2.getMonth() &&
           date1.getFullYear() === date2.getFullYear();
}

// Helper function to check if a date is a weekend (Saturday or Sunday)
function isWeekend(date) {
    const day = date.getDay();
    return day === 0 || day === 6;  // 0 is Sunday, 6 is Saturday
}

// Helper function to check if a date is within the next X days
function isWithinNextDays(date, days) {
    const today = new Date();
    const futureDate = new Date();
    futureDate.setDate(today.getDate() + days);
    
    return date >= today && date <= futureDate;
}
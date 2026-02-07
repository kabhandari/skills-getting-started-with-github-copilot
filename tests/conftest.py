"""
Pytest configuration and fixtures for API tests
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client with the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        },
        "Basketball": {
            "description": "Team basketball practice and games",
            "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
            "max_participants": 15,
            "participants": []
        },
        "Soccer": {
            "description": "Competitive soccer training and matches",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
            "max_participants": 22,
            "participants": []
        },
        "Debate Club": {
            "description": "Develop public speaking and analytical skills through debate",
            "schedule": "Wednesdays, 3:30 PM - 5:00 PM",
            "max_participants": 16,
            "participants": []
        },
        "Robotics Club": {
            "description": "Design and build robots for competitions",
            "schedule": "Saturdays, 10:00 AM - 12:00 PM",
            "max_participants": 14,
            "participants": []
        },
        "Art Club": {
            "description": "Explore various art mediums and techniques",
            "schedule": "Fridays, 4:00 PM - 5:30 PM",
            "max_participants": 18,
            "participants": []
        },
        "Theater": {
            "description": "Acting, staging, and performing in theatrical productions",
            "schedule": "Mondays and Thursdays, 3:30 PM - 5:00 PM",
            "max_participants": 25,
            "participants": []
        },
        "Music Band": {
            "description": "Play instruments and perform in the school band",
            "schedule": "Tuesdays, Thursdays, Saturdays, 3:00 PM - 4:30 PM",
            "max_participants": 30,
            "participants": []
        }
    })
    yield

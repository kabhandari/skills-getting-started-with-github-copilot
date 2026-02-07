"""
Tests for the Mergington High School API
"""
import pytest


class TestGetActivities:
    """Tests for the /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        activities = response.json()
        assert len(activities) == 10
        assert "Chess Club" in activities
        assert "Programming Class" in activities

    def test_activity_has_required_fields(self, client):
        """Test that each activity has all required fields"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, details in activities.items():
            assert "description" in details
            assert "schedule" in details
            assert "max_participants" in details
            assert "participants" in details
            assert isinstance(details["participants"], list)

    def test_chess_club_has_initial_participants(self, client):
        """Test that Chess Club starts with initial participants"""
        response = client.get("/activities")
        activities = response.json()
        assert len(activities["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in activities["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in activities["Chess Club"]["participants"]


class TestSignup:
    """Tests for the /activities/{activity_name}/signup endpoint"""

    def test_signup_new_participant(self, client):
        """Test signing up a new participant to an activity"""
        response = client.post(
            "/activities/Basketball/signup?email=alex@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up alex@mergington.edu for Basketball" in data["message"]

    def test_signup_adds_participant_to_activity(self, client):
        """Test that signup actually adds participant to activity list"""
        client.post("/activities/Soccer/signup?email=lucy@mergington.edu")
        
        response = client.get("/activities")
        activities = response.json()
        assert "lucy@mergington.edu" in activities["Soccer"]["participants"]

    def test_signup_duplicate_participant_fails(self, client):
        """Test that signing up the same participant twice fails"""
        # Michael is already in Chess Club
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for a nonexistent activity fails"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    def test_signup_multiple_different_participants(self, client):
        """Test that multiple different participants can sign up"""
        client.post("/activities/Debate Club/signup?email=participant1@mergington.edu")
        client.post("/activities/Debate Club/signup?email=participant2@mergington.edu")
        
        response = client.get("/activities")
        activities = response.json()
        assert len(activities["Debate Club"]["participants"]) == 2


class TestUnregister:
    """Tests for the /activities/{activity_name}/unregister endpoint"""

    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        response = client.post(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered michael@mergington.edu from Chess Club" in data["message"]

    def test_unregister_removes_participant_from_activity(self, client):
        """Test that unregister actually removes participant from activity list"""
        client.post("/activities/Chess Club/unregister?email=michael@mergington.edu")
        
        response = client.get("/activities")
        activities = response.json()
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
        assert len(activities["Chess Club"]["participants"]) == 1

    def test_unregister_nonparticipant_fails(self, client):
        """Test that unregistering someone not in the activity fails"""
        response = client.post(
            "/activities/Chess Club/unregister?email=nonexistent@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]

    def test_unregister_from_nonexistent_activity_fails(self, client):
        """Test that unregistering from a nonexistent activity fails"""
        response = client.post(
            "/activities/Nonexistent Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    def test_unregister_and_signup_again(self, client):
        """Test that a participant can unregister and sign up again"""
        # Unregister
        client.post("/activities/Chess Club/unregister?email=michael@mergington.edu")
        
        # Verify unregistered
        response = client.get("/activities")
        activities = response.json()
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
        
        # Sign up again
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify signed up
        response = client.get("/activities")
        activities = response.json()
        assert "michael@mergington.edu" in activities["Chess Club"]["participants"]


class TestIntegration:
    """Integration tests combining multiple operations"""

    def test_signup_unregister_flow(self, client):
        """Test a complete flow of signup and unregister"""
        email = "integration@mergington.edu"
        
        # Sign up
        response = client.post(f"/activities/Art Club/signup?email={email}")
        assert response.status_code == 200
        
        # Verify signed up
        response = client.get("/activities")
        assert email in response.json()["Art Club"]["participants"]
        
        # Unregister
        response = client.post(f"/activities/Art Club/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify unregistered
        response = client.get("/activities")
        assert email not in response.json()["Art Club"]["participants"]

    def test_multiple_signups_and_activities(self, client):
        """Test signing up for multiple activities and unregistering from some"""
        email = "multi@mergington.edu"
        
        # Sign up for multiple activities
        for activity in ["Theater", "Music Band", "Robotics Club"]:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all signups
        response = client.get("/activities")
        activities = response.json()
        assert email in activities["Theater"]["participants"]
        assert email in activities["Music Band"]["participants"]
        assert email in activities["Robotics Club"]["participants"]
        
        # Unregister from one
        client.post(f"/activities/Music Band/unregister?email={email}")
        
        # Verify
        response = client.get("/activities")
        activities = response.json()
        assert email in activities["Theater"]["participants"]
        assert email not in activities["Music Band"]["participants"]
        assert email in activities["Robotics Club"]["participants"]

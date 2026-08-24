from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import CustomUser


class AuthenticationTests(APITestCase):

    def test_signup_success(self):
        url = reverse("signup")

        data = {
            "username": "candidate1",
            "email": "candidate1@test.com",
            "password": "Test@12345",
            "phone": "9876543210",
            "role": "Candidate"
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CustomUser.objects.count(), 1)

    def test_signup_duplicate_email(self):

        CustomUser.objects.create_user(
            username="user1",
            email="duplicate@test.com",
            password="Test12345",
            role="Candidate"
        )

        url = reverse("signup")

        data = {
            "username": "user2",
            "email": "duplicate@test.com",
            "password": "Test12345",
            "phone": "9999999999",
            "role": "Candidate"
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_job_list(self):

        url = reverse("job-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


from rest_framework.test import APIClient


class SecurityTests(APITestCase):

    def setUp(self):
        self.client = APIClient()

    def test_profile_without_login(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 401)

    def test_create_job_without_login(self):
        response = self.client.post(reverse("create-job"), {})
        self.assertEqual(response.status_code, 401)

    def test_candidate_dashboard_without_login(self):
        response = self.client.get(reverse("candidate-dashboard"))
        self.assertEqual(response.status_code, 401)        
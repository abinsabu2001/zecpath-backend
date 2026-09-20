from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import (
    CustomUser,
    SubscriptionPlan,
    UserSubscription,
    Job,
    Notification,
)


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

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.assertEqual(
            CustomUser.objects.count(),
            1
        )

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

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_job_list(self):

        url = reverse("job-list")

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    def test_job_invalid_salary_range(self):

        employer = CustomUser.objects.create_user(
            username="employer1",
            email="employer@test.com",
            password="Test@12345",
            role="Employer"
        )

        # Create a subscription plan
        plan = SubscriptionPlan.objects.create(
            name="PRO",
            description="Test plan",
            price=0,
            job_post_limit=10,
            ai_analytics=False,
            unlimited_job_posts=False,
            is_active=True
        )

        # Create an active subscription
        UserSubscription.objects.create(
            user=employer,
            plan=plan,
            start_date=timezone.now(),
            status="ACTIVE"
        )

        self.client.force_authenticate(user=employer)

        url = reverse("create-job")

        data = {
            "title": "Python Developer",
            "description": "Backend development job",
            "skills": "Python, Django",
            "experience": 2,
            "salary_min": 50000,
            "salary_max": 30000,
            "location": "Kochi",
            "job_type": "Full Time"
        }

        response = self.client.post(url, data)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_inactive_job_not_returned_in_search(self):

        employer = CustomUser.objects.create_user(
            username="search_employer",
            email="search_employer@test.com",
            password="Test@12345",
            role="Employer"
        )

        # Create active job
        Job.objects.create(
            employer=employer,
            title="Active Python Developer",
            description="Python Django developer",
            skills="Python Django",
            experience=2,
            salary_min=30000,
            salary_max=50000,
            location="Kochi",
            job_type="Full Time",
            status=True
        )

        # Create inactive job
        Job.objects.create(
            employer=employer,
            title="Inactive Developer",
            description="Python Django developer",
            skills="Python Django",
            experience=2,
            salary_min=30000,
            salary_max=50000,
            location="Kochi",
            job_type="Full Time",
            status=False
        )

        response = self.client.get(
            reverse("job-list"),
            {"search": "Python"}
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        results = response.data.get(
            "results",
            response.data
        )

        titles = [
            job["title"]
            for job in results
        ]

        self.assertIn(
            "Active Python Developer",
            titles
        )

        self.assertNotIn(
            "Inactive Developer",
            titles
        )


class SecurityTests(APITestCase):

    def setUp(self):
        self.client = APIClient()

    def test_profile_without_login(self):

        response = self.client.get(
            reverse("profile")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_create_job_without_login(self):

        response = self.client.post(
            reverse("create-job"),
            {}
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_candidate_dashboard_without_login(self):

        response = self.client.get(
            reverse("candidate-dashboard")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_admin_dashboard_without_login(self):

        response = self.client.get(
            reverse("admin-dashboard")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )


class NotificationTests(APITestCase):

    def setUp(self):
        self.client = APIClient()

        self.admin = CustomUser.objects.create_user(
            username="notification_admin",
            email="notification_admin@test.com",
            password="Test@12345",
            role="Admin",
            is_staff=True
        )

        self.employer = CustomUser.objects.create_user(
            username="notification_employer",
            email="notification_employer@test.com",
            password="Test@12345",
            role="Employer"
        )

        self.candidate = CustomUser.objects.create_user(
            username="notification_candidate",
            email="notification_candidate@test.com",
            password="Test@12345",
            role="Candidate"
        )

    def create_notification(self):

        self.client.force_authenticate(
            user=self.admin
        )

        response = self.client.post(
            reverse("create-notification"),
            {
                "user": self.employer.id,
                "title": "Test Notification",
                "message": "This is a test notification.",
                "notification_type": "JOB"
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        return response.data["id"]

    def test_admin_can_create_notification(self):

        notification_id = self.create_notification()

        self.assertTrue(
            Notification.objects.filter(
                id=notification_id,
                user=self.employer
            ).exists()
        )

    def test_user_can_list_own_notifications(self):

        notification_id = self.create_notification()

        notification = Notification.objects.get(
            id=notification_id
        )

        self.client.force_authenticate(
            user=self.employer
        )

        response = self.client.get(
            reverse("notification-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        results = response.data["results"]

        self.assertEqual(
            len(results),
            1
        )

        self.assertEqual(
            results[0]["id"],
            notification.id
        )

    def test_user_cannot_see_other_users_notifications(self):

        self.create_notification()

        self.client.force_authenticate(
            user=self.candidate
        )

        response = self.client.get(
            reverse("notification-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            response.data["count"],
            0
        )

    def test_unread_notification_count(self):

        self.create_notification()

        self.client.force_authenticate(
            user=self.employer
        )

        response = self.client.get(
            reverse("unread-notification-count")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            response.data["unread_count"],
            1
        )

    def test_mark_notification_as_read(self):

        notification_id = self.create_notification()

        self.client.force_authenticate(
            user=self.employer
        )

        response = self.client.patch(
            reverse(
                "mark-notification-read",
                kwargs={
                    "notification_id": notification_id
                }
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        notification = Notification.objects.get(
            id=notification_id
        )

        self.assertTrue(
            notification.is_read
        )

    def test_mark_all_notifications_as_read(self):

        self.create_notification()

        self.client.force_authenticate(
            user=self.admin
        )

        Notification.objects.create(
            user=self.employer,
            title="Second Notification",
            message="Second test notification.",
            notification_type="GENERAL"
        )

        self.client.force_authenticate(
            user=self.employer
        )

        response = self.client.patch(
            reverse("mark-all-notifications-read")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        unread_count = Notification.objects.filter(
            user=self.employer,
            is_read=False
        ).count()

        self.assertEqual(
            unread_count,
            0
        )

    def test_user_can_delete_own_notification(self):

        notification_id = self.create_notification()

        self.client.force_authenticate(
            user=self.employer
        )

        response = self.client.delete(
            reverse(
                "delete-notification",
                kwargs={
                    "notification_id": notification_id
                }
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertFalse(
            Notification.objects.filter(
                id=notification_id
            ).exists()
        )        
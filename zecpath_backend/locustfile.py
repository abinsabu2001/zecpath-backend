from locust import HttpUser, task, between


class CandidateListUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        self.token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzg2Njg5NzUyLCJpYXQiOjE3ODY2ODc5NTIsImp0aSI6IjgzNTljNDc2NjE4NzQ4NjZhYjcwN2Q4NDU5ZDY1MmMwIiwidXNlcl9pZCI6IjIyIn0.AoSCzeg_yKoWMV_WRWHKc0mC0kdJZZ_b2Rlsm74ZGgw"

    @task
    def get_candidate_list(self):
        self.client.get(
            "/api/candidate-list/",
            headers={
                "Authorization": f"Bearer {self.token}"
            }
        )
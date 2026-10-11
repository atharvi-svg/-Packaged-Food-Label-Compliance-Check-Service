
from locust import HttpUser, task, between

class ComplianceUser(HttpUser):
    wait_time = between(1, 2)

    @task(3)
    def health(self):
        self.client.get("/health")

    @task
    def metrics(self):
        self.client.get("/metrics")

    @task
    def submit_label(self):
        self.client.post("/labels/check", json={
            "product_name": "Test Protein Bar",
            "ingredients": "oats, milk protein, cocoa",
            "claims": "source of protein",
            "label_text": "Source of protein"
        })

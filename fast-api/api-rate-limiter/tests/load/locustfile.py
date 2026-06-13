"""
Locust load test for the API Rate Limiter.

Simulates 4 user types hitting each algorithm endpoint.
Run with:
    uv run locust -f tests/load/locustfile.py --headless \
        -u 50 -r 10 -t 30s --host http://localhost:8000 \
        --html tests/load/report.html

Or with the web UI:
    uv run locust -f tests/load/locustfile.py --host http://localhost:8000
    # Open http://localhost:8089
"""

from locust import HttpUser, between, constant_throughput, task


class FixedWindowUser(HttpUser):
    """Hits /api/fixed — expects throttling after 10 req/min per IP."""

    wait_time = between(0.05, 0.2)
    weight = 3

    @task
    def hit_fixed(self):
        with self.client.get(
            "/api/fixed",
            headers={"X-Forwarded-For": f"10.0.{self.user_id % 10}.1"},
            catch_response=True,
        ) as r:
            if r.status_code in (200, 429):
                r.success()  # both are valid — 429 means rate limiting is working
            else:
                r.failure(f"Unexpected status {r.status_code}")


class SlidingWindowUser(HttpUser):
    """Hits /api/sliding — sliding window, no boundary burst."""

    wait_time = between(0.05, 0.2)
    weight = 2

    @task
    def hit_sliding(self):
        with self.client.get(
            "/api/sliding",
            headers={"X-Forwarded-For": f"10.1.{self.user_id % 10}.1"},
            catch_response=True,
        ) as r:
            if r.status_code in (200, 429):
                r.success()
            else:
                r.failure(f"Unexpected status {r.status_code}")


class TokenBucketUser(HttpUser):
    """Hits /api/token — burst allowed, measures burst absorption."""

    wait_time = constant_throughput(5)  # 5 req/sec per user
    weight = 3

    @task
    def hit_token(self):
        with self.client.get(
            "/api/token",
            headers={"X-Forwarded-For": f"10.2.{self.user_id % 10}.1"},
            catch_response=True,
        ) as r:
            if r.status_code in (200, 429):
                r.success()
            else:
                r.failure(f"Unexpected status {r.status_code}")


class LeakyBucketUser(HttpUser):
    """Hits /api/leaky — strict constant rate, any burst denied immediately."""

    wait_time = between(0.02, 0.1)
    weight = 2

    @task
    def hit_leaky(self):
        with self.client.get(
            "/api/leaky",
            headers={"X-Forwarded-For": f"10.3.{self.user_id % 10}.1"},
            catch_response=True,
        ) as r:
            if r.status_code in (200, 429):
                r.success()
            else:
                r.failure(f"Unexpected status {r.status_code}")


class BurstAttacker(HttpUser):
    """
    Simulates a client trying to exploit the boundary burst in fixed window.
    Sends 20 rapid requests. Sliding window should deny the extra ones;
    fixed window may allow up to 2× at the boundary.
    """

    wait_time = between(0.01, 0.05)
    weight = 1

    @task(3)
    def burst_fixed(self):
        with self.client.get(
            "/api/fixed",
            headers={"X-Forwarded-For": "10.9.9.1"},
            catch_response=True,
        ) as r:
            if r.status_code in (200, 429):
                r.success()

    @task(3)
    def burst_sliding(self):
        with self.client.get(
            "/api/sliding",
            headers={"X-Forwarded-For": "10.9.9.1"},
            catch_response=True,
        ) as r:
            if r.status_code in (200, 429):
                r.success()

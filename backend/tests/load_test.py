"""
Load testing script for Syntra API using httpx
Tests performance and scalability of endpoints
"""
import asyncio
import time
import statistics
from typing import List, Dict, Any
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8000"
TOTAL_USERS = 50
DURATION_SECONDS = 120
RAMP_UP_TIME = 30

class LoadTestMetrics:
    """Tracks performance metrics"""

    def __init__(self):
        self.response_times: List[float] = []
        self.status_codes: Dict[int, int] = {}
        self.errors = 0
        self.total_requests = 0
        self.start_time = time.time()
        self.end_time = None

    def record_request(self, duration_ms: float, status_code: int, is_error: bool = False):
        self.response_times.append(duration_ms)
        self.total_requests += 1
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        if is_error:
            self.errors += 1

    def finalize(self):
        self.end_time = time.time()

    def get_summary(self) -> Dict[str, Any]:
        return {
            'total_requests': self.total_requests,
            'total_errors': self.errors,
            'error_rate': (self.errors / self.total_requests * 100) if self.total_requests > 0 else 0,
            'min_response_time_ms': min(self.response_times) if self.response_times else 0,
            'max_response_time_ms': max(self.response_times) if self.response_times else 0,
            'mean_response_time_ms': statistics.mean(self.response_times) if self.response_times else 0,
            'median_response_time_ms': statistics.median(self.response_times) if self.response_times else 0,
            'p95_response_time_ms': statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) > 20 else max(self.response_times) if self.response_times else 0,
            'p99_response_time_ms': statistics.quantiles(self.response_times, n=100)[98] if len(self.response_times) > 100 else max(self.response_times) if self.response_times else 0,
            'status_codes': self.status_codes,
            'duration_seconds': self.end_time - self.start_time if self.end_time else 0,
            'requests_per_second': self.total_requests / (self.end_time - self.start_time) if self.end_time else 0,
        }

class LoadTestUser:
    """Simulates a single user making requests"""

    def __init__(self, user_id: int, metrics: LoadTestMetrics):
        self.user_id = user_id
        self.metrics = metrics
        self.client = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()

    async def make_request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make HTTP request and record metrics"""
        try:
            start = time.time()
            response = await self.client.request(method, f"{BASE_URL}{path}", **kwargs)
            duration = (time.time() - start) * 1000  # Convert to milliseconds

            is_error = response.status_code >= 400
            self.metrics.record_request(duration, response.status_code, is_error)
            return response
        except Exception as e:
            duration = (time.time() - start) * 1000
            self.metrics.record_request(duration, 0, is_error=True)
            return None

    async def run_test_sequence(self, test_duration: int):
        """Run continuous test sequence for specified duration"""
        end_time = time.time() + test_duration

        while time.time() < end_time:
            # Test 1: Health check
            await self.make_request('GET', '/')
            await asyncio.sleep(0.1)

            # Test 2: Health endpoint
            await self.make_request('GET', '/health')
            await asyncio.sleep(0.1)

            # Test 3: Invalid UUID handling
            await self.make_request('GET', '/api/threads/invalid-uuid', headers={'x-org-id': 'also-invalid'})
            await asyncio.sleep(0.1)

            # Test 4: CORS preflight
            await self.make_request('OPTIONS', '/', headers={'Origin': 'http://localhost:3000'})
            await asyncio.sleep(0.2)

async def ramp_up_users(metrics: LoadTestMetrics, target_users: int, ramp_up_duration: int):
    """Gradually increase number of concurrent users"""
    tasks = []
    start_time = time.time()

    for i in range(target_users):
        # Calculate delay for smooth ramp-up
        delay = (i / target_users) * ramp_up_duration

        async def run_user(user_id: int, start_delay: float):
            await asyncio.sleep(start_delay)
            async with LoadTestUser(user_id, metrics) as user:
                remaining_time = DURATION_SECONDS - (time.time() - start_time)
                if remaining_time > 0:
                    await user.run_test_sequence(int(remaining_time))

        tasks.append(run_user(i, delay))

    await asyncio.gather(*tasks)

async def run_load_test():
    """Run the complete load test"""
    print("=" * 80)
    print("SYNTRA API LOAD TEST")
    print("=" * 80)
    print(f"Target Users: {TOTAL_USERS}")
    print(f"Test Duration: {DURATION_SECONDS}s")
    print(f"Ramp-up Time: {RAMP_UP_TIME}s")
    print(f"Base URL: {BASE_URL}")
    print(f"Start Time: {datetime.now().isoformat()}")
    print("=" * 80)
    print()

    metrics = LoadTestMetrics()

    try:
        await ramp_up_users(metrics, TOTAL_USERS, RAMP_UP_TIME)
        metrics.finalize()

        # Print results
        summary = metrics.get_summary()

        print("=" * 80)
        print("LOAD TEST RESULTS")
        print("=" * 80)
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Total Errors: {summary['total_errors']}")
        print(f"Error Rate: {summary['error_rate']:.2f}%")
        print(f"Duration: {summary['duration_seconds']:.2f}s")
        print(f"Requests/Second: {summary['requests_per_second']:.2f}")
        print()
        print("Response Time Statistics (ms):")
        print(f"  Min: {summary['min_response_time_ms']:.2f}")
        print(f"  Mean: {summary['mean_response_time_ms']:.2f}")
        print(f"  Median: {summary['median_response_time_ms']:.2f}")
        print(f"  P95: {summary['p95_response_time_ms']:.2f}")
        print(f"  P99: {summary['p99_response_time_ms']:.2f}")
        print(f"  Max: {summary['max_response_time_ms']:.2f}")
        print()
        print("Status Code Distribution:")
        for status, count in sorted(summary['status_codes'].items()):
            print(f"  {status}: {count}")
        print()
        print("=" * 80)

        # Performance assessment
        print("\nPERFORMANCE ASSESSMENT:")
        print("-" * 80)

        if summary['error_rate'] < 1:
            print("✅ Error Rate: PASS (<1%)")
        elif summary['error_rate'] < 5:
            print("⚠️  Error Rate: WARNING (1-5%)")
        else:
            print("❌ Error Rate: FAIL (>5%)")

        if summary['p95_response_time_ms'] < 500:
            print("✅ P95 Response Time: PASS (<500ms)")
        elif summary['p95_response_time_ms'] < 1000:
            print("⚠️  P95 Response Time: WARNING (500-1000ms)")
        else:
            print("❌ P95 Response Time: FAIL (>1000ms)")

        if summary['p99_response_time_ms'] < 1000:
            print("✅ P99 Response Time: PASS (<1000ms)")
        else:
            print("⚠️  P99 Response Time: WARNING (>1000ms)")

        if summary['requests_per_second'] > 100:
            print(f"✅ Throughput: PASS (>{100} req/s)")
        else:
            print(f"⚠️  Throughput: WARNING (<{100} req/s)")

        print("-" * 80)

        return summary

    except Exception as e:
        print(f"❌ Load test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(run_load_test())

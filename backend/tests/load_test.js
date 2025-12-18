import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const healthCheckDuration = new Trend('health_check_duration');
const threadDuration = new Trend('thread_request_duration');
const errorRate = new Rate('errors');

export let options = {
  stages: [
    { duration: '30s', target: 10 },  // Ramp up to 10 virtual users
    { duration: '1m30s', target: 50 }, // Ramp up to 50 virtual users
    { duration: '2m', target: 50 },    // Stay at 50 virtual users
    { duration: '30s', target: 10 },   // Ramp down to 10 virtual users
    { duration: '30s', target: 0 },    // Ramp down to 0 virtual users
  ],
  thresholds: {
    'health_check_duration': ['p(95)<100'],    // 95th percentile should be below 100ms
    'thread_request_duration': ['p(95)<500'],  // 95th percentile should be below 500ms
    'errors': ['rate<0.1'],                     // Error rate should be below 10%
    'http_req_duration': ['p(95)<1000'],       // 95th percentile of all requests < 1s
    'http_req_failed': ['rate<0.1'],           // HTTP failure rate < 10%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  // Test 1: Health check endpoint
  group('Health Checks', function () {
    const res = http.get(`${BASE_URL}/`);
    healthCheckDuration.add(res.timings.duration);

    check(res, {
      'health check status is 200': (r) => r.status === 200,
      'health check returns ok': (r) => r.json('status') === 'ok',
      'response time < 100ms': (r) => r.timings.duration < 100,
    }) || errorRate.add(1);

    sleep(1);
  });

  // Test 2: Health endpoint
  group('Health Endpoint', function () {
    const res = http.get(`${BASE_URL}/health`);
    healthCheckDuration.add(res.timings.duration);

    check(res, {
      'health endpoint status is 200': (r) => r.status === 200,
      'health endpoint returns healthy': (r) => r.json('status') === 'healthy',
    }) || errorRate.add(1);

    sleep(1);
  });

  // Test 3: Invalid UUID handling (should return 400/404)
  group('Error Handling - Invalid UUID', function () {
    const res = http.get(`${BASE_URL}/api/threads/invalid-uuid`, {
      headers: {
        'x-org-id': 'also-invalid'
      }
    });

    check(res, {
      'invalid uuid returns error': (r) => [400, 404, 422].includes(r.status),
      'error response is structured': (r) => r.json('error') !== undefined,
    }) || errorRate.add(1);

    sleep(1);
  });

  // Test 4: CORS preflight requests
  group('CORS Handling', function () {
    const res = http.options(`${BASE_URL}/`, {
      headers: {
        'Origin': 'http://localhost:3000',
        'Access-Control-Request-Method': 'POST'
      }
    });

    check(res, {
      'options request succeeds': (r) => [200, 204, 405].includes(r.status),
      'cors headers present': (r) => r.headers['access-control-allow-origin'] !== undefined || r.status === 405,
    });

    sleep(1);
  });

  // Test 5: Security header verification
  group('Security Headers', function () {
    const res = http.get(`${BASE_URL}/`);

    check(res, {
      'x-content-type-options header present': (r) => r.headers['x-content-type-options'] !== undefined,
      'x-frame-options header present': (r) => r.headers['x-frame-options'] !== undefined,
      'csp header present': (r) => r.headers['content-security-policy'] !== undefined,
    });

    sleep(1);
  });

  // Test 6: Large payload handling
  group('Input Validation - Large Payload', function () {
    const largePayload = JSON.stringify({
      org_id: '550e8400-e29b-41d4-a716-446655440000',
      title: 'x'.repeat(100000)  // 100KB string
    });

    const res = http.post(`${BASE_URL}/api/threads/`, largePayload, {
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // Should either reject or require auth
    check(res, {
      'large payload handled': (r) => [401, 400, 422].includes(r.status),
      'response time < 500ms even with large payload': (r) => r.timings.duration < 500,
    }) || errorRate.add(1);

    sleep(1);
  });

  // Test 7: Concurrent requests to same endpoint
  group('Concurrent Request Handling', function () {
    const responses = http.batch([
      ['GET', `${BASE_URL}/`, null, { tags: { name: 'health_batch' } }],
      ['GET', `${BASE_URL}/health`, null, { tags: { name: 'health_endpoint_batch' } }],
      ['GET', `${BASE_URL}/`, null, { tags: { name: 'health_batch' } }],
      ['GET', `${BASE_URL}/health`, null, { tags: { name: 'health_endpoint_batch' } }],
    ]);

    check(responses[0], { 'batch requests succeed': (r) => r.status === 200 });
  });

  sleep(2);
}

// Summary calculations
export function teardown(data) {
  console.log('=== Load Test Summary ===');
  console.log('Completed load test with up to 50 concurrent users');
  console.log('Test metrics stored in k6 metrics');
}

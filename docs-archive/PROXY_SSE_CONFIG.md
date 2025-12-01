---
title: Proxy Configuration for Server-Sent Events (SSE)
summary: Documentation file
last_updated: '2025-11-12'
owner: DAC
tags:
- dac
- docs
---

# Proxy Configuration for Server-Sent Events (SSE)

When deploying DAC behind a reverse proxy (Nginx, Apache, etc.), it's critical to disable response buffering for SSE endpoints to ensure low-latency streaming.

## Why This Matters

SSE (Server-Sent Events) requires immediate delivery of each event to the client. If a reverse proxy buffers the response, clients won't see tokens until the buffer fills or the request completes, defeating the purpose of streaming and breaking TTFT (Time To First Token) metrics.

## Nginx Configuration

Add these directives to your SSE endpoint location blocks:

```nginx
# Nginx configuration for SSE streaming endpoints
server {
    listen 80;
    server_name your-domain.com;

    # SSE endpoints (chat/streaming)
    location /api/chat {
        proxy_pass http://backend:8000;

        # Critical for SSE
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;

        # Disable gzip for SSE (interferes with streaming)
        gzip off;

        # Tell Nginx not to buffer (FastCGI/uWSGI)
        add_header X-Accel-Buffering no;

        # Standard proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-lived connections
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # Apply same config to threads endpoint
    location /api/threads/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        gzip off;
        add_header X-Accel-Buffering no;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # Regular API endpoints (buffering OK)
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Apache Configuration

If using Apache with mod_proxy:

```apache
<VirtualHost *:80>
    ServerName your-domain.com

    # SSE endpoints
    <Location /api/chat>
        ProxyPass http://backend:8000/api/chat
        ProxyPassReverse http://backend:8000/api/chat

        # Disable buffering
        SetEnv proxy-nokeepalive 1
        SetEnv proxy-sendchunked 1
        SetEnv proxy-interim-response RFC

        # No compression for SSE
        SetEnv no-gzip 1
    </Location>

    <Location /api/threads/>
        ProxyPass http://backend:8000/api/threads/
        ProxyPassReverse http://backend:8000/api/threads/
        SetEnv proxy-nokeepalive 1
        SetEnv proxy-sendchunked 1
        SetEnv proxy-interim-response RFC
        SetEnv no-gzip 1
    </Location>
</VirtualHost>
```

## Caddy Configuration

Caddy automatically handles SSE well, but you can be explicit:

```caddyfile
your-domain.com {
    # SSE endpoints
    handle /api/chat {
        reverse_proxy backend:8000 {
            flush_interval -1
        }
    }

    handle /api/threads/* {
        reverse_proxy backend:8000 {
            flush_interval -1
        }
    }

    # Other endpoints
    handle /api/* {
        reverse_proxy backend:8000
    }
}
```

## Verification

After configuring your proxy, verify SSE streaming works correctly:

1. **Manual test with curl:**
   ```bash
   curl -N -H "Accept: text/event-stream" \
        http://your-domain.com/api/chat \
        -d '{"messages":[{"role":"user","content":"test"}]}'
   ```

   You should see events appear immediately, not after a delay.

2. **Check response headers:**
   ```bash
   curl -I -H "Accept: text/event-stream" \
        http://your-domain.com/api/chat
   ```

   Look for:
   - `Content-Type: text/event-stream`
   - `X-Accel-Buffering: no` (Nginx)
   - No `Content-Length` header (streaming response)

3. **Browser DevTools:**
   - Open Network tab
   - Trigger a chat request
   - Look for the request in the network log
   - Click on it and check the "EventStream" or "Messages" tab
   - Events should appear in real-time

4. **TTFT test:**
   ```bash
   node scripts/ttft_probe.mjs
   ```

   If TTFT is high (>2000ms for first token), buffering may still be enabled.

## Common Issues

### Issue: Events delayed by 4-8KB
**Cause:** Proxy is buffering despite config
**Fix:**
- Check for multiple proxy layers (load balancer + nginx)
- Verify `proxy_buffering off` is in the right location block
- Check for CloudFlare or CDN caching (disable for SSE paths)

### Issue: Connection drops after 60s
**Cause:** Default proxy timeouts too short
**Fix:**
- Increase `proxy_read_timeout` and `proxy_send_timeout` in Nginx
- Set `ProxyTimeout` in Apache

### Issue: Compressed/garbled events
**Cause:** gzip compression enabled
**Fix:**
- Add `gzip off;` to Nginx location
- Set `SetEnv no-gzip 1` in Apache

## Testing in CI/CD

Add a smoke test to your deployment pipeline:

```bash
#!/bin/bash
# test-sse-streaming.sh

URL="${1:-https://your-domain.com/api/chat}"

echo "Testing SSE streaming at: $URL"

# Send request and measure time to first event
start=$(date +%s%3N)
first_event=$(curl -sN -H "Accept: text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"hi"}]}' \
  "$URL" | head -n 1)
end=$(date +%s%3N)

ttft=$((end - start))

echo "Time to first event: ${ttft}ms"
echo "First event: $first_event"

if [ "$ttft" -gt 2000 ]; then
  echo "ERROR: TTFT too high, buffering may be enabled"
  exit 1
fi

echo "OK: SSE streaming working correctly"
```

## Best Practices

1. **Separate location blocks** for SSE endpoints (don't apply buffering=off globally)
2. **Monitor TTFT** in production to catch proxy misconfigurations
3. **Test after deployments** to ensure config wasn't overridden
4. **Document SSE paths** so ops team knows which endpoints need special handling
5. **Use CDN bypass** for SSE paths if using CloudFlare/Fastly

## Production Checklist

- [ ] Nginx/Apache config updated with `proxy_buffering off`
- [ ] Gzip disabled for SSE endpoints
- [ ] Proxy timeouts increased (≥300s)
- [ ] Manual curl test passes
- [ ] TTFT test shows <1500ms p95
- [ ] Smoke test added to deployment pipeline
- [ ] CDN bypass configured for SSE paths (if applicable)
- [ ] Documentation updated with SSE endpoint paths
- [ ] Monitoring alerts for high TTFT (>2000ms)

## References

- [MDN: Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [Nginx SSE Guide](https://www.nginx.com/blog/event-driven-data-management-nginx/)
- [EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)

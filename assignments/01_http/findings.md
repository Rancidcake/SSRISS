# Assignment 01 — HTTP Detective Findings

## Probe Empirical Results

The HTTP probe (`http_probe.py`) was executed across 5 representative endpoints using `requests` with an explicit 10-second timeout and custom `User-Agent: WebMonitor/1.0 (JNU Academic Monitoring)`.

### Summary Table

| Target Description | Requested URL | Final URL | Status Code | Content-Type | Content Length | Redirects | Is HTML |
|---|---|---|---|---|---|---|---|
| **JNU Homepage** | `https://www.jnu.ac.in` | `https://www.jnu.ac.in/` | `200` | `text/html; charset=UTF-8` | 135,580 B | 0 | Yes |
| **HTTP -> HTTPS** | `http://www.jnu.ac.in` | `http://www.jnu.ac.in/` | `200` | `text/html; charset=UTF-8` | 135,578 B | 0 | Yes |
| **JSON Test** | `https://httpbin.org/json` | `https://httpbin.org/json` | `200` | `application/json` | 429 B | 0 | No |
| **404 Endpoint** | `https://www.jnu.ac.in/nonexistent_page_12345` | `https://www.jnu.ac.in/nonexistent_page_12345` | `404` | `text/html; charset=UTF-8` | 46,691 B | 0 | Yes |
| **robots.txt** | `https://www.jnu.ac.in/robots.txt` | `https://www.jnu.ac.in/robots.txt` | `200` | `text/plain; charset=UTF-8` | 2,027 B | 0 | No |

---

## Detailed HTTP Response Snippets

### 1. JNU Homepage (`https://www.jnu.ac.in`)
- **Server Header**: `Apache`
- **Cache-Control**: `must-revalidate, no-cache, private`
- **Body Preview**:
  ```html
  <!DOCTYPE html>
  <html lang="en" dir="ltr">
    <head>
      <meta charset="utf-8" />
      <meta name="Generator" content="Drupal 10 (https://www.drupal.org)" />
  ```

### 2. JSON Test Endpoint (`https://httpbin.org/json`)
- **Server Header**: `gunicorn/19.9.0`
- **Body Preview**:
  ```json
  {
    "slideshow": {
      "author": "Yours Truly", 
      "date": "date of publication", 
      "slides": [...]
    }
  }
  ```

### 3. Robots.txt (`https://www.jnu.ac.in/robots.txt`)
- **Server Header**: `Apache`
- **Cache-Control**: `max-age=31536000`
- **Body Preview**:
  ```text
  #
  # robots.txt
  #
  # This file is to prevent the crawling and indexing of certain parts
  # of your site by web crawlers...
  ```

---

## HTTP Conceptual Questions & Analysis

### 1. What is the difference between the requested URL and final URL?
The **requested URL** is the target address submitted by the client initiating the HTTP request (e.g., `http://www.jnu.ac.in`). The **final URL** is the location where the client landed after server-side redirects (`301 Moved Permanently`, `302 Found`, etc.) or path normalization (e.g., appending a trailing slash `/`). Tracking both is critical for URL canonicalization and resolving relative links accurately.

### 2. How can your program determine whether the server returned HTML?
By inspecting the `Content-Type` header of the HTTP response:
```python
is_html = "text/html" in response.headers.get("Content-Type", "").lower()
```
If `Content-Type` contains `text/html`, the response body contains markup intended for DOM parsing. If it contains `application/json`, `application/pdf`, or `text/plain`, attempting HTML DOM selector parsing will fail or yield invalid results.

### 3. What should a crawler do after receiving HTTP `429 Too Many Requests`?
Receiving `429` indicates the target server's rate limiter has been triggered:
1. **Respect `Retry-After` Header**: Check if the server included a `Retry-After` header specifying seconds or an HTTP-date.
2. **Exponential Backoff with Jitter**: If no header is present, back off exponentially (e.g., wait 2s, 4s, 8s, 16s with random jitter) before retrying.
3. **Reduce Concurrency**: Lower request frequency across the entire monitoring pipeline.

### 4. What should your crawler do after receiving HTTP `403 Forbidden`?
A `403` status means server access control explicitly denied the request.
1. **Do NOT attempt evasion**: Never attempt CAPTCHA bypassing, header spoofing, or proxy rotation to circumvent server access boundaries.
2. **Log & Quarantine**: Record the forbidden URL in logs/database with error status `403` and cease further automated polling on that specific resource path.
3. **Audit Surface**: Verify whether the endpoint requires authentication or if public alternative feeds (like RSS/Sitemaps) exist.

### 5. Why should every HTTP request have an explicit timeout?
Without a timeout (`timeout=None`), a Python socket operation will block indefinitely if the server accepts the connection but drops response transmission or hangs. A missing timeout can lock up worker threads/processes permanently, draining system resources and halting monitoring pipelines.

### 6. Why is repeatedly retrying a failing endpoint dangerous?
1. **Denial-of-Service Risk**: Tight retry loops act like a distributed denial-of-service (DDoS) attack on university infrastructure.
2. **IP Banning**: Triggers automated firewall rules (e.g., fail2ban / Cloudflare), causing persistent IP blocks.
3. **Resource Exhaustion**: Wastes network bandwidth, CPU cycles, and thread pools on unproductive request cycles.

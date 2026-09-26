#!/usr/bin/env python3
"""
HTTP Detective - Assignment 01
Probes target URLs and extracts key HTTP response metadata safely.
"""

import sys
import json
from typing import Dict, Any
import requests

DEFAULT_USER_AGENT = "WebMonitor/1.0 (JNU Academic Monitoring)"
DEFAULT_TIMEOUT = 10


def probe_url(url: str, user_agent: str = DEFAULT_USER_AGENT, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """
    Sends an HTTP GET request to a URL with timeout and custom User-Agent,
    returning structured response metadata.
    """
    headers = {"User-Agent": user_agent}
    result: Dict[str, Any] = {
        "requested_url": url,
        "final_url": None,
        "status_code": None,
        "content_type": None,
        "content_length": None,
        "is_html": False,
        "redirect_history": [],
        "selected_response_headers": {},
        "first_200_characters_of_body": "",
        "error": None
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        result["final_url"] = response.url
        result["status_code"] = response.status_code

        # Redirect history capture
        result["redirect_history"] = [
            {"status_code": r.status_code, "url": r.url, "location": r.headers.get("Location")}
            for r in response.history
        ]

        # Header extraction
        content_type = response.headers.get("Content-Type", "")
        result["content_type"] = content_type
        result["is_html"] = "text/html" in content_type.lower()
        
        # Content length handling (from header or actual body size)
        content_len_header = response.headers.get("Content-Length")
        if content_len_header and content_len_header.isdigit():
            result["content_length"] = int(content_len_header)
        else:
            result["content_length"] = len(response.content)

        # Selected relevant response headers
        headers_of_interest = ["Server", "Date", "Cache-Control", "Content-Encoding", "Strict-Transport-Security"]
        result["selected_response_headers"] = {
            h: response.headers[h] for h in headers_of_interest if h in response.headers
        }

        # First 200 characters of body text
        result["first_200_characters_of_body"] = response.text[:200]

    except requests.Timeout:
        result["error"] = f"Request timed out after {timeout} seconds."
    except requests.ConnectionError:
        result["error"] = f"Failed to connect to host at {url}."
    except requests.RequestException as e:
        result["error"] = f"HTTP request failed: {str(e)}"
    
    return result


def main():
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.jnu.ac.in"
    print(f"[*] Probing URL: {target_url}\n")
    info = probe_url(target_url)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()

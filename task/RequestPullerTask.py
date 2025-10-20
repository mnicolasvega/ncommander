from task.BaseTask import BaseTask
from typing import Any, Dict, List
import requests

"""
Fetches the HTML of a website provided in the constructor.
"""
class RequestPullerTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        try:
            url = carry['url']
            self._print(f"Fetching URL: {url}")
            resp = requests.get(url)
            status = resp.status_code
            self._print(f"Fetch status: {status}")
            html = resp.text if resp.ok else ""
            return {
                "url": url,
                "status_code": status,
                "ok": resp.ok,
                "html": html,
            }
        except Exception as e:
            self._print(f"Error fetching '{url}': {e}")
            return {
                "url": url,
                "status_code": None,
                "ok": False,
                "html": "",
                "error": str(e),
            }

    def text_output(self, data: Dict[str, Any]) -> str:
        if not data.get("ok"):
            return f"Failed to fetch: {data.get('url')} ({data.get('error', 'unknown error')})"
        # Keep text output short
        snippet = data['html']
        return f"Fetched {data.get('url')} (status {data.get('status_code')}):\n{snippet}"

    def html_output(self, data: Dict[str, Any]) -> str:
        # Return the fetched HTML directly so the renderer can display it as-is.
        # If the fetch failed, return a minimal error page.
        if data.get("ok") and data.get("html"):
            return data["html"]
        return f"<html><body><h3>Failed to fetch</h3><p>URL: {data.get('url')}</p><p>Error: {data.get('error', 'unknown error')}</p></body></html>"

    def dependencies(self) -> List[str]:
        return ["requests"]

    def requires_connection(self) -> bool:
        return True

    def max_time_expected(self) -> float | None:
        return self._timeout + 2.0

    def interval(self) -> int:
        return 60

    def name(self) -> str:
        return "request_puller"

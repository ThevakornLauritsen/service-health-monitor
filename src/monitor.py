import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.json"
REPORT_FILE = PROJECT_ROOT / "reports" / "health-report.json"


def load_config():
    """Load monitoring targets from the configuration file."""
    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def check_service(service):
    """Check an HTTP service and return its health information."""
    started = time.monotonic()

    result = {
        "service": service["name"],
        "url": service["url"],
        "status_code": None,
        "response_time_ms": None,
        "status": "unhealthy",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "error": None
    }

    request = Request(
        service["url"],
        headers={"User-Agent": "ServiceHealthMonitor/1.0"}
    )

    try:
        with urlopen(request, timeout=service["timeout"]) as response:
            result["status_code"] = response.status

    except HTTPError as error:
        result["status_code"] = error.code

    except (URLError, TimeoutError, OSError) as error:
        result["error"] = str(error)

    elapsed = (time.monotonic() - started) * 1000
    result["response_time_ms"] = round(elapsed, 2)

    if result["status_code"] is not None:
        if 200 <= result["status_code"] < 400:
            result["status"] = "healthy"
        else:
            result["error"] = f"HTTP status {result['status_code']}"

    return result


def main():
    """Run all configured health checks and generate a JSON report."""
    config = load_config()
    results = []

    for service in config["services"]:
        result = check_service(service)
        results.append(result)

        print(
            f'{result["service"]}: '
            f'{result["status"]} '
            f'({result["response_time_ms"]} ms)'
        )

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with REPORT_FILE.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=4)

    print(f"\nReport saved to: {REPORT_FILE}")

    all_healthy = all(
        result["status"] == "healthy" for result in results
    )

    return 0 if all_healthy else 1


if __name__ == "__main__":
    sys.exit(main())
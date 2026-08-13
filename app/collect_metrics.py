import os
import sys
import time
import csv
from datetime import datetime

sys.path.append(
    os.path.dirname(os.path.abspath(__file__))
)

from prometheus_collector import PrometheusCollector


PROMETHEUS_URL = "http://localhost:9090"

OUTPUT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "datasets",
    "processed",
    "prometheus_metrics.csv"
)

INTERVAL = 15


def normalize_metrics(metrics):

    rows = {}

    for metric_name, values in metrics.items():

        if not isinstance(values, list):
            continue

        for item in values:

            if not isinstance(item, dict):
                continue

            pod = item.get("pod")
            value = item.get("value")

            if not pod:
                continue

            if pod not in rows:
                rows[pod] = {
                    "timestamp": datetime.now().isoformat(),
                    "pod": pod
                }

            rows[pod][metric_name] = value

    return list(rows.values())


def save_metrics(rows):

    if not rows:
        print("WARNING: No pod data could be extracted.")
        return

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    fieldnames = set()

    for row in rows:
        fieldnames.update(row.keys())

    fieldnames = list(fieldnames)

    file_exists = os.path.exists(OUTPUT_FILE)

    with open(
        OUTPUT_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        if not file_exists:
            writer.writeheader()

        writer.writerows(rows)


def main():

    print("=" * 70)
    print("AIOPS PROMETHEUS METRIC COLLECTION")
    print("=" * 70)

    print(f"Collection interval: {INTERVAL} seconds")
    print(f"Output: {OUTPUT_FILE}")

    collector = PrometheusCollector(
        prometheus_url=PROMETHEUS_URL
    )

    while True:

        print("\nCollecting metrics...")

        try:

            metrics = collector.collect_pod_metrics()

            rows = normalize_metrics(metrics)

            if rows:

                save_metrics(rows)

                print(
                    f"Collected {len(rows)} pod(s)"
                )

                for row in rows:
                    print(
                        f"Pod: {row.get('pod')} | "
                        f"CPU: {row.get('cpu_usage')} | "
                        f"Memory: {row.get('memory_usage')} MB"
                    )

                print(
                    f"Saved to: {OUTPUT_FILE}"
                )

            else:

                print("No metrics collected.")

        except KeyboardInterrupt:

            print("\nCollection stopped.")

            break

        except Exception as e:

            print("\nERROR:")
            print(type(e).__name__)
            print(e)

        print(
            f"\nWaiting {INTERVAL} seconds..."
        )

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
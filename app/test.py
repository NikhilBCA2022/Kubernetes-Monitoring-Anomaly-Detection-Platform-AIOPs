
from prometheus_collector import PrometheusCollector


collector = PrometheusCollector()

data = collector.collect_pod_metrics()


for metric_name, values in data.items():

    print("\n")
    print("=" * 80)
    print(metric_name.upper())
    print("=" * 80)

    if not values:
        print("NO DATA")
        continue

    for item in values:

        print(
            f"Pod: {item['pod']:<50} "
            f"Value: {item['value']}"
        )


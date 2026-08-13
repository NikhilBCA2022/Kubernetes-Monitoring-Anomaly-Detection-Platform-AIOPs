
"""
Prometheus Collector for AIOps Platform.

Collects the eight metrics used by the AIOps platform:

    1. cpu_usage
    2. memory_usage
    3. disk_usage
    4. network_latency
    5. request_rate
    6. pod_restarts
    7. error_rate
    8. response_time

Prometheus:
    http://localhost:9090

Kubernetes namespace:
    aiops
"""

import requests
from urllib.parse import urljoin


class PrometheusCollector:
    """
    Collect Kubernetes and application metrics from Prometheus.
    """

    def __init__(self, prometheus_url="http://localhost:9090", timeout=10):
        self.prometheus_url = prometheus_url.rstrip("/")
        self.timeout = timeout

    # ============================================================
    # PROMETHEUS QUERY
    # ============================================================

    def query(self, promql):
        """
        Execute an instant PromQL query.

        Returns:
            list: Prometheus result list.
        """

        url = urljoin(
            self.prometheus_url + "/",
            "api/v1/query"
        )

        try:
            response = requests.get(
                url,
                params={"query": promql},
                timeout=self.timeout
            )

            response.raise_for_status()

            data = response.json()

            if data.get("status") != "success":
                print("Prometheus query failed:", data)
                return []

            return data.get("data", {}).get("result", [])

        except requests.exceptions.RequestException as exc:
            print(f"Prometheus connection error: {exc}")
            return []

        except ValueError as exc:
            print(f"Invalid Prometheus JSON response: {exc}")
            return []

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _extract_value(item):
        """
        Safely extract a numeric value from a Prometheus result.
        """

        try:
            return float(item["value"][1])
        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError
        ):
            return None

    def _pod_values(self, result):
        """
        Convert Prometheus results into:

            [
                {
                    "pod": "...",
                    "value": 123.0
                }
            ]

        Intended for pod-level metrics.
        """

        output = []

        for item in result or []:

            metric = item.get("metric", {})

            pod = (
                metric.get("pod")
                or metric.get("pod_name")
            )

            # Ignore results that are not pod-level.
            if not pod:
                continue

            value = self._extract_value(item)

            if value is None:
                continue

            output.append({
                "pod": pod,
                "value": value
            })

        return output

    def _node_values(self, result):
        """
        Convert node-exporter results into:

            [
                {
                    "node": "...",
                    "value": 123.0
                }
            ]

        Node metrics commonly contain:
            instance = 10.x.x.x:9100
        """

        output = []

        for item in result or []:

            metric = item.get("metric", {})

            node = (
                metric.get("node")
                or metric.get("instance")
                or metric.get("nodename")
                or "unknown"
            )

            value = self._extract_value(item)

            if value is None:
                continue

            output.append({
                "node": node,
                "value": value
            })

        return output

    def _scalar_value(self, result):
        """
        Extract the first scalar/vector value returned by Prometheus.
        """

        if not result:
            return None

        try:

            item = result[0]

            if "value" in item:
                return float(item["value"][1])

            if "values" in item and item["values"]:
                return float(item["values"][-1][1])

        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError
        ):
            return None

        return None

    # ============================================================
    # CPU
    # ============================================================

    def cpu_usage(self):
        """
        CPU usage percentage per pod.

        The raw Prometheus value from:

            rate(container_cpu_usage_seconds_total[5m])

        represents CPU cores being consumed.

        Multiplying by 100 converts:
            1.0 core -> 100%
            0.5 core -> 50%
            0.05 core -> 5%

        This is percentage of one CPU core.
        """

        query = """
        100 *
        sum by (pod) (
            rate(
                container_cpu_usage_seconds_total{
                    namespace="aiops",
                    container!="",
                    container!="POD",
                    pod!=""
                }[5m]
            )
        )
        """

        result = self.query(query)

        values = self._pod_values(result)

        return values

    # ============================================================
    # MEMORY
    # ============================================================

    def memory_usage(self):
        """
        Memory usage percentage per pod.

        Attempts:

            working_set / memory_limit * 100

        If Kubernetes memory limits are unavailable, falls back
        to memory usage in MiB.
        """

        # --------------------------------------------------------
        # Preferred: percentage of configured memory limit
        # --------------------------------------------------------

        query = """
        100 *
        (
            sum by (pod) (
                container_memory_working_set_bytes{
                    namespace="aiops",
                    container!="",
                    container!="POD",
                    pod!=""
                }
            )
        )
        /
        (
            sum by (pod) (
                kube_pod_container_resource_limits{
                    namespace="aiops",
                    resource="memory",
                    unit="byte",
                    pod!=""
                }
            )
        )
        """

        result = self.query(query)

        values = self._pod_values(result)

        if values:
            return values

        # --------------------------------------------------------
        # Fallback: memory in MiB
        # --------------------------------------------------------

        fallback_query = """
        sum by (pod) (
            container_memory_working_set_bytes{
                namespace="aiops",
                container!="",
                container!="POD",
                pod!=""
            }
        ) / 1024 / 1024
        """

        return self._pod_values(
            self.query(fallback_query)
        )

    # ============================================================
    # DISK
    # ============================================================

    def disk_usage(self):
        """
        Node filesystem usage percentage.

        IMPORTANT:
        This is node disk usage, not pod disk usage.

        Therefore the returned objects use:

            {
                "node": "...",
                "value": ...
            }

        instead of incorrectly calling the node an "pod".
        """

        query = """
        100 *
        (
            sum by (instance) (
                node_filesystem_size_bytes{
                    mountpoint="/",
                    fstype!~"tmpfs|overlay"
                }
            )
            -
            sum by (instance) (
                node_filesystem_avail_bytes{
                    mountpoint="/",
                    fstype!~"tmpfs|overlay"
                }
            )
        )
        /
        sum by (instance) (
            node_filesystem_size_bytes{
                mountpoint="/",
                fstype!~"tmpfs|overlay"
            }
        )
        """

        result = self.query(query)

        values = self._node_values(result)

        if values:
            return values

        # --------------------------------------------------------
        # Optional container filesystem fallback
        # --------------------------------------------------------

        fallback_query = """
        100 *
        sum by (pod) (
            container_fs_usage_bytes{
                namespace="aiops",
                container!="",
                container!="POD",
                pod!=""
            }
        )
        /
        sum by (pod) (
            container_fs_limit_bytes{
                namespace="aiops",
                container!="",
                container!="POD",
                pod!=""
            }
        )
        """

        return self._pod_values(
            self.query(fallback_query)
        )

    # ============================================================
    # NETWORK LATENCY
    # ============================================================

    def network_latency(self):
        """
        Application request latency per pod in milliseconds.

        Uses the Flask request duration histogram.

        NOTE:
        This is application-level request latency, not ICMP/network
        packet latency. It is a useful proxy for service latency
        when an actual network probe metric is unavailable.
        """

        query = """
        1000 *
        (
            sum by (pod) (
                rate(
                    flask_http_request_duration_seconds_sum{
                        namespace="aiops"
                    }[5m]
                )
            )
            /
            sum by (pod) (
                rate(
                    flask_http_request_duration_seconds_count{
                        namespace="aiops"
                    }[5m]
                )
            )
        )
        """

        result = self.query(query)

        values = self._pod_values(result)

        if values:
            return values

        # --------------------------------------------------------
        # Fallback to network receive activity
        # --------------------------------------------------------

        fallback_query = """
        sum by (pod) (
            rate(
                container_network_receive_bytes_total{
                    namespace="aiops",
                    pod!=""
                }[5m]
            )
        )
        """

        return self._pod_values(
            self.query(fallback_query)
        )

    # ============================================================
    # REQUEST RATE
    # ============================================================

    def request_rate(self):
        """
        HTTP requests per second across the AIOps service.

        Uses:

            flask_http_request_duration_seconds_count
        """

        query = """
        sum(
            rate(
                flask_http_request_duration_seconds_count{
                    namespace="aiops"
                }[5m]
            )
        )
        """

        result = self.query(query)

        value = self._scalar_value(result)

        if value is None:
            return []

        return [
            {
                "pod": "cluster",
                "value": float(value)
            }
        ]

    # ============================================================
    # POD RESTARTS
    # ============================================================

    def pod_restarts(self):
        """
        Current restart count per pod.
        """

        query = """
        sum by (pod) (
            kube_pod_container_status_restarts_total{
                namespace="aiops",
                pod!=""
            }
        )
        """

        return self._pod_values(
            self.query(query)
        )

    # ============================================================
    # ERROR RATE
    # ============================================================

    def error_rate(self):
        """
        HTTP 5xx requests per second.

        Returns:

            {
                "pod": "cluster",
                "value": 0.0
            }

        when no 5xx traffic exists.
        """

        query = """
        sum(
            rate(
                flask_http_request_duration_seconds_count{
                    namespace="aiops",
                    status=~"5.."
                }[5m]
            )
        )
        """

        result = self.query(query)

        value = self._scalar_value(result)

        if value is None:
            value = 0.0

        return [
            {
                "pod": "cluster",
                "value": float(value)
            }
        ]

    # ============================================================
    # RESPONSE TIME
    # ============================================================

    def response_time(self):
        """
        Average HTTP response time in milliseconds.

        Formula:

            rate(duration_sum)
            ------------------
            rate(duration_count)

        Prometheus duration is stored in seconds,
        therefore the final result is multiplied by 1000.
        """

        query = """
        (
            sum(
                rate(
                    flask_http_request_duration_seconds_sum{
                        namespace="aiops"
                    }[5m]
                )
            )
            /
            sum(
                rate(
                    flask_http_request_duration_seconds_count{
                        namespace="aiops"
                    }[5m]
                )
            )
        )
        """

        result = self.query(query)

        value = self._scalar_value(result)

        if value is None:
            return []

        return [
            {
                "pod": "cluster",
                "value": float(value) * 1000.0
            }
        ]

    # ============================================================
    # ALL POD METRICS
    # ============================================================

    def collect_pod_metrics(self):
        """
        Collect all eight AIOps metrics.

        Returns:

            {
                "cpu_usage": [...],
                "memory_usage": [...],
                "disk_usage": [...],
                "network_latency": [...],
                "request_rate": [...],
                "pod_restarts": [...],
                "error_rate": [...],
                "response_time": [...]
            }
        """

        return {
            "cpu_usage": self.cpu_usage(),
            "memory_usage": self.memory_usage(),
            "disk_usage": self.disk_usage(),
            "network_latency": self.network_latency(),
            "request_rate": self.request_rate(),
            "pod_restarts": self.pod_restarts(),
            "error_rate": self.error_rate(),
            "response_time": self.response_time()
        }


# ================================================================
# LOCAL TEST
# ================================================================

if __name__ == "__main__":

    collector = PrometheusCollector(
        "http://localhost:9090"
    )

    metrics = collector.collect_pod_metrics()

    print()
    print("=" * 70)
    print("AIOPS PROMETHEUS METRICS")
    print("=" * 70)

    for metric_name, values in metrics.items():

        print()
        print("-" * 70)
        print(metric_name)
        print("-" * 70)

        if not values:
            print("NO DATA")
            continue

        for item in values:
            print(item)

    print()
    print("=" * 70)
    print("COLLECTION COMPLETE")
    print("=" * 70)


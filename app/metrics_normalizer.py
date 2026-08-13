import pandas as pd
from datetime import datetime


class MetricsNormalizer:

    def __init__(self):
        pass

    # ==========================================================
    # CONVERT COLLECTOR RESULT TO POD -> VALUE
    # ==========================================================

    def _to_pod_dict(self, metric_data):
        """
        Converts:

        [
            {"pod": "pod-1", "value": 10},
            {"pod": "pod-2", "value": 20}
        ]

        into:

        {
            "pod-1": 10,
            "pod-2": 20
        }
        """

        result = {}

        if not metric_data:
            return result

        if not isinstance(metric_data, list):
            return result

        for item in metric_data:

            if not isinstance(item, dict):
                continue

            pod = item.get("pod")
            value = item.get("value")

            if pod is None:
                continue

            try:
                value = float(value)
            except (TypeError, ValueError):
                continue

            result[pod] = value

        return result

    # ==========================================================
    # NORMALIZE ALL METRICS
    # ==========================================================

    def normalize(self, metrics):

        if not metrics:
            print("WARNING: No metrics received.")
            return pd.DataFrame()

        # ------------------------------------------------------
        # Convert every metric into:
        #
        # metric_name -> {pod: value}
        # ------------------------------------------------------

        normalized = {}

        for metric_name, metric_data in metrics.items():

            normalized[metric_name] = self._to_pod_dict(
                metric_data
            )

        # ------------------------------------------------------
        # Find all pods
        # ------------------------------------------------------

        pods = set()

        for metric_name, pod_data in normalized.items():

            pods.update(pod_data.keys())

        if not pods:

            print("WARNING: No pod data could be extracted.")

            # Debug information
            print("\nReceived metrics:")

            for metric_name, metric_data in metrics.items():

                print(
                    f"{metric_name}: "
                    f"type={type(metric_data)}, "
                    f"length={len(metric_data) if isinstance(metric_data, list) else 'N/A'}"
                )

            return pd.DataFrame()

        print(f"\nPods detected: {len(pods)}")

        for pod in sorted(pods):
            print(f"  {pod}")

        # ------------------------------------------------------
        # Create one row per pod
        # ------------------------------------------------------

        rows = []

        timestamp = datetime.now().isoformat()

        for pod in sorted(pods):

            row = {
                "timestamp": timestamp,
                "pod": pod
            }

            # --------------------------------------------------
            # Add every metric
            # --------------------------------------------------

            for metric_name, pod_data in normalized.items():

                value = pod_data.get(pod)

                if value is None:
                    value = 0.0

                row[metric_name] = value

            rows.append(row)

        # ------------------------------------------------------
        # Create dataframe
        # ------------------------------------------------------

        df = pd.DataFrame(rows)

        # ------------------------------------------------------
        # Ensure numeric columns
        # ------------------------------------------------------

        for column in df.columns:

            if column not in ["timestamp", "pod"]:

                df[column] = pd.to_numeric(
                    df[column],
                    errors="coerce"
                ).fillna(0.0)

        print(
            f"\nNormalizer produced {len(df)} rows "
            f"and {len(df.columns)} columns."
        )

        return df
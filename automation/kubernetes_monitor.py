
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException


class KubernetesMonitor:

    def __init__(self, namespace="aiops"):

        self.namespace = namespace

        try:
            # Use in-cluster configuration when running inside AKS.
            config.load_incluster_config()

            print("Kubernetes configuration: IN-CLUSTER")

        except Exception:

            # Use local kubeconfig when running from your PC.
            config.load_kube_config()

            print("Kubernetes configuration: LOCAL")

        self.core_api = client.CoreV1Api()

    # ============================================================
    # GET ALL PODS
    # ============================================================

    def get_pods(self):

        try:

            pods = self.core_api.list_namespaced_pod(
                namespace=self.namespace
            )

            return pods.items

        except ApiException as exc:

            print(
                "Kubernetes API error:",
                exc
            )

            return []

    # ============================================================
    # GET POD INFORMATION
    # ============================================================

    def get_pod_info(self, pod):

        restart_count = 0
        container_states = []

        if pod.status.container_statuses:

            for container in pod.status.container_statuses:

                restart_count += (
                    container.restart_count or 0
                )

                state = container.state

                state_info = {
                    "container": container.name,
                    "running": state.running is not None,
                    "waiting": state.waiting is not None,
                    "terminated": state.terminated is not None
                }

                if state.terminated:

                    state_info["reason"] = (
                        state.terminated.reason
                    )

                    state_info["exit_code"] = (
                        state.terminated.exit_code
                    )

                    state_info["signal"] = (
                        state.terminated.signal
                    )

                if state.waiting:

                    state_info["reason"] = (
                        state.waiting.reason
                    )

                    state_info["message"] = (
                        state.waiting.message
                    )

                container_states.append(
                    state_info
                )

        return {

            "name":
                pod.metadata.name,

            "namespace":
                pod.metadata.namespace,

            "phase":
                pod.status.phase,

            "node":
                pod.spec.node_name,

            "restart_count":
                restart_count,

            "containers":
                container_states
        }

    # ============================================================
    # FIND POD WITH MOST RESTARTS
    # ============================================================

    def find_affected_pod(self):

        pods = self.get_pods()

        if not pods:

            return None

        pod_information = []

        for pod in pods:

            info = self.get_pod_info(
                pod
            )

            pod_information.append(
                info
            )

        # Highest restart count first.
        pod_information.sort(
            key=lambda item:
                item["restart_count"],
            reverse=True
        )

        return pod_information[0]

    # ============================================================
    # VERIFY POD CRASH
    # ============================================================

    def verify_pod_crash(
        self,
        minimum_restarts=3
    ):

        pods = self.get_pods()

        if not pods:

            return {

                "confirmed": False,

                "reason":
                    "No pods found",

                "pod": None
            }

        candidates = []

        for pod in pods:

            info = self.get_pod_info(
                pod
            )

            # ----------------------------------------------------
            # Restart based detection
            # ----------------------------------------------------

            if (
                info["restart_count"]
                >= minimum_restarts
            ):

                candidates.append(
                    info
                )

                continue

            # ----------------------------------------------------
            # Check terminated container state
            # ----------------------------------------------------

            for container in info["containers"]:

                reason = container.get(
                    "reason"
                )

                if reason in [
                    "OOMKilled",
                    "Error",
                    "CrashLoopBackOff"
                ]:

                    candidates.append(
                        info
                    )

                    break

        if not candidates:

            return {

                "confirmed": False,

                "reason":
                    "Kubernetes does not currently confirm a pod crash",

                "pod": None
            }

        # Select the pod with the highest restart count.
        candidates.sort(
            key=lambda item:
                item["restart_count"],
            reverse=True
        )

        affected_pod = candidates[0]

        return {

            "confirmed": True,

            "reason":
                "Kubernetes confirms abnormal pod state",

            "pod":
                affected_pod
        }

    # ============================================================
    # CLUSTER SUMMARY
    # ============================================================

    def cluster_summary(self):

        pods = self.get_pods()

        total = len(pods)

        running = 0
        failed = 0
        pending = 0
        restarts = 0

        for pod in pods:

            info = self.get_pod_info(
                pod
            )

            restarts += info[
                "restart_count"
            ]

            if info["phase"] == "Running":

                running += 1

            elif info["phase"] == "Failed":

                failed += 1

            elif info["phase"] == "Pending":

                pending += 1

        return {

            "namespace":
                self.namespace,

            "total_pods":
                total,

            "running":
                running,

            "failed":
                failed,

            "pending":
                pending,

            "total_restarts":
                restarts
        }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("KUBERNETES INCIDENT MONITOR")
    print("=" * 70)

    monitor = KubernetesMonitor(
        namespace="aiops"
    )

    print()
    print("CLUSTER SUMMARY")
    print("-" * 70)

    summary = monitor.cluster_summary()

    for key, value in summary.items():

        print(
            f"{key:20s}: {value}"
        )

    print()
    print("PODS")
    print("-" * 70)

    pods = monitor.get_pods()

    if not pods:

        print(
            "No pods found."
        )

    else:

        for pod in pods:

            info = monitor.get_pod_info(
                pod
            )

            print()
            print(
                f"Pod: {info['name']}"
            )

            print(
                f"Status: {info['phase']}"
            )

            print(
                f"Restarts: {info['restart_count']}"
            )

            print(
                f"Node: {info['node']}"
            )

    print()
    print("POD CRASH VERIFICATION")
    print("-" * 70)

    result = monitor.verify_pod_crash()

    print(
        result
    )

    print()
    print("=" * 70)


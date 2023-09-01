API_POD_NAME=$(kubectl get ep kernelci-api -o=jsonpath='{.subsets[*].addresses[*].ip}' | tr ' ' '\n' | xargs -I % kubectl get pods -o=name --field-selector=status.podIP=%)
kubectl exec -it $API_POD_NAME -- python3 -m api.admin --mongo mongodb://kernelci-api-db.default.svc.cluster.local:27017 --email bot@kernelci.org

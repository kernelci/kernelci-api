#!/bin/bash

# Clean up the existing /home/docker/kernelci-api directory in Minikube node
minikube ssh -- sudo rm -rf /home/docker/kernelci-api

# Delete Deployments
kubectl delete -f ../api-deployment.yaml --ignore-not-found
kubectl delete -f ../deployments/db-deployment.yaml --ignore-not-found
kubectl delete -f ../deployments/redis-deployment.yaml --ignore-not-found
kubectl delete -f ../deployments/ssh-deployment.yaml --ignore-not-found
kubectl delete -f ../deployments/storage-deployment.yaml --ignore-not-found

# Wait for pods associated with the deployments to be terminated
while kubectl get pods | grep -E "kernelci-api|kernelci-api-db|kernelci-api-redis|kernelci-api-ssh|kernelci-api-storage"; do
    echo "Waiting for pods to be terminated..."
    sleep 5
done

# Delete Services
kubectl delete -f ../services/api-service.yaml --ignore-not-found
kubectl delete -f ../services/db-service.yaml --ignore-not-found
kubectl delete -f ../services/redis-service.yaml --ignore-not-found
kubectl delete -f ../services/ssh-service.yaml --ignore-not-found
kubectl delete -f ../services/storage-service.yaml --ignore-not-found

# Delete PersistentVolumeClaims
kubectl delete -f ../pvc/db-pvc.yaml --ignore-not-found

# Delete Init Job and Pod
kubectl delete -f ../init/init-job.yaml --ignore-not-found
kubectl delete -f ../init/init-pod.yaml --ignore-not-found

# Delete Secret
kubectl delete secret kernelci-api-secret --ignore-not-found

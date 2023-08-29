#!/bin/bash

# Function to check if a resource exists
check_resource_exist() {
  local kind=$1
  local name=$2

  # Wait for the resource to be available
  while [[ -z "$(kubectl get $kind $name -o json)" ]]; do
    echo "Waiting for $kind $name to be available..."
    sleep 5
  done

  echo "$kind $name is available!"
}

# Function to check if a resource is bound (for PVCs)
check_pvc_bound() {
  local name=$1

  while true; do
    STATUS=$(kubectl get pvc $name -o 'jsonpath={.status.phase}')
    if [[ "$STATUS" == "Bound" ]]; then
      break
    fi
    # Pending is also means ready (it might be waiting first consumer)
    # Example: Normal  WaitForFirstConsumer  12s (x3 over 29s)  persistentvolume-controller  waiting for first consumer to be created before binding
    if [[ "$STATUS" == "Pending" ]]; then
      break
    fi
    echo "Waiting for PVC $name to be bound..., current status: $STATUS"
    sleep 5
  done

  echo "PVC $name is bound!"
}

# Function to check if a resource is ready (for Deployments)
check_deployment_ready() {
  local name=$1

  # Wait for the Deployment to have available replicas
  while [[ "$(kubectl get deployment $name -o 'jsonpath={.status.availableReplicas}')" != "$(kubectl get deployment $name -o 'jsonpath={.status.replicas}')" ]]; do
    echo "Waiting for Deployment $name to have available replicas..."
    sleep 5
  done

  echo "Deployment $name is ready!"
}

# Function to check if a resource is completed (for Jobs)
check_job_completed() {
  local name=$1

  # Wait for the Job to be completed
  while true; do
    STATUS=$(kubectl get job $name -o 'jsonpath={.status.conditions[].type}')
    if [[ "$STATUS" == "Complete" ]]; then
      break
    fi

    # If error occurs, exit (Failed/Error)
    if [[ "$STATUS" == "Failed" || "$STATUS" == "Error" ]]; then
      echo "Job $name failed! Status is $STATUS, exiting..."
      echo "You can review the logs of the Job $name using the following command:"
      echo "kubectl logs job/$name"
      exit 1
    fi
    echo "Waiting for Job $name to be completed..., current status: $STATUS"
    sleep 5
  done

  echo "Job $name is completed!"
}

# Function to apply a resource and check if it is ready or completed (for Jobs)
apply_and_check_resource() {
  local file=$1

  kubectl apply -f "$file"

  # Get the resource kind and name from the file
  kind=$(kubectl get -f "$file" -o 'jsonpath={.kind}')
  name=$(kubectl get -f "$file" -o 'jsonpath={.metadata.name}')

  case "$kind" in
    "Job")
      check_job_completed "$name"
      ;;
    "Deployment")
      check_deployment_ready "$name"
      ;;
    *)
      ;;
  esac
}

# Run the clean-all.sh script
source clean-all.sh
check_job_completed "delete-dir-job"

# Fork GitHub repository in Minikube node
kubectl apply -f ../init/init-job.yaml
check_job_completed "github-cloning-job"

# Create Kubernetes secret
kubectl create secret generic kernelci-api-secret --from-literal=secret-key=$(openssl rand -hex 32)
check_resource_exist "Secret" "kernelci-api-secret"

# Set up persistent volume claim
kubectl apply -f ../pvc/db-pvc.yaml
check_pvc_bound "mongo-data-pvc"

# Apply all the services
for file in ../services/*.yaml; do
  kubectl apply -f "$file"
done

# Apply all the deployments
for file in ../deployments/*.yaml; do
  apply_and_check_resource "$file"
done

# Apply the api-deployment.yaml
kubectl apply -f ../api-deployment.yaml
check_deployment_ready "kernelci-api"  # Assuming the deployment has the name "api-deployment" in api-deployment.yaml

echo "All components deployed successfully!"

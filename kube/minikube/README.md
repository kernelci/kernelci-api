Getting Started with KernelCI API in Minikube
=============================================

## Forking GitHub Repository in the Minikube node

### init/init-job.yaml

Simply run the following from the root of the kube/minikube folder and it will run a Kubernetes job that will fork the kernelci-api official github repository and will use hostPath based volume persisting mechanism to persist the job-based pod data on the Minikube node.
``` 
kubectl apply -f init/init-job.yaml
```
Thus the data will remain on the Minikube node in /home/docker/kernelci-api folder even after the pod gets deleted. You can verify this by simply SSHing into Minikube node and finding the mentioned directory.

To SSH into Minikube node simply run
```
minikube ssh
```

### init/init-pod.yaml

Simply run the following command to use init-pod.yaml instead of init-job.yaml from the root of the kube/minikube folder.
```
kubectl apply -f init/init-pod.yaml
```
In the case of init-pod.yaml, everything would essentially be the same except for the case that pods are not good at the tasks that ends at certain point and for that specific reason we prefer init-job.yaml. Here to forcefully keep the pod persisting and stopping it from failing we used the command ```tail -f /dev/null```. Thus it would be more resource intensive than init-job.yaml. Except for this everything would be the same

### re-running or reinitializing the init-job.yaml or init-pod.yaml 

To re-run or reinitialize the init-pod.yaml or init-job.yaml, first of all you need to clean the existing ```/home/docker/kernelci-api``` directory in the minikube node, otherwise the associated pods would throw an error as the directory would not be empty at the time of re-running or reinitialization. So in order to avoid these errors and prevent pods associated with init-jobs.yaml or init-pods.yaml from failing, simply run the following command before applying or reconfiguring any of these yaml files if you haven't done complete clean-up and are not starting afresh.
```
minikube ssh -- sudo rm -rf /home/docker/kernelci-api
```

### manually forking github repo in minikube node without using pods or jobs

To achieve this we need to ssh into minikube using ```minikube ssh``` and then we need to manually download git using ```sudo apt update``` and ```sudo apt git```. After that we can manually clone the official kernelci-api github repository. This is not a recommended method, as manually doing a task that can be automated is against one of the Larry Wall's three virtues of programmers i.e. laziness. Also, things that requires frequent manual tunneling can be a security threat. To update your cloned git repo, you can simply use ```git pull``` command to merge the latest changes.

## Creating a Kubernetes secret

To create a Kubernetes secret with name my-secret and store its value as key-value pair with the key named secret-key run the following command.
```
kubectl create secret generic kernelci-api-secret --from-literal=secret-key=$(openssl rand -hex 32)
```

To check your secret in base64 encoded form use

```
kubectl get secret kernelci-api-secret -o jsonpath='{.data.secret-key}'
```

To decode your secret key and get the original data use
```
kubectl get secret kernelci-api-secret -o jsonpath='{.data.secret-key}' | base64 -d
```

To encode your already encoded base64 key using base64 encryption i.e. to double encode your key in base64 format use
```
kubectl get secret kernelci-api-secret -o jsonpath='{.data.secret-key}' | base64 -
```

## Setting up persistent volume claim

Simply run the following command from the roots of the kube/minikube folder to set up the pvc.
```
kubectl apply -f pvc/db-pvc.yaml
```

To monitor your pvc use 
```
kubectl get pvc
```

## Setting up the services

Simply run the following command from the root of kube/minikube/services folder to set up all the services.
```
kubectl apply -f .
```

To check your services, run
```
kubectl get svc
```

To port-forward api-service, run
```
kubectl port-forward svc/kernelci-api 8001:8001
```

To port-forward ssh-service, run
```
kubectl port-forward svc/kernelci-api-ssh 8022:8022
```

To port-forward storage-service, run
```
kubectl port-forward svc/kernelci-api-storage 8002:8002
```

To port-forward to redis-service, run
```
kubectl port-forward svc/kernelci-api-redis 6379:6379
```

To port-forward to db-service, run
```
kubectl port-forward svc/kernelci-api-db 27017:27017
```

To ensure api connections are handled properly, assign the value ```kernelci-api-redis.default.svc.cluster.local``` to ```redis_host``` variable present in the file api/pubsub.py.

## Getting deployments up and running

It is important to run all the above given steps and wait for them to be executed successfully before getting your deployments up and running.

Simply run the following command from the roots of kube/minikube/deployments folder to get all the deployments up and running.
```
kubectl apply -f .
```

To monitor whether the deployments have setup the pods successfully or not you can use 
```
kubectl get pods
```

To log any accidental error persisting in your pods use
```
kubectl logs <pod-name>
```

## Getting api-deployment up and running

As kernelci-api relies on other deployments, it is important to get them up and running first and get kernelci-api up and running afterwards. Thus after completing all the above steps, you can apply ```api-deployment.yaml``` file that is present in the root of kube/minikube folder. To apply the YAML file in the minikube cluster, simply run
```
kubectl apply -f api-deployment.yaml
```

## Cleaning up everything afterwards

To clean up everything simply use the ```clean-all.sh``` script provided in the root of the kube/minikube/hack folder by running
```
./clean-all.sh
```

## Deploying all the resources at once

To apply all the resources at once, you can use the ```apply-all.sh``` script provided in the root of the kube/minikube/hack folder by running
```
./apply-all.sh
```
This script would also do the clean up and will deploy everything afresh. But it can be time-consuming to deploy everything afresh, so if you want to reconfigure some deployment maybe because the image is updated, just reapply that deployment or do the rolling update instead of running this script.

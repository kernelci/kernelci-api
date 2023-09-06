<!--
SPDX-License-Identifier: LGPL-2.1-or-later

Copyright (C) 2023 Collabora Limited
Author: Guillaume Tucker <guillaume.tucker@collabora.com>
-->

KernelCI API Deployment in Azure Kubernetes Services (AKS)
==========================================================

This guide goes through all the steps required to deploy the KernelCI API
service in
[AKS](https://azure.microsoft.com/en-us/products/kubernetes-service).  It
relies on an external Atlas account for MongoDB and does not include any
storage solution.

## Azure account

The first prerequisite is to have a [Microsoft Azure](https://azure.com)
account.  If you already have one, you can skip this step and carry on with
setting up an AKS cluster.  Otherwise, please create one now typically with an
`@outlook.com` email address.  You can create a new address on
[outlook.com](https://outlook.com) for this purpose if needed.

## AKS cluster

Please create an AKS cluster via the [Azure
portal](https://portal.azure.com/#create/Microsoft.AKS).  The standard settings
are fine for this use-case although you might need to adjust a few things to
match the scale of your particular deployment.

## Atlas MongoDB account

This AKS reference deployment relies on an Atlas account for MongoDB in order
to keep everything in the Cloud and application setup to the bare minimal.  As
such, please [create an Atlas
account](https://www.mongodb.com/cloud/atlas/register) if you don't already
have one and set up a database.  The MongoDB service string will be needed
later on to let the API service connect to it.

The recommended way to set up a subscription is to create a "MongoDB Atlas
(pay-as-you-go)" resource via the Azure Marketplace.

To set up a database:

* create a cluster with the appropriate tier for the deployment
* add a database in the project via the web UI with "Create Database"
* go to "Database Access" to create a user and password with the
  `readWriteAnyDatabase` built-in role

You should now be able to connect to the database with a connection string of
the form `mongodb+srv://user:password@something.mongodb.net`.  To verify it's
working:

```
$ mongo mongodb+srv://user:password@something.mongodb.net
[...]
MongoDB Enterprise atlas-ucvcf2-shard-0:PRIMARY> show databases
admin      0.000GB
kernelci   0.004GB
local     22.083GB
```

The string used with the `mongo` shell here is the same one that needs to be
stored as a Kubernetes secret for the API service as described in a later
section of this documentation page.

## Command line tools

Configuring this AKS deployment relies on `az`, `kubectl` and `helm` to be
installed.  As a convenience, the `kernelci/k8s` Docker image can be used with
these tools already installed.  We'll be using it in this documentation page
going forward.  Here's a sample command to start a container with the Docker
image:

```
$ cd kube/aks
$ mkdir -p home
$ cp *.yaml home
$ docker run -it \
    -u1000 -v$PWD/home:/tmp/home -w/tmp/home -eHOME=/tmp/home \
    kernelci/k8s /bin/bash
I have no name!@e628a6d08636:~$ ls -la
total 20
drwxr-xr-x 2 1000 1000 4096 Aug 29 11:36 .
drwxrwxrwt 1 root root 4096 Aug 29 11:36 ..
-rw-r--r-- 1 1000 1000 1089 Aug 29 11:36 api.yaml
-rw-r--r-- 1 1000 1000  878 Aug 29 11:36 ingress.yaml
-rw-r--r-- 1 1000 1000  479 Aug 29 11:36 redis.yaml
I have no name!@ace0f3581e23:~$
```

The commands shown in this tutorial will be omitting the prompt up to the `$`
sign for the sake of readability.  The image only has a `root` user but it's
better when accessing volumes mounted from the local file system to run the
containers with a regular user so in this case it's using anonymous user ID
`1000`.

## Get `kubectl` credentials

The container started in the previous section has a `home` directory mounted
from the host.  This allows Azure credentials to be stored there persistently,
so if the container is restarted they'll still be available.

To create the initial credentials, you can run the `az login` command from
within the container and then login by pasting the temporary code into the [web
page](https://microsoft.com/devicelogin):

```
$ az login --use-device-code
To sign in, use a web browser to open the page https://microsoft.com/devicelogin and enter the code XXXYYYZZZ to authenticate.
```

After following the instructions on the web page, you should be able to access
your AKS cluster.  Still from within the container, run the following commands
with your own cluster name instead of `kernelci-api-1`:

```
$ az aks list -o table
Name                    Location        ResourceGroup              KubernetesVersion    [...]
----------------------  --------------  -------------------------  -------------------  [...]
kernelci-api-1          eastus          kernelci-api               1.26.6               [...]
$ az aks get-credentials -n kernelci-api-1 -g kernelci-api
Merged "kernelci-api-1" as current context in /tmp/home/.kube/config
$ kubectl config use-context kernelci-api-1
Switched to context "kernelci-api-1".
$ kubectl get nodes
NAME                                STATUS   ROLES   AGE    VERSION
aks-agentpool-23485665-vmss000000   Ready    agent   4h3m   v1.26.6
aks-userpool-23485665-vmss000000    Ready    agent   4h3m   v1.26.6
```

## Install extra packages in the AKS cluster

A couple of additional packages are needed in order to have a full production
deployment with SSL encryption.  This is done using `ingress-nginx` to act as a
form of proxy for incoming requests and `cert-manager` to manage the SSL
certificates with [Let's Encrypt](https://letsencrypt.org/).

Still in the same container, let's first define some environment variables to
make the subsequent commands easier to run:

```
CONTROLLER_IMAGE=ingress-nginx/controller
CONTROLLER_TAG=v1.2.1
DEFAULTBACKEND_IMAGE=defaultbackend-amd64
DEFAULTBACKEND_TAG=1.5
PATCH_IMAGE=ingress-nginx/kube-webhook-certgen
PATCH_TAG=v1.1.1
```

### Set up `ingress-nginx`

The first Kubernetes package to install in the cluster is `ingress-nginx` which
provides a way to handle incoming connections as a Kubernetes ingress.  Here
are some samples commands to do this:

```
$ helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
$ helm repo update
Hang tight while we grab the latest from your chart repositories...
...Successfully got an update from the "ingress-nginx" chart repository
Update Complete. ⎈Happy Helming!⎈
$ helm install ingress-nginx ingress-nginx/ingress-nginx \
    --version=4.1.3 \
    --namespace=kernelci-api \
    --create-namespace \
    --set controller.replicaCount=2 \
    --set controller.nodeSelector."kubernetes\.io/os"=linux \
    --set controller.image.image=$CONTROLLER_IMAGE \
    --set controller.image.tag=$CONTROLLER_TAG \
    --set controller.image.digest="" \
    --set controller.admissionWebhooks.patch.nodeSelector."kubernetes\.io/os"=linux \
    --set controller.service.loadBalancerIP=10.224.0.42 \
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-internal"=true \
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
    --set controller.admissionWebhooks.patch.image.image=$PATCH_IMAGE \
    --set controller.admissionWebhooks.patch.image.tag=$PATCH_TAG \
    --set controller.admissionWebhooks.patch.image.digest="" \
    --set defaultBackend.nodeSelector."kubernetes\.io/os"=linux \
    --set defaultBackend.image.image=$DEFAULTBACKEND_IMAGE \
    --set defaultBackend.image.tag=$DEFAULTBACKEND_TAG \
    --set defaultBackend.image.digest=""
```

You should get a summary of the operation with some confirmation like this as
part of it:

```
The ingress-nginx controller has been installed.
It may take a few minutes for the LoadBalancer IP to be available.
You can watch the status by running 'kubectl --namespace default get services -o wide -w ingress-nginx-controller'
```

### Add a DNS label

Then as SSL certificates are bound to particular domain names, you either have
to provide your own and update some independent DNS record with the public IP
address of the ingress or rely on the default Azure domain names.  In this
example, we'll go down the standard Azure route to keep things self-contained.
This can be done by creating a label for the ingress:

```
$ helm upgrade ingress-nginx ingress-nginx/ingress-nginx \
    --namespace kernelci-api \
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=kernelci-api \
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz
```

The cluster used in this example is located in the East US region, so the full
domain name (FQDN) is `kernelci-api.eastus.cloudapp.azure.com`.  To confirm:

```
$ nslookup kernelci-api.eastus.cloudapp.azure.com
Server:		192.168.1.254
Address:	192.168.1.254#53

Non-authoritative answer:
Name:	kernelci-api.eastus.cloudapp.azure.com
Address: 4.157.88.45
```

> **Note:** The IP address is assigned dynamically every time the ingress is
> recreated so it's normal to get a different one.

### Set up `cert-manager`

Once `ingress-nginx` has been set up, we can install `cert-manager` which will
be providing a Let's Encrypt SSL certificate to handle HTTPS incoming
connections.  To do this:

```
$ helm repo add jetstack https://charts.jetstack.io
$ helm repo update
$ CERT_MANAGER_TAG=v1.8.0
$ helm install cert-manager jetstack/cert-manager \
    --version $CERT_MANAGER_TAG \
    --namespace kernelci-api \
    --set controller.nodeSelector."kubernetes\.io/os"=linux \
    --set installCRDs=true \
    --set image.tag=$CERT_MANAGER_TAG \
    --set webhook.image.tag=$CERT_MANAGER_TAG \
    --set cainjector.image.tag=$CERT_MANAGER_TAG
```

Then you should see this as part of the output:

```
cert-manager v1.8.0 has been deployed successfully!
```

## Set up the ingress

Once the Kubernetes packages have been installed, the actual ingress
definition can be applied.  Still within the same container, run this command:

```
$ kubectl apply -f ingress.yaml
```

Then to check it's all set up correctly:

```
$ kubectl --namespace=kernelci-api get certificates
NAME         READY   SECRET       AGE
tls-secret   True    tls-secret   79s
$ kubectl --namespace=kernelci-api get ingresses
NAME   CLASS   HOSTS                                    ADDRESS       PORTS     AGE
api    nginx   kernelci-api.eastus.cloudapp.azure.com   4.157.88.45   80, 443   33s
```

> **Note:** It can take a few minutes for the `ADDRESS` to appear and for the
> certificate to be ready.  Initially the `READY` status will be `False` but
> this is expected.

## Deploy the redis service

There are two services to deploy in AKS: `redis` and `api`.  First, let's look
at `redis` since it's simpler and is a dependency for the `api` service.  To
deploy it:

```
$ kubectl apply -f redis.yaml
```

Then to check it's working:

```
$ kubectl --namespace=kernelci-api get deployments
NAME                       READY   UP-TO-DATE   AVAILABLE   AGE
cert-manager               1/1     1            1           7h53m
cert-manager-cainjector    1/1     1            1           7h53m
cert-manager-webhook       1/1     1            1           7h53m
ingress-nginx-controller   1/1     1            1           8h
redis                      1/1     1            1           8s
$ kubectl --namespace=kernelci-api get pods
NAME                                        READY   STATUS    RESTARTS   AGE
cert-manager-cainjector-f856fb49-hj2rw      1/1     Running   0          7h53m
cert-manager-f89f7fd88-ndsvn                1/1     Running   0          7h53m
cert-manager-webhook-665cd46d4b-ddq5r       1/1     Running   0          7h53m
ingress-nginx-controller-5ff6bb675f-c2lsx   1/1     Running   0          7h39m
redis-799cd8b7bd-ws2fs                      1/1     Running   0          22s
$ kubectl logs redis-799cd8b7bd-ws2fs --namespace=kernelci-api
1:C 23 Aug 2023 14:19:20.774 # oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
1:C 23 Aug 2023 14:19:20.774 # Redis version=6.2.13, bits=64, commit=00000000, modified=0, pid=1, just started
1:C 23 Aug 2023 14:19:20.774 # Warning: no config file specified, using the default config. In order to specify a config file use redis-server /path/to/redis.conf
1:M 23 Aug 2023 14:19:20.774 * monotonic clock: POSIX clock_gettime
1:M 23 Aug 2023 14:19:20.775 * Running mode=standalone, port=6379.
1:M 23 Aug 2023 14:19:20.775 # Server initialized
1:M 23 Aug 2023 14:19:20.775 * Ready to accept connections
```

## Deploy the main API service

### Create secret key

The API service requires a unique "secret key" used when generating JWT tokens.
To create your own key using the `openssl` tool and then add it as a Kubernetes
secret:

```
$ openssl rand -hex 32
f9256e80e30c16187d3e42fa1ea70c41f6945743846cf1fb2911e0665f16dd99
$ kubectl create secret generic \
    kernelci-api-secret-key \
    --namespace=kernelci-api \
    --from-literal=secret-key=f9256e80e30c16187d3e42fa1ea70c41f6945743846cf1fb2911e0665f16dd99
secret/kernelci-api-secret-key created
```

This will then be shared with the application via the `SECRET_KEY` environment
variable as defined in `api.yaml`.

### Add MongoDB service string

While deployments with `docker-compose` typically rely on a local container
running MongoDB directly, when deploying in the Cloud you might want to use a
separate database.  The kernelci.org Azure deployment relies on an Atlas
account for MongoDB and as such requires a service string which includes the
user name and password.  This is why the MongoDB string is also defined as a
secret, although it might in some cases be an anonymous connection with no real
credentials.

To define the Kubernetes secret for MongoDB:

```
$ kubectl create secret generic \
    kernelci-api-mongo-service \
    --namespace=kernelci-api \
    --from-literal=mongo-service="mongodb+srv://user:password@something.mongodb.net"
secret/kernelci-api-mongo-service created
```

This will then be shared with the application via the `MONGO_SERVICE`
environment variable as defined in `api.yaml`.

### Deployment

Let's first double-check that the secrets have been created as expected:

```
$ kubectl get secrets --namespace=kernelci-api | grep kernelci-api
kernelci-api-mongo-service            Opaque               1      22h
kernelci-api-secret-key               Opaque               1      22h
```

The main API service is based on the `kernelci/api` Docker image which is built
from the `Dockerfile.production` file included in this repository and hosted on
the Docker hub.  As with any YAML file used by `kubectl`, it's possible to
override the Docker image name with an overlay on top of `api.yaml` if you want
to use your own instead.

To deploy the API service:

```
$ kubectl apply -f api.yaml
```

Then if all went well, you should now be able query the API:

```
$ curl https://kernelci-api.eastus.cloudapp.azure.com/latest/
{"message":"KernelCI API"}
```

The interactive API documentation should also be available on
[https://kernelci-api.eastus.cloudapp.azure.com/latest/docs](https://kernelci-api.eastus.cloudapp.azure.com/latest/docs)

## Enjoy!

Now you have a publicly available API instance suitable for production.  To
make best use of it, you can try the `kci` command line tools to do things by
hand and run the `kernelci-pipeline` services to automatically run jobs, send
email reports etc.  See the main documentation for pointers with more details.

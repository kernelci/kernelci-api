<img src="https://kernelci.org/image/kernelci-horizontal-color.png"
     alt="KernelCI project logo"
     width="40%" />

KernelCI API
============

This repository is a work-in-progress implementation of a new API and database
interface for KernelCI, to replace
[kernelci-backend](https://github.com/kernelci/kernelci-backend.git).  It's
mainly based on [FastAPI](https://fastapi.tiangolo.com/), [Mongo
DB](https://www.mongodb.com/) and [Redis](https://redis.io/).

Please refer to the [architecture](https://kernelci.org/docs/api/overview/#api-architecture) for more details.


## Getting started with docker-compose

Please refer to [start Docker containers](https://kernelci.org/docs/api/getting-started/#start-docker-compose) of all the services. 

Note that the FastAPI server is running on port 8000 inside the container, but
it's exposed to the host via port 8001 to avoid conflicts with other services.
This can be adjusted for each setup in
[`docker-compose.yaml`](docker-compose.yaml).


## Authentication

Generate a new key for [Authentication](https://kernelci.org/docs/api/getting-started/#create-the-environment-file
).
After that, please refer to [create and add a user](https://kernelci.org/docs/api/getting-started/#create-a-user-account) in Mongo DB.
The user can also generate an [API token](https://kernelci.org/docs/api/getting-started/#create-an-api-token) to use API endpoints.

Ultimately, there will be a web frontend to provide a login form.  We don't
have that yet as this new KernelCI API implementation is still in its early
stages.


## API Documentation

The FastAPI server will automatically generate documentation for the API itself
and serve it directly:: http://localhost:8001/docs

To use the generated documentation, first open it on
http://localhost:8001/docs.  Then click on "Authorize", enter the user name and
password and click on the "Authorize" button.

This is based on OpenAPI, and you can also download the `openapi.json` file to
use it with other tools: http://localhost:8001/openapi.json


## API Testing

Please follow the below instructions to test API endpoints.

Install Python requirements with additional packages for testing:
```
pip install -r docker/api/requirements-dev.txt
```

We have created .env file using env.sample in kernelci-api directory from 'Generate SECRET KEY and add it in environment file' section. Export .env file with SECRET_KEY environment variable in it:
```
export $(cat .env)
```

Run the below command from kernelci-api/api directory:
```
pytest
```
This will start running test cases from kernelci-api/api/test_api.py and display results.

## Generate SSH key and copy to SSH directory

Use the below command to generate SSH key. It will store private key to `/home/username/.ssh/id_rsa_kernelci-api` file and public key to `/home/username/.ssh/id_rsa_kernelci-api.pub` file.

```
$ ssh-keygen -f ~/.ssh/id_rsa_kernelci-api
```

Use the below command to copy the public key to ssh/user-data directory.
```
$ cat ~/.ssh/id_rsa_kernelci-api.pub >> docker/ssh/user-data/authorized_keys
```

SSH docker container will have /home/kernelci/.ssh/authorized_keys file.
Now, the user will be able to SSH to container using private key.
```
$ ssh -i ~/.ssh/id_rsa_kernelci-api -p 8022 kernelci@localhost
```

### SSH login on WSL using authorization keys

In case of running setup on WSL (Windows Subsystem for Linux),
we need to have certain file permissions to be able to login to kernelci-ssh container using SSH authorization keys.

Use the below commands to check permissions for `user-data` directory and `authorized_keys` file in `kernelci-api` directory.
```
$ ls -lrt kernelci-api/docker/ssh/
total 5
-rwxrwxrwx 1 user user  652 Dec 29 11:31 Dockerfile
-rwxrwxrwx 1 user user 3289 Feb  9 16:25 sshd_config
drwxrwxrwx 1 user user  512 Feb 11 14:32 user-data
```

```
$ ls -lrt kernelci-api/docker/ssh/user-data/
total 1
-rwxrwxrwx 1 user user   0 Feb 10 15:59 authorized_keys.sample
-rwxrwxrwx 1 user user 574 Feb 11 14:35 authorized_keys
```

We need `user-data` directory permission to be 700(drwxr-xr-x) and `authorized_keys` file permission to be 644(-rw-r--r--). The reason being is, SSH key authorization will not work if the public key file has all the permissions enabled i.e. set to 777(rwxrwxrwx).

If we don't have these permissions already set then we need to change them using the below commands.

```
$ chmod 700 kernelci-api/docker/ssh/user-data
$ chmod 644 kernelci-api/docker/ssh/user-data/authorized_keys
```

If running `chmod` command doesn't affect the permissions, we need to add the below line to /etc/wsl.conf file and restart the `wsl` service to change them successfully:
```
options = "metadata"
```

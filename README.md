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


## Getting started with docker-compose

The FastAPI server and Mongo DB can all be started at the same time using
`docker-compose`.  Then FastAPI can access the Mongo DB container directly via
the `db` hostname.

```
$ docker-compose up --build
[...]
kernelci-api | INFO:     Application startup complete.
```

Then to check it's working:

```
$ curl http://localhost:8001/
{"message":"KernelCI API"}
```

Note that the FastAPI server is running on port 8000 inside the container, but
it's exposed to the host via port 8001 to avoid conflicts with other services.
This can be adjusted for each setup in
[`docker-compose.yaml`](docker-compose.yaml).

The container log should show:
```
kernelci-api | INFO:     172.20.0.1:49228 - "GET / HTTP/1.1" 200 OK
```

## API Documentation

The FastAPI server will automatically generate documentation for the API itself
and serve it directly:: http://localhost:8001/docs

This is based on OpenAPI, and you can also download the `openapi.json` file to
use it with other tools: http://localhost:8001/openapi.json


## Authentication

### Generate SECRET KEY and add it in environment file

Generate a new key for Authentication using following command:
```
$ openssl rand -hex 32
```

Store the generated key to `.env` file and give its path to
`docker-compose.yaml` file.  We have loaded secret key using FastAPI settings
feature in `api.auth`. Please find the env.sample file in the base directory to
store secret key and copy the file to your `.env` file.

Some parts of the API require the user to be authenticated, for example to
submit data to store in the database or access restricted data.  The first
thing to do is create a user account.  For example, with a user called `bob`
and a password `hello`:

### Set ALGORITHM and ACCESS_TOKEN_EXPIRE_MINUTES in environment file

We need to specify algorithm for JWT token encoding and decoding. ALGORITHM variable needs to be passed in the parameter for that.
ALGORITHM is set default to HS256.
We have used ACCESS_TOKEN_EXPIRE_MINUTES variable to set expiry time on generated jwt access token.
ACCESS_TOKEN_EXPIRE_MINUTES is set default to None.
If user wants to change any of the above variable, It should be added to .env file. Please refer env.sample to add variable to .env file.

### Get a password hash

The passwords are not stored in clear in the database, instead a hash of them
is stored.  The `/hash` API endpoint can be used to produce a hash using the
same algorithm as used by the authentication:

```
$ curl http://localhost:8001/hash/hello
"$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.xCZGmM8jWXUXJZ4K"
```

### Add the user in Mongo DB

The command below will run in the Mongo DB container via `docker-compose`.
Make sure to escape special characters in the password hash generated in the
previous step.  In particular, `$` characters need to be escaped with `\$`:

```
$ docker-compose exec db /bin/mongo kernelci --eval \
  "db.user.insert({username: 'bob', hashed_password: '\$2b\$12\$VtfVij6zz20F/Qr0Ri18O.11.0LJMMXyJxAJAHQbKU0jC96eo2fr.', active: true})"
MongoDB shell version v5.0.3
connecting to: mongodb://127.0.0.1:27017/kernelci?compressors=disabled&gssapiServiceName=mongodb
Implicit session: session { "id" : UUID("84a62d1b-4b06-4631-8227-413964826100") }
MongoDB server version: 5.0.3
WriteResult({ "nInserted" : 1 })
```

Ultimately, there will be a web frontend to provide a login form.  We don't
have that yet as this new KernelCI API implementation is still in its early
stages.  However, it's always possible to authenticate using either `curl` or
the documentation interface mentioned in the previous section.  With `curl`:

```
$ curl -X 'POST' \
  'http://localhost:8001/token' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=&username=bob&password=hello'
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJib2IifQ.KHkILtsJaCmueOfFCj79HGr6kHamuZFdB1Yz_5GqcC4","token_type":"bearer"}
```

The token can then be used with API entry points that require authentication.
For example:

```
$ curl -X 'GET' \
  'http://localhost:8001/me' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJib2IifQ.KHkILtsJaCmueOfFCj79HGr6kHamuZFdB1Yz_5GqcC4'
{"_id":"615f30020eb7c3c6616e5ac3","username":"bob","hashed_password":"$2b$12$VtfVij6zz20F/Qr0Ri18O.11.0LJMMXyJxAJAHQbKU0jC96eo2fr.","active":true}
```

To use the generated documentation, first open it on
http://localhost:8001/docs.  Then click on "Authorize", enter the user name and
password and click on the "Authorize" button.  Then the entry points that
require authentication such as `/me` will work like with the example above when
running `curl` by hand.


## Nodes

As a proof-of-concept, an object model called `Node` is defined in this API.
It's possible to create new objects and retrieve them via the API.

### Creating a Node

This requires an authentication token, as explained in the previous section:

```
$ curl -X 'POST' \
  'http://localhost:8001/node' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJib2IifQ.ci1smeJeuX779PptTkuaG1SEdkp5M1S1AgYvX8VdB20' \
  -H 'Content-Type: application/json' \
  -d '{
  "name":"checkout",
  "revision":{"tree":"mainline",
  "url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
  "branch":"master",
  "commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
  "describe":"v5.16-rc4-31-g2a987e65025e"}
}'
{"_id":"61bda8f2eb1a63d2b7152418","kind":"node","name":"checkout","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":null,"status":"pending", "created":"2022-02-02T11:23:03.157648"}
```

### Getting Nodes back

Reading Node doesn't require authentication, so plain URLs can be used.

To get node by ID, use `/node` endpoint with node ID as a path parameter:

```
$ curl http://localhost:8001/node/61bda8f2eb1a63d2b7152418
{"_id":"61bda8f2eb1a63d2b7152418","kind":"node","name":"checkout","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":null,"status":"pending", "created":"2022-02-02T11:23:03.157648"}
```

To get all the nodes as a list, use the `/nodes` API endpoint:

```
$ curl http://localhost:8001/nodes
[{"_id":"61b052199bca2a448fe49673","kind":"node","name":"checkout","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":null,"status":"pass", "created":"2022-02-01T11:23:03.157648"},{"_id":"61b052199bca2a448fe49674","kind":"node","name":"check-describe","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":"61b052199bca2a448fe49673","status":"pending", "created":"2022-01-02T10:23:03.157648"}]
```

To get nodes by providing attributes, use `/nodes` endpoint with query parameters. All the attributes except node ID can be passed to this endpoint.
In case of ID, please use `/node` endpoint with node ID as described above.

```
$ curl 'http://localhost:8001/nodes?name=checkout&revision.tree=mainline'
[{"_id":"61b052199bca2a448fe49673","kind":"node","name":"checkout","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":null,"status":"pass", "created":"2022-02-01T11:23:03.157648"}]
```

### Updating a Node

To update a node, use PUT request to `node/{node_id}` endpoint.

```
$ curl -X 'PUT' \
  'http://localhost:8001/node/61bda8f2eb1a63d2b7152418' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJib2IifQ.ci1smeJeuX779PptTkuaG1SEdkp5M1S1AgYvX8VdB20' \
  -H 'Content-Type: application/json' \
  -d '{
  "name":"checkout-test",
  "revision":{"tree":"mainline",
  "url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
  "branch":"master",
  "commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
  "describe":"v5.16-rc4-31-g2a987e65025e"},
  "created":"2022-02-02T11:23:03.157648"
}'
{"_id":"61bda8f2eb1a63d2b7152418","kind":"node","name":"checkout-test","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":null,"status":"pending", "created":"2022-02-02T11:23:03.157648"}
```

## Pub/Sub and CloudEvent

The API provides a publisher / subscriber interface so clients can listen to
events and publish them too.  All the events are formatted using
[CloudEvents](https://cloudevents.io).

The [`client.py`](api/client.py) script provides a reference implentation for
publishing and listening to events.

For example, in a first terminal:

```
$ docker-compose exec api /bin/sh -c '\
TOKEN=<insert token here> \
/usr/bin/env python3 /home/kernelci/api/client.py \
listen abc'
Listening for events on channel abc.
Press Ctrl-C to stop.
```

Then in a second terminal:

```
$ docker-compose exec api /bin/sh -c '\
TOKEN=<insert token here> \
/usr/bin/env python3 /home/kernelci/api/client.py \
publish abc "Hello KernelCI"'
```

You should see the message appear in the first terminal (and stopping after
pressing Ctrl-C):

```
Message: Hello KernelCI
^CStopping.
```

Meanwhile, something like this should be seen in the API logs:

```
$ docker-compose logs api | tail -4
kernelci-api | INFO:     127.0.0.1:35752 - "POST /subscribe/abc HTTP/1.1" 200 OK
kernelci-api | INFO:     127.0.0.1:35810 - "POST /publish/abc HTTP/1.1" 200 OK
kernelci-api | INFO:     127.0.0.1:35754 - "GET /listen/abc HTTP/1.1" 200 OK
kernelci-api | INFO:     127.0.0.1:36744 - "POST /unsubscribe/abc HTTP/1.1" 200 OK
```

> **Note** The client doesn't necessarily need to be run within the `api`
Docker container, but it's a convenient way of trying things out as it already
has all the Python dependencies installed (essentially, `cloudevents`).

## API Testing

Please follow below instructions to test API endpoints.

Install Python requirements with additional packages for testing:
```
pip install -r docker/api/requirements-dev.txt
```

We have created .env file using env.sample in kernelci-api directory from 'Generate SECRET KEY and add it in environment file' section. Export .env file with SECRET_KEY environment variable in it:
```
export $(cat .env)
```

Run below command from kernelci-api/api directory:
```
pytest
```
This will start running test cases from kernelci-api/api/test_api.py and display results.

## Generate SSH key and copy to SSH directory

Use below command to generate SSH key. It will store private key to `/home/username/.ssh/id_rsa_kernelci-api` file and public key to `/home/username/.ssh/id_rsa_kernelci-api.pub` file.

```
$ ssh-keygen -f ~/.ssh/id_rsa_kernelci-api
```

Use below command to copy the public key to ssh/user-data directory.
```
$ cat ~/.ssh/id_rsa_kernelci-api.pub >> docker/ssh/user-data/authorized_keys
```

SSH docker container will have /home/kernelci/.ssh/authorized_keys file.
Now, the user will able to SSH to container using private key.
```
$ ssh -i ~/.ssh/id_rsa_kernelci-api -p 8022 kernelci@localhost
```

### SSH login on WSL using authorization keys

In case of running setup on WSL (Windows Subsystem for Linux),
we need to have certain file permissions to be able to login to kernelci-ssh container using SSH authorization keys.

Use below commands to check permissions for `user-data` directory and `authorized_keys` file in `kernelci-api` directory.
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

If we don't have these permission already set then we need to change them using below commands.

```
$ chmod 700 kernelci-api/docker/ssh/user-data
$ chmod 644 kernelci-api/docker/ssh/user-data/authorized_keys
```

If running `chmod` command doesn't affect the permissions, we need to add below line to /etc/wsl.conf file and restart the `wsl` service to change them successfully:
```
options = "metadata"
```

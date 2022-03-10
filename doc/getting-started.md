---
title: "Getting Started"
date: 2022-03-10
draft: true
description: "Setting up a local instance"
weight: 1
---

A [docker-compose](https://docs.docker.com/compose/) environment is provided
for both the new API and the pipeline.  On Debian systems, the main
prerequisite is to install it:

```
sudo apt install docker-compose
```

All the dependencies for running the API services as well as the pipeline
clients are then handled using Docker images.

## Setting up an API instance

The first step is to bring up the `docker-compose` environment file.  It
contains some settings specific to the local instance.

### Authenticaion secret key

The API authentication requires a secret key used with encryption algorithms.
To generate one for your local instance:

```
$ echo SECRET_KEY=$(openssl rand -hex 32) >> .env
```

### Start `docker-compose`

To build the Docker images and start `docker-compose`:

```
$ docker-compose up --build
[...]
kernelci-api | INFO:     Application startup complete.
```

It can take a few minutes to build the images from scratch the first time.
Then the services should be up and running.  To confirm the API is available:

```
$ curl http://localhost:8001/
{"message":"KernelCI API"}
```

> **Port numbers** for the services exposed by `docker-compose` can be
> configured using environment variables in the `.env` file: `API_HOST_PORT`,
> `STORAGE_HOST_PORT`, `SSH_HOST_PORT`.  See
> [`docker-compose.yaml`](https://github.com/kernelci/kernelci-api/blob/main/docker-compose.yaml).

Following the `curl` command from the example above, the container log should
show:
```
kernelci-api | INFO:     172.20.0.1:49228 - "GET / HTTP/1.1" 200 OK
```

### Create a user account

Some parts of the API don't require any authentication, like in the example
above with the root `/` endpoint and most `GET` requests to retrieve data.
However, sending data with `POST` and `PUT` requests will require a user token.
This will be required to run a full pipeline or to subscribe to the pub/sub
interface.  At the moment, there is no web UI for creating new user accounts or
obtaining API tokens so it needs to be done manually.

First, get an encrypted hash for the password you want to use using the `/hash`
API endpoint.  For example, if the password is `hello`:

```
$ curl http://localhost:8001/hash/hello
"$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.xCZGmM8jWXUXJZ4K"
```

Then create a new user entry in the database.  You will need to provide the
password hash from the previous command with special characters escaped.  In
particular, `$` characters need to be escaped with `\$`.  For example, a Mongo
shell command to create a user entry with the name `bob` and the hash from the
example above would be:

```
db.user.insert({username: 'bob', hashed_password: '\$2b\$12\$VtfVij6zz20F/Qr0Ri18O.11.0LJMMXyJxAJAHQbKU0jC96eo2fr.', active: true})
```

This can be run directly from a terminal via `docker-compose exec`:

```
$ docker-compose exec db /bin/mongo kernelci --eval \
  "db.user.insert({username: 'bob', hashed_password: '\$2b\$12\$VtfVij6zz20F/Qr0Ri18O.11.0LJMMXyJxAJAHQbKU0jC96eo2fr.', active: true})"
MongoDB shell version v5.0.3
connecting to: mongodb://127.0.0.1:27017/kernelci?compressors=disabled&gssapiServiceName=mongodb
Implicit session: session { "id" : UUID("84a62d1b-4b06-4631-8227-413964826100") }
MongoDB server version: 5.0.3
WriteResult({ "nInserted" : 1 })
```

### Create an API token

Then to get an API token, the `/token` API endpoint can be used.  For example,
with the same user and password as used previously:

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

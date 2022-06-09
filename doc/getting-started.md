---
title: "Getting Started"
date: 2022-03-18
description: "Setting up a local instance"
weight: 1
---

This guide should provide all the basic information to set up a local
development system with an API instance and a minimal pipeline.

A [docker-compose](https://docs.docker.com/compose/) environment is provided
for both the new API and the pipeline.  On Debian systems, the main
prerequisite is to install it:

```
sudo apt install docker-compose
```

All the dependencies for running the API services as well as the pipeline
clients are then handled using Docker images.

## Setting up an API instance

This section covers how to set up a local API instance using the default
self-contained configuration.  It doesn't rely on any external services.

### Create the environment file

The first step is to populate the `docker-compose` environment file.  It
contains some settings specific to the local instance.

The API authentication mechanism requires a secret key used internally with
encryption algorithms.  To generate one for your local instance:

```
$ echo SECRET_KEY=$(openssl rand -hex 32) >> .env
```

This `SECRET_KEY` environment variable is currently the only required one.

### Start docker-compose

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
However, sending data with `POST` and `PUT` requests can typically only be done
by authenticated users.  This will be required to run a full pipeline or to
subscribe to the pub/sub interface.  At the moment, there is no web UI for
creating new user accounts or obtaining API tokens so it needs to be done
manually.

First, get an encrypted hash for your password with the `/hash` API endpoint.
This uses a `POST` method to avoid putting the plaintext password in the URL
which could be leaked in server logs, but it doesn't require authentication
since it's needed to create an initial user account.  For example, if the
password is `hello`:

```
curl \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"password": "hello"}' \
  http://localhost:8001/hash
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

Even though after creating the above user, we would be able to run API, ideally, an admin user needs to be created first (using terminal), and then additional users can be created with the `/user` endpoint or kernelci-core command line tools (`kci_data`). The instructions are described [here](https://kernelci.org/docs/api/api-details/#users).

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

The token for an admin user should be created with admin scope so that other users can be created using kernelci-core command line tools or `/user` endpoint. More details are described [here](https://kernelci.org/docs/api/api-details/#create-an-API-token-with-security-scopes).


## Setting up a Pipeline instance

The pipeline can perform a minimal set of tests using solely the API and its
associated storage.  More advanced use-cases would involve other runtime
environments such as Kubernetes LAVA, KCIDB credentials to send data etc.  On
this page, we'll focus on the simple case with just a `docker-compose` API
instance as described in the previous section and one instance for the
pipeline.

### Configure the API token

The previous section about setting up the API explains how to generate a token.
It can be made available to the pipeline clients by storing it in the `.env`
file which provides environment variables for the Docker containers:

```
echo "API_TOKEN=<your token>" >> .env
```

### Start docker-compose

Then the pipeline can simply be started with docker-compose:

```
docker-compose up --build
```

It should show some logs like this:
```
$ docker-compose up
Recreating kernelci-pipeline-tarball     ... done
Recreating kernelci-pipeline-trigger     ... done
Recreating kernelci-pipeline-runner      ... done
Recreating kernelci-pipeline-notifier    ... done
Recreating kernelci-pipeline-test_report ... done
Recreating kernelci-pipeline-kcidb       ... done
Attaching to kernelci-pipeline-tarball, kernelci-pipeline-test_report, kernelci-pipeline-kcidb, kernelci-pipeline-runner, kernelci-pipeline-notifier, kernelci-pipeline-trigger
kernelci-pipeline-tarball | Listening for new checkout events
kernelci-pipeline-tarball | Press Ctrl-C to stop.
kernelci-pipeline-test_report | Listening for test completion events
kernelci-pipeline-test_report | Press Ctrl-C to stop.
kernelci-pipeline-notifier | Listening for events...
kernelci-pipeline-notifier | Press Ctrl-C to stop.
kernelci-pipeline-runner | Listening for completed checkout events
kernelci-pipeline-runner | Press Ctrl-C to stop.
kernelci-pipeline-trigger | Sending revision node to API: 551acdc3c3d2b6bc97f11e31dcf960bc36343bfc
kernelci-pipeline-trigger | Node id: 6233a47a4d5e52296f57e3b0
kernelci-pipeline-notifier | Time                        Commit        Status    Name
kernelci-pipeline-notifier | 2022-03-17 21:13:30.673172  551acdc3c3d2  Pending   checkout
kernelci-pipeline-tarball | Updating repo for mainline
```

### Check the results

The `tarball` step can take a while, especially the first time as it sets up a
full Linux kernel repository and checks out the source code.  If things work
correctly, there should be a test report printed in the logs eventually:

```
kernelci-pipeline-test_report | mainline/master v5.17-rc8-45-g551acdc3c3d2: 1 runs, 0 failures
kernelci-pipeline-test_report |
kernelci-pipeline-test_report | test            | result
kernelci-pipeline-test_report | ----------------+-------
kernelci-pipeline-test_report | check-describe  | pass
kernelci-pipeline-test_report |
kernelci-pipeline-test_report |   Tree:     mainline
kernelci-pipeline-test_report |   Branch:   master
kernelci-pipeline-test_report |   Describe: v5.17-rc8-45-g551acdc3c3d2
kernelci-pipeline-test_report |   URL:      https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
kernelci-pipeline-test_report |   SHA1:     551acdc3c3d2b6bc97f11e31dcf960bc36343bfc
```

You may also check the logs from the `notifier` which prints all the events
sent by the API (run this in a separate shell if `docker-compose` is running in
the foreground):

```
$ docker-compose logs notifier
Attaching to kernelci-pipeline-notifier
kernelci-pipeline-notifier | Listening for events...
kernelci-pipeline-notifier | Press Ctrl-C to stop.
kernelci-pipeline-notifier | Time                        Commit        Status    Name
kernelci-pipeline-notifier | 2022-03-17 21:13:30.673172  551acdc3c3d2  Pending   checkout
kernelci-pipeline-notifier | 2022-03-17 21:14:30.837013  551acdc3c3d2  Pass      checkout
kernelci-pipeline-notifier | 2022-03-17 21:14:30.912592  551acdc3c3d2  Pending   check-describe
kernelci-pipeline-notifier | 2022-03-17 21:14:54.952120  551acdc3c3d2  Pass      check-describe
```

Meanwhile, the API logs should also show all the API calls (here's just the
first few lines):

```
kernelci-api | INFO:     172.24.0.1:38268 - "POST /subscribe/node HTTP/1.1" 200 OK
kernelci-api | INFO:     172.24.0.1:38290 - "POST /subscribe/node HTTP/1.1" 200 OK
kernelci-api | INFO:     172.24.0.1:38300 - "POST /subscribe/node HTTP/1.1" 200 OK
kernelci-api | INFO:     172.24.0.1:38310 - "POST /subscribe/node HTTP/1.1" 200 OK
kernelci-api | INFO:     172.24.0.1:38322 - "GET /nodes?revision.commit=551acdc3c3d2b6bc97f11e31dcf960bc36343bfc HTTP/1.1" 200 OK
kernelci-api | INFO:     172.24.0.1:38326 - "POST /node HTTP/1.1" 200 OK
kernelci-api | INFO:     172.24.0.1:38316 - "GET /listen/920 HTTP/1.1" 200 OK
kernelci-api | INFO:     172.24.0.1:38306 - "GET /listen/919 HTTP/1.1" 200 OK
kernelci-api | INFO:     172.24.0.1:38296 - "GET /listen/918 HTTP/1.1" 200 OK
kernelci-api | INFO:     172.24.0.1:38278 - "GET /listen/917 HTTP/1.1" 200 OK
kernelci-api | INFO:     172.24.0.1:38334 - "GET /node/6233a47a4d5e52296f57e3b0 HTTP/1.1" 200 OK
kernelci-api | INFO:     172.24.0.1:38340 - "GET /node/6233a47a4d5e52296f57e3b0 HTTP/1.1" 200 OK
kernelci-api | INFO:     172.24.0.1:38336 - "GET /node/6233a47a4d5e52296f57e3b0 HTTP/1.1" 200 OK
```

## What next?

The `check-describe` test is a very basic hack to quickly exercise the
pipeline.  It will compare the string produced by `git describe` and the kernel
revision information from the top of the `Makefile` in the source tree.  This
is run locally as a Python script, directly in the Docker container where
`runner.py` is running.  It's not practical to run all tests like this, they
would typically need to be scheduled in a different runtime environment such as
Kubernetes or LAVA.  Having the ability to run some tests locally mostly helps
with developing things quickly and in a self-contained way.

There are a number of parameters used in `docker-compose.yaml` files which can
be adjusted for various reasons, typically when deploying a public instance.
Also, some extra services can be used such as Kubernetes, LAVA, KCIDB, Atlas,
Cloud storage etc.  All this will need to be detailed in full in the
documentation as things progress.

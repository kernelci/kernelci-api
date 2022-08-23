---
title: "API details"
date: 2022-08-23
description: "KernelCI API building blocks"
weight: 3
---

This guide describes the KernelCI API components such as data models and the
Pub/Sub interface in detail.  It also explains how to use the API directly for
setting things up and issuing low-level queries.


## Environment Variables

General instructions about the environment file are described on the [getting
started](https://kernelci.org/docs/api/getting-started/#create-the-environment-file)
page.  This section goes through all the environment variables used by the API.

### Set ALGORITHM and ACCESS_TOKEN_EXPIRE_MINUTES in environment file

We need to specify an algorithm for JWT token encoding and decoding. ALGORITHM
variable needs to be passed in the parameter for that.  ALGORITHM is set
default to HS256.  We have used ACCESS_TOKEN_EXPIRE_MINUTES variable to set
expiry time on generated jwt access token.  ACCESS_TOKEN_EXPIRE_MINUTES is set
default to None.  If a user wants to change any of the above variables, they
should be added to the .env file.


## Users

`User` model objects can be created from a terminal or using `/user` endpoint.

### Create an admin user

The very first admin user needs to be created from terminal.  To create an
admin user from a terminal, provide `is_admin: 1` to the request:

```
sudo docker-compose exec db /bin/mongo kernelci --eval   "db.user.insert({username: 'admin', hashed_password: '\$2b\$12\$VtfVij6zz20F/Qr0Ri18O.11.0LJMMXyJxAJAHQbKU0jC96eo2fr.', active: true, is_admin: 1})"
MongoDB shell version v5.0.8
connecting to: mongodb://127.0.0.1:27017/kernelci?compressors=disabled&gssapiServiceName=mongodb
Implicit session: session { "id" : UUID("03737b4c-7528-43ae-9cb8-8f345748267f") }
MongoDB server version: 5.0.8
WriteResult({ "nInserted" : 1 })
```

Regular users can also be created this way without the `is_admin` attribute.


### Create an API token with security scopes

We can associate available security scopes with an API token. Currently
available scopes are 'admin' (admin user permissions) and 'users' (regular user
permissions).

To get a token with desired user scope, provide `scope` to request data
dictionary along with the username and password.  Multiple scopes can be
provided with white space separation. For example:

```
$ curl -X 'POST' \
  'http://localhost:8001/token' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  s-d 'grant_type=&username=test_admin&password=admin&scope=admin users'
{'access_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X2FkbWluIiwic2NvcGVzIjpbImFkbWluIl19.NWShAwOodFl2iCcDh0YB8O4xzfaRlIS4GkzUO8OQhQg', 'token_type': 'bearer'}
```

> **Note** Only admin users can provide `admin` scope to the `/token` endpoint.

### Create user using endpoint

Now, we can use above created admin user to create regular users and other
admin users using `/user` API endpoint.  We need to provide token (retrieved
with scope admin) to the endpoint for the authorization.

To create a regular user, provide a username to request query parameter and
password to request data dictionary.

```
$ curl -X 'POST'
  'http://localhost:8001/user/test' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Iiwic2NvcGVzIjpbImFkbWluIiwidXNlciJdfQ.KhcIWfMRr3xTFSCLcr5L4KTUVSsfSsLeyRDEjgkQRBg' \
  -d '{"password": "test"}'
{'_id': '615f30020eb7c3c6616e5ac3', 'username': 'test', 'hashed_password': '$2b$12$Whi.dpTC.HR5UHMdMFQeOe1eD4oXaP08oW7ogYqyiNziZYNdUHs8i', 'active': True, 'is_admin': False}
```

To create an admin user, provide a username, and `is_admin` flag to request
query parameter and password to request data dictionary.

```
$ curl -X 'POST' 'http://localhost:8001/user/test_admin?is_admin=1' -H 'accept: application/json'   -H 'Content-Type: application/json'  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Iiwic2NvcGVzIjpbImFkbWluIiwidXNlciJdfQ.KhcIWfMRr3xTFSCLcr5L4KTUVSsfSsLeyRDEjgkQRBg' -d '{"password": "admin"}'
{'_id': '615f30020eb7c3c6616e5ac6', 'username': 'test_admin', 'hashed_password': '$2b$12$Whi.dpTC.HR5UHMdMFQeOe1eD4oXaP08oW7ogYqyiNziZYNdUHs8i', 'active': True, 'is_admin': True}
```

Another way of creating users is to use `kci_data` from kernelci-core. The
instructions are described
[here](https://kernelci.org/docs/core/kci_data/#creating-user).


## Nodes

As a proof-of-concept, an object model called `Node` is defined in this API.
It's possible to create new objects and retrieve them via the API.

### Create a Node

To create an object of `Node` model, a `POST` request should be made along with
the Node attributes. This requires an authentication token:

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
{"_id":"61bda8f2eb1a63d2b7152418","kind":"node","name":"checkout","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":null,"status":"pending","result":null, "created":"2022-02-02T11:23:03.157648", "updated":"2022-02-02T11:23:03.157648"}
```

### Getting Nodes back

Reading Node doesn't require authentication, so plain URLs can be used.

To get node by ID, use `/node` endpoint with node ID as a path parameter:

```
$ curl http://localhost:8001/node/61bda8f2eb1a63d2b7152418
{"_id":"61bda8f2eb1a63d2b7152418","kind":"node","name":"checkout","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":null,"status":"pending","result":null, "created":"2022-02-02T11:23:03.157648", "updated":"2022-02-02T11:23:03.157648"}
```

To get all the nodes as a list, use the `/nodes` API endpoint:

```
$ curl http://localhost:8001/nodes
[{"_id":"61b052199bca2a448fe49673","kind":"node","name":"checkout","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":null,"status":"pending","result":null, "created":"2022-02-01T11:23:03.157648", "updated":"2022-02-02T11:23:03.157648"},{"_id":"61b052199bca2a448fe49674","kind":"node","name":"check-describe","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":"61b052199bca2a448fe49673","status":"pending", "result":null,"created":"2022-01-02T10:23:03.157648", "updated":"2022-01-02T11:23:03.157648"}]
```

To get nodes by providing attributes, use `/nodes` endpoint with query
parameters. All the attributes except node ID can be passed to this endpoint.
In case of ID, please use `/node` endpoint with node ID as described above.

```
$ curl 'http://localhost:8001/nodes?name=checkout&revision.tree=mainline'
[{"_id":"61b052199bca2a448fe49673","kind":"node","name":"checkout","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":null,"status":"pending","result":null, "created":"2022-02-01T11:23:03.157648", "updated":"2022-02-02T11:23:03.157648"}]
```

### Update a Node

To update an existing node, use PUT request to `node/{node_id}` endpoint.

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
{"_id":"61bda8f2eb1a63d2b7152418","kind":"node","name":"checkout-test","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":null,"status":"pending","result":null, "created":"2022-02-02T11:23:03.157648", "updated":"2022-02-02T12:23:03.157648"}
```

### State diagram

The Node objects are governed by the following state machine:

```mermaid
graph LR
  running(Running) --> job{successful?}
  running -.-> |timeout| done(Done)
  job --> |no| done(Done)
  job --> |yes| available(Available)
  available -.-> |timeout| done
  available --> |holdoff expired| closing(Closing)
  closing -.-> |timeout| done
  closing --> |child nodes done| done
```

The state of the Node is kept in the `state` field in the `Node` models.  The
different state values are described below:

Running
: The job has been scheduled and there is no result yet.

Available
: The job was successful.  Child nodes that depend on the job's success can now
  be created.

Closing
: The holdoff time has been reached, the node is now waiting for any closing
  child nodes to reach the Done state.

Done
: The node has reached its final state.


> **Note** The information whether the job succeeded or not, or if any tests
> passed or not is stored in a separate field `result`.  The state machine
> doesn't rely on the data field at all, it's considered extra meta-data used
> for looking at the actual results.  If a job fails, it goes straight from
> Running to Done and any service waiting for it to be Available will know it
> can't be used (for example, runtime tests can't be scheduled if a kernel
> build failed).

There are two fields that can cause time-driven state transitions:

holdoff
: This is for the node to remain in the Available state for a minimum amount of
  time and allow other nodes that depend on its success to be created.  Without
  this time constraint, there would be a race condition when the job is
  complete as without any child nodes it would go directly to Done.

timeout
: This is the time when the node needs to go to the Done state regardless of
  its current state.  The main reasons why this is needed are for when a node
  gets stuck and never completes its job, or while waiting for child nodes to
  complete.

## Pub/Sub and CloudEvent

The API provides a publisher / subscriber interface so clients can listen to
events and publish them too.  All the events are formatted using
[CloudEvents](https://cloudevents.io).

### Listen & Publish CloudEvent

The
[`client.py`](https://github.com/kernelci/kernelci-api/blob/main/api/client.py)
script provides a reference implementation for publishing and listening to
events.

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

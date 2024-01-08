---
title: "API details"
date: 2023-09-27
description: "KernelCI API building blocks"
weight: 3
---

GitHub repository:
[`kernelci-api`](https://github.com/kernelci/kernelci-api.git)

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


### Configure Redis and Mongo

By default, API uses Redis and Database services specified in [`docker-compose.yaml`](https://github.com/kernelci/kernelci-api/blob/main/docker-compose.yaml).
API is configured to use redis hostname `redis` and database service
URL `mongodb://db:27017` at the moment.
In case of using different services or configurations, `REDIS_HOST` and `MONGO_SERVICE` variables should be added to .env file.


## Users

`User` model objects can be created using `/user` endpoint. Only admin
users are allowed to create user accounts.

### Create an admin user

The very first admin user needs to be created with
[`api.admin`](https://github.com/kernelci/kernelci-api/blob/main/api/admin.py)
tool provided in the `kernelci-api` repository.
[Here](/docs/api/local-instance/#create-an-admin-user-account) is a guide to
setup an admin user. We can use this admin user to create other user accounts.


### Create user using endpoint

Now, we can use above created admin user to create regular users and other
admin users using `/user/register` API endpoint.  We need to provide token to the endpoint for the authorization.

To create a regular user, provide username, email address, and password to request data dictionary.

```
$ curl -X 'POST'
  'http://localhost:8001/latest/user/register' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Iiwic2NvcGVzIjpbImFkbWluIiwidXNlciJdfQ.KhcIWfMRr3xTFSCLcr5L4KTUVSsfSsLeyRDEjgkQRBg' \
  -d '{"username":"test", "email": "test@kernelci.org", "password": "test"}'
{'id': '615f30020eb7c3c6616e5ac3', 'email': 'test@kernelci.org', 'is_active':true, 'is_superuser':false, 'is_verified':false, 'username': 'test', 'groups': []}
```

An user accout can be added to multiple user groups by providing user group names to request query parameter. All the admin users
should be added to `admin` group by default.
To create an admin user, provide username, email, password, `"groups": ["admin"]`, and `"is_superuser": 1` to request data dictionary.

```
$ curl -X 'POST' 'http://localhost:8001/latest/user/register' -H 'accept: application/json'   -H 'Content-Type: application/json'  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Iiwic2NvcGVzIjpbImFkbWluIiwidXNlciJdfQ.KhcIWfMRr3xTFSCLcr5L4KTUVSsfSsLeyRDEjgkQRBg' -d '{"username": "test_admin", "email": "test-admin@kernelci.org", "password": "admin", "groups": ["admin"], "is_superuser": 1}'
{'_id': '615f30020eb7c3c6616e5ac6', 'username': 'test_admin', 'email': 'test-admin@kernelci.org', 'is_active':true, 'is_superuser':true, 'is_verified':false, 'groups': [{'id':'648c07a70fccad400a122509','name':'admin'}]}
```

Another way of creating users is to use `kci user add` tool from kernelci-core.


## Nodes

As a proof-of-concept, an object model called `Node` is defined in this API.
It's possible to create new objects and retrieve them via the API.

### Create a Node

To create an object of `Node` model, a `POST` request should be made along with
the Node attributes. This requires an authentication token:

```
$ curl -X 'POST' \
  'http://localhost:8001/latest/node' \
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
$ curl http://localhost:8001/latest/node/61bda8f2eb1a63d2b7152418
{"_id":"61bda8f2eb1a63d2b7152418","kind":"node","name":"checkout","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":null,"status":"pending","result":null, "created":"2022-02-02T11:23:03.157648", "updated":"2022-02-02T11:23:03.157648"}
```

To get all the nodes as a list, use the `/nodes` API endpoint:

```
$ curl http://localhost:8001/latest/nodes
[{"_id":"61b052199bca2a448fe49673","kind":"node","name":"checkout","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":null,"status":"pending","result":null, "created":"2022-02-01T11:23:03.157648", "updated":"2022-02-02T11:23:03.157648"},{"_id":"61b052199bca2a448fe49674","kind":"node","name":"check-describe","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":"61b052199bca2a448fe49673","status":"pending", "result":null,"created":"2022-01-02T10:23:03.157648", "updated":"2022-01-02T11:23:03.157648"}]
```

To get nodes by providing attributes, use `/nodes` endpoint with query
parameters. All the attributes except node ID can be passed to this endpoint.
In case of ID, please use `/node` endpoint with node ID as described above.

```
$ curl 'http://localhost:8001/latest/nodes?name=checkout&revision.tree=mainline'
[{"_id":"61b052199bca2a448fe49673","kind":"node","name":"checkout","revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"2a987e65025e2b79c6d453b78cb5985ac6e5eb26","describe":"v5.16-rc4-31-g2a987e65025e"},"parent":null,"status":"pending","result":null, "created":"2022-02-01T11:23:03.157648", "updated":"2022-02-02T11:23:03.157648"}]
```

Attributes along with comparison operators are also supported for the
`/nodes` endpoint. The attribute name and operator should be separated by `__` i.e. `attribute__operator`. Supported operators are `lt`(less than), `gt`(greater than), `lte`(less than or equal to), and `gte`(greater than or equal to).

```
$ curl 'http://localhost:8001/latest/nodes?name=checkout&created__gt=2022-12-06T04:59:08.102000'
{"items":[{"_id":"638ecc1c749a8d1209b758af","kind":"node","name":"checkout","path":["checkout"],"group":null,"revision":{"tree":"mainline","url":"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git","branch":"master","commit":"bce9332220bd677d83b19d21502776ad555a0e73","describe":"v6.1-rc8-3-gbce9332220bd","version":{"version":6,"patchlevel":1,"sublevel":null,"extra":"-rc8-3-gbce9332220bd","name":null}},"parent":null,"state":"done","result":"pass","artifacts":{"tarball":"http://172.17.0.1:8002/linux-mainline-master-v6.1-rc8-3-gbce9332220bd.tar.gz"},"created":"2022-12-06T04:59:08.959000","updated":"2022-12-06T05:11:33.098000","timeout":"2022-12-07T04:59:08.959000","holdoff":"2022-12-06T05:11:30.873000"}],"total":1,"limit":50,"offset":0}
```

> **Note** In order to support comparison operators in URL request parameters, models can not contain `__` in the field name.

Nodes with `null` fields can also be retrieved using the endpoint.
For example, the below command will get all the nodes with `parent` field set to `null`:

```
$ curl 'http://localhost:8001/latest/nodes?parent=null'
"items":[{"_id":"63c549319fb3b62c7626e7f9","kind":"node","name":"checkout","path":["checkout"],"group":null,"revision":{"tree":"kernelci","url":"https://github.com/kernelci/linux.git","branch":"staging-mainline","commit":"1385303d0d85c68473d8901d69c7153b03a3150b","describe":"staging-mainline-20230115.1","version":{"version":6,"patchlevel":2,"sublevel":null,"extra":"-rc4-2-g1385303d0d85","name":null}},"parent":null,"state":"available","result":null,"artifacts":{"tarball":"http://172.17.0.1:8002/linux-kernelci-staging-mainline-staging-mainline-20230115.1.tar.gz"},"created":"2023-01-16T12:55:13.879000","updated":"2023-01-16T12:55:51.780000","timeout":"2023-01-16T13:55:13.877000","holdoff":"2023-01-16T13:05:51.776000"},{"_id":"63c549329fb3b62c7626e7fa","kind":"node","name":"checkout","path":["checkout"],"group":null,"revision":{"tree":"kernelci","url":"https://github.com/kernelci/linux.git","branch":"staging-next","commit":"39384a5d7e2eb2f28039a92c022aed886a675fbf","describe":"staging-next-20230116.0","version":{"version":6,"patchlevel":2,"sublevel":null,"extra":"-rc4-5011-g39384a5d7e2e","name":null}},"parent":null,"state":"available","result":null,"artifacts":{"tarball":"http://172.17.0.1:8002/linux-kernelci-staging-next-staging-next-20230116.0.tar.gz"},"created":"2023-01-16T12:55:14.706000","updated":"2023-01-16T12:56:30.886000","timeout":"2023-01-16T13:55:14.703000","holdoff":"2023-01-16T13:06:30.882000"}],"total":2,"limit":50,"offset":0}
```

Please make sure that the query parameter provided with the `null` value in the request exists in the `Node` schema. Otherwise, the API will behave unexpectedly and return all the nodes.


### Update a Node

To update an existing node, use PUT request to `node/{node_id}` endpoint.

```
$ curl -X 'PUT' \
  'http://localhost:8001/latest/node/61bda8f2eb1a63d2b7152418' \
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

### Getting Nodes count

To get a count of all the nodes, use GET request to `/count` endpoint.

```
$ curl http://localhost:8001/latest/count
4
```

To get count of nodes matching provided attributes, use `/count` endpoint with query parameters. All the Node attributes except ID and timestamps(created, updated, timeout, and holdoff) can be passed to this endpoint.
```
$ curl http://localhost:8001/latest/count?name=checkout
3
$ curl http://localhost:8001/latest/count?revision.branch=staging-mainline
1
```

In case of providing multiple attributes, it will return count of nodes matching all the attributes.
```
$ curl 'http://localhost:8001/latest/count?name=checkout&artifacts.tarball=http://172.17.0.1:8002/linux-kernelci-staging-mainline-staging-mainline-20220927.0.tar.gz'
1
```

Same as `/nodes`, the `/count` endpoint also supports comparison operators for request query parameters.
```
$ curl 'http://localhost:8001/latest/count?name=checkout&created__lt=2022-12-06T04:59:08.102000'
3
```

To query the count of nodes with `null` attributes, use the endpoint with
query parameters set to `null`.
```
$ curl 'http://localhost:8001/latest/count?result=null'
2
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


## Migrations

Migrations are required to propagate the changes made to API models to the database like updating or deleting a model field or a model.

[`pymongo-migrate`](https://github.com/stxnext/pymongo-migrate) package has been integrated to enable migration support in the API.

Use the below command to run migration from the `api` Docker container.
```
$ docker-compose exec api /bin/sh -c 'pymongo-migrate migrate -u mongodb://db/kernelci -m migrations -v'
2022-11-25 06:12:17,996 [DEBUG]  Migration target not specified, assuming upgrade
Command find#1957747793 STARTED
SON([('find', 'pymongo_migrate'), ('filter', {'name': '20221014061654_set_timeout'}), ('limit', 1), ('singleBatch', True), ('lsid', {'id': Binary(b'7\x18\xe4\xe7\xd0\x88Gc\xafq\x0f[\x8b\x8d\xec\xde', 4)}), ('$db', 'kernelci'), ('$readPreference', {'mode': 'primaryPreferred'})])
Command find#1957747793 SUCCEEDED in 215us
2022-11-25 06:12:17,998 [INFO ]  Running upgrade migration '20221014061654_set_timeout'
Command find#424238335 STARTED
SON([('find', 'node'), ('filter', {}), ('lsid', {'id': Binary(b'7\x18\xe4\xe7\xd0\x88Gc\xafq\x0f[\x8b\x8d\xec\xde', 4)}), ('$db', 'kernelci'), ('$readPreference', {'mode': 'primaryPreferred'})])
Command find#424238335 SUCCEEDED in 4404us
Command update#719885386 STARTED
SON([('update', 'node'), ('ordered', True), ('lsid', {'id': Binary(b'7\x18\xe4\xe7\xd0\x88Gc\xafq\x0f[\x8b\x8d\xec\xde', 4)}), ('$db', 'kernelci'), ('$readPreference', {'mode': 'primary'}), ('updates', [SON([('q', {'_id': ObjectId('63720d307d572b5aa15462f4')}), ('u', {'$set': {'timeout': datetime.datetime(2022, 11, 14, 15, 41, 4, 175000)}}), ('multi', False), ('upsert', False)])])])
Command update#719885386 SUCCEEDED in 989us
Command update#1649760492 STARTED
SON([('update', 'node'), ('ordered', True), ('lsid', {'id': Binary(b'7\x18\xe4\xe7\xd0\x88Gc\xafq\x0f[\x8b\x8d\xec\xde', 4)}), ('$db', 'kernelci'), ('$readPreference', {'mode': 'primary'}), ('updates', [SON([('q', {'_id': ObjectId('63720d317d572b5aa15462f5')}), ('u', {'$set': {'timeout': datetime.datetime(2022, 11, 14, 15, 41, 5, 454000)}}), ('multi', False), ('upsert', False)])])])
Command update#1649760492 SUCCEEDED in 151us
```

The above command will run the necessary `upgrade` for the migrations stored in `migrations` directory.
If migration target is specified, it will run the necessary `upgrade` or `downgrade` to reach the target.

The status of migration can be found with the below command:
```
$ docker-compose exec api /bin/sh -c 'pymongo-migrate show -u mongodb://db/kernelci -m migrations -v'
Migration name            	Applied timestamp
Command find#1957747793 STARTED
SON([('find', 'pymongo_migrate'), ('filter', {'name': '20221014061654_set_timeout'}), ('limit', 1), ('singleBatch', True), ('lsid', {'id': Binary(b'\x1e\x0b"M\x1f\xb3N\xf4\xa3\x00\xaa\xff]c\xf8\xe5', 4)}), ('$db', 'kernelci'), ('$readPreference', {'mode': 'primaryPreferred'})])
Command find#1957747793 SUCCEEDED in 228us
20221014061654_set_timeout	2022-11-25T07:00:14.923000+00:00
```

If the `upgrade` has already been applied, `downgrade` can be run using the below command:
```
$ docker-compose exec api /bin/sh -c 'pymongo-migrate downgrade -u mongodb://db/kernelci -m migrations -v'
Command find#1957747793 STARTED
SON([('find', 'pymongo_migrate'), ('filter', {'name': '20221014061654_set_timeout'}), ('limit', 1), ('singleBatch', True), ('lsid', {'id': Binary(b'\x0c}X\x9d\xe9{O\xd5\x85\xb3\x904\xa2R\x89i', 4)}), ('$db', 'kernelci'), ('$readPreference', {'mode': 'primaryPreferred'})])
Command find#1957747793 SUCCEEDED in 237us
2022-11-25 07:07:21,857 [INFO ]  Running downgrade migration '20221014061654_set_timeout'
2022-11-25 07:07:21,858 [INFO ]  Execution time of '20221014061654_set_timeout': 1.049041748046875e-05 seconds
Command update#424238335 STARTED
SON([('update', 'pymongo_migrate'), ('ordered', True), ('lsid', {'id': Binary(b'\x0c}X\x9d\xe9{O\xd5\x85\xb3\x904\xa2R\x89i', 4)}), ('$db', 'kernelci'), ('$readPreference', {'mode': 'primary'}), ('updates', [SON([('q', {'name': '20221014061654_set_timeout'}), ('u', {'name': '20221014061654_set_timeout', 'applied': None}), ('multi', False), ('upsert', True)])])])
Command update#424238335 SUCCEEDED in 279us
```


## Pub/Sub and CloudEvent

The API provides a publisher / subscriber interface so clients can listen to
events and publish them too.  All the events are formatted using
[CloudEvents](https://cloudevents.io).

### Listen & Publish CloudEvent

The API provides different endpoints for publishing and listening to events.

For example, subscribe to a channel first:
```
curl -X 'POST' 'http://localhost:8001/latest/subscribe/abc' -H 'Authorization: Bearer TOKEN'
{"id":800,"channel":"abc","user":"bob"}
```

Use the subscription ID from the response to listen to the events:
```
$ curl -X 'GET' 'http://localhost:8001/latest/listen/800' -H 'Authorization: Bearer TOKEN'
```

Then in a second terminal publish `CloudEvent` message:
```
$ curl -X 'POST' 'http://localhost:8001/latest/publish/abc' -H 'Authorization: Bearer TOKEN' -H 'Content-Type: application/json' \
-d '{"data": {"sample_key":"sample_value"}}'
```
Other `CloudEvent` fields such as "type", "source", and "attributes" can also
be sent to the request dictionary above.

You should see the message appear in the first terminal inside "data" dictionary:
```
$ curl -X 'GET' 'http://localhost:8001/latest/listen/800' -H 'Authorization: Bearer TOKEN'
{"type":"message","pattern":null,"channel":"abc","data":"{\"specversion\": \"1.0\", \"id\": \"9e67036c-650e-4688-b4dd-5b2eafd21f5f\", \"source\": \"https://api.kernelci.org/\", \"type\": \"api.kernelci.org\", \"time\": \"2024-01-04T10:48:39.974782+00:00\", \"data\": {\"sample_key\": \"sample_value\"}, \"owner\": \"bob\"}"}
```

Now, unsubscribe from the channel:
```
$ curl -X 'GET' 'http://localhost:8001/latest/unsubscribe/800' -H 'Authorization: Bearer TOKEN'
```

Meanwhile, something like this should be seen in the API logs:

```
$ docker-compose logs api | tail -4
kernelci-api | INFO:     127.0.0.1:35752 - "POST /subscribe/abc HTTP/1.1" 200 OK
kernelci-api | INFO:     127.0.0.1:35810 - "POST /publish/abc HTTP/1.1" 200 OK
kernelci-api | INFO:     127.0.0.1:35754 - "GET /listen/abc HTTP/1.1" 200 OK
kernelci-api | INFO:     127.0.0.1:36744 - "POST /unsubscribe/abc HTTP/1.1" 200 OK
```

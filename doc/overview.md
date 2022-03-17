---
title: "Overview"
date: 2022-03-10
draft: true
description: "KernelCI API and Pipeline Overview"
weight: 2
---

## API architecture

The main building blocks of the API are put together this way:

```mermaid
graph TD
  api(FastAPI)
  pubsub(Pub/Sub) --- api
  redis(Redis) --- pubsub
  models(Pydantic) --- api
  db(MongoDB) --- models

  storage(Storage)
  storage --- ssh(SSH)
  storage --- http(HTTP)

  api --> client
  ssh --> client
  http --> client
```

The `client` component can be a number of things.  Each service in the pipeline
is a client, and there could be extra standalone ones too.  They interact via
the API and the storage services separately.  By default, storage is provided
by SSH for uploads and HTTP for downloads.  Production deployments may use
alternative solutions, as long as all the binaries are accessible via direct
HTTP URLs.

## Why a new API?

The new KernelCI API is a work-in-progress to replace the current
[backend](https://api.kernelci.org/) used in production, which has several
limitations.  In particular:

* Written in Python 2.7, which has now reached end-of-life
* Monolithic design with many built-in features (regression tracking, email
  reports, parsing test results directly from LAVA labs...)
* Asynchronous request handling is done using Celery, whereas modern Python can
  do this natively
* No pub/sub mechanism, orchestration relies on an external framework
  (i.e. Jenkins)


To overcome these limitations, the new API has the following characteristics:

* Based on FastAPI to provide native asynchronous request handling, data model
  validation using Pydantic, automatically generated documentation with
  [OpenAPI](https://www.openapis.org/).  See also the [OpenAPI JSON
  description](https://staging.kernelci.org:9000/openapi.json).
* Pub/SUb mechanism via the API, with Redis to manage message queues.  This can
  now be used to coordinate client-side functions and recreate a full modular
  pipeline with no additional framework
* CloudEvent for the formatting of Pub/Sub events
* Written for Python 3.10
* Authentication based on JWT for inter-operability with other services
* Storage is entirely separate from the API as it purely handles data.  An
  initial storage solution is provided using SSH for sending files and HTTP for
  serving them.

A few things aren't changing:

* MongoDB has been used with the first backend for several years and is
  providing good results.  We might just move it to a Cloud-based hosting such
  as Atlas for the future linux.kernelci.org deployment.
* Redis is still being used internally as in-memory database for various
  features in addition to the pub/sub channels

## Pipeline design

The pipeline currently has the following steps:

```mermaid
graph LR
  trigger(Trigger) --> new{New <br /> kernel?}
  new --> |yes| tarball(Tarball)
  new -.-> |no| trigger
  tarball --> |event: <br /> new revision| runner(Test <br /> Runner)
  runner --> |event: <br /> test pending| runtime(Runtime <br /> Environment)
  runtime --> |event: <br /> test complete| email(Email <br /> Generator)
```

Each step is a client for the API and associated storage.  Apart from the
runtime environment, They are all implemented in Python, rely on the [KernelCI
Core](/docs/core) tools and run in a separate `docker-compose` container.
Here's a summary of each step:

### Trigger

The Trigger step periodically checks whether a new kernel revision has appeared
on a git branch.  It first gets the revision checksum from the top of the
branch from the git repo and then queries the API to check whether it has
already been covered.  If there's no revision entry with this checksum in the
API, it then pushes one with "pending" state.

### Tarball

The Tarball step listens for pub/sub events about new pending revisions.  When
one is received, typically because the trigger pushed a new revision to the
API, it then updates a local git checkout of the full kernel source tree.  Then
it makes a tarball with the source code and pushes it to the storage.  Finally,
the URL of the tarball is added to the revision data, the status is set to
"complete" and an update is sent to the API.

### Test Runner

The Runner step listens for pub/sub events about completed revisions, typically
following the tarball step.  It will then schedule some tests to be run in
various runtime environments as defined in the pipeline YAML configuration from
the Core tools.  An data entry is sent to the API for each test submitted with
"pending" state.  It's then up to the test in the runtime environment to send
its results to the API and set the final status.

### Runtime Environment

This could be anything from a local shell (currently the only supported one),
to Kubernetes, LAVA or any arbitrary system.  Tests can be any actual work
scheduled by the Runner step such as building a kernel, running some test,
performing some static analysis etc.  Each environment needs to have its own
API token set up locally to be able to submit the results.

### Email Generator

The Email Generator step listens for pub/sub events for when tests are complete
to then generate a summary and send it via email.  The current implementation
only prints the summary in the logs, and generates one for every test results
received.  A production solution would send emails to various recipients
depending on the tests and would wait for an event signalling that a group of
tests has completed (or timed out).

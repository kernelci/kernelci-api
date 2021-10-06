KernelCI API
============

This repository is a work-in-progress implementation of a new API and database
interface for KernelCI, to replace
[kernelci-backend](https://github.com/kernelci/kernelci-backend.git).  It's
mainly based on [FastAPI](https://fastapi.tiangolo.com/), [Mongo
DB](https://www.mongodb.com/) and [Redis](https://redis.io/).


### Getting started with Docker

To start the API server, first build the Docker image and then start a
container with it:

```
$ docker build docker/api -t kernelci-server-api
[...]
Successfully tagged kernelci-server-api:latest
$ docker run -v $PWD/api:/home/kernelci/api -p 8000:8000 kernelci-server-api
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [1] using watchgod
INFO:     Started server process [8]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Then to check it's working:

```
$ curl http://localhost:8000
{"message":"KernelCI API"}
```

The container log should show:
```
INFO:     172.17.0.1:51150 - "GET / HTTP/1.1" 200 OK
```

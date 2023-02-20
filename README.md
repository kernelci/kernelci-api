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

We have already created .env file from [Authentication](https://github.com/kernelci/kernelci-api#authentication) section.
Export the file with SECRET_KEY environment variable in it:
```
export $(cat .env)
```

Run the below command from kernelci-api directory:
```
pytest -v test/
```
This will start running unit test cases from kernelci-api/test directory and display results.

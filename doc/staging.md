---
title: "Staging"
date: 2024-08-15
description: "Staging API"
weight: 5
---

Maestro maintains a staging instance for development purposes.

This environment allows you to test the latest changes and features before they are 
merged into the production KernelCI API.
If you contribute to the kernelci-core, kernelci-pipeline, or kernelci-api repositories and
open a pull request, staging will automatically incorporate your changes (provided you're on the [contributor list](https://github.com/kernelci/kernelci-deploy/blob/main/data/staging.ini))
and deploy them to the staging instance. This enables you to receive feedback
from other contributors before merging changes into the production API.
The staging instance updates every 8 hours or can be manually triggered by
the sysadmin team. You can also exclude a pull request from deployment by adding the `staging-skip` label.
It is highly recommended to set such label if your pull request is not ready for
deployment and might break the staging instance.

The staging deployment runs only
kernelci-stable, kernelci-mainline, and kernelci-next branches by default, which are mirrors of 
Linux kernel trees. If you need to test changes with a different tree or are adding a new
tree, you can use the [kci-dev](https://github.com/kernelci/kci-dev) tool to trigger jobs on the staging instance.
The staging instance is not intended for production use and stability is not
guaranteed. Occasional crashes are expected.

Please try it out and report any issues on
GitHub or ask questions through the [available contacts](https://kernelci.org/community-contact/).

[Developer documentation](https://docs.kernelci.org/maestro/pipeline/developer-documentation/)

## Requesting a user account

If your workflow requires authenticated access to the API (you need to submit your own nodes),
you need to request a user account.  This is done via the KernelCI GitHub
repository.  The user account will be created for you by the sysadmin team.

It can be done in two simple steps:

* Create an "API Staging Access" [issue on
  GitHub](https://github.com/kernelci/kernelci-project/issues/new/choose)
* Wait for an email confirmation of your user account which should contain an
  invite link (and an AzureFiles token if applicable)

> **Tip**: If you don't have a GitHub account, please send an email to
    [kernelci-sysadmin@groups.io](mailto:kernelci-sysadmin@groups.io) instead.

## Setting up the `kci` tool

While you're waiting for your user account to be created, you can already set a
few things up that don't require any account.  Several parts of the API are
publicly available for anonymous users and some commands can be run without any
API at all.

* The `kci` command line tool is available via a Docker image
  `kernelci/kernelci`.  It typically relies on a local settings file
  `kernelci.toml` which is specific to each user.  Here's a minimal file to get
  started:

```toml
[kci]
api = 'staging'
```

* Then to run a container with your own settings file:

```sh
$ mkdir kernelci
$ cd kernelci
$ cp ~/path/to/kernelci.toml .
$ docker pull kernelci/kernelci
$ docker run -v $PWD:/home/kernelci -it kernelci/kernelci /bin/bash
kernelci@3215c7c7b590:~$ kci api hello
{"message": "KernelCI API"}
```

> **Tip**: If you're wondering how it managed to find the API, take a look at
> `/etc/kernelci/core/api-configs.yaml` from within the Docker container.

From now on, all the shell commands are run **from within the same container**
so the prompt `kernelci@3215c7c7b590:~$` is being replaced with `$` to make it
easier to read.

* Once you've received your confirmation email, open the invite link and set
  your password. You can use the helper script from this repository (set
  `--api-url` or configure a `staging` instance in `usermanager.toml` and use
  `--instance staging`):

```sh
$ ./scripts/usermanager.py accept-invite \
  --api-url "https://staging.kernelci.org/latest" \
  --token "<INVITE-TOKEN>"
```

Or via curl:

```sh
$ curl -X 'POST' \
  'https://staging.kernelci.org/latest/user/accept-invite' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "token": "<INVITE-TOKEN>",
  "password": "<new-password>"
}'
```

* Then create an API token by providing your username and new
  password:

```sh
$ ./scripts/usermanager.py login \
  --api-url "https://staging.kernelci.org/latest" \
  --username <your-username>
```

* Store your API token in a `kernelci.toml` file, for example:

```toml
[kci]
api = 'staging'
indent = 4

[kci.secrets]
api.staging.token = "<your-api-token-here>"
```

* To verify things are set up correctly:

```sh
$ kci user whoami
{
    "id": "64f4a0978326c545a780bffc",
    "email": "<your-email>"
    "is_active": true,
    "is_superuser": false,
    "is_verified": true,
    "groups": [],
    "username": "<your-username>"
}
```

## Access staging containers

The staging container logs are accessible [here](https://staging.kernelci.org:9088/). It is possible to see logs for your `kci` command requests by clicking on `kernelci-api` container on the dashboard.
For example, on a successful `kci user whoami` command, you should be able to see the below log in the container logs:
```
2024-08-28T13:16:41.983273376Z INFO:     192.168.64.1:55218 - "GET /whoami HTTP/1.0" 200 OK
```

As mentioned earlier, the staging instance has been deployed to test development changes more frequently. The instance is updated every 8 hours and is being deployed with all the pull requests unless the PR has `staging-skip` label added or the PR changes are conflicting with already deployed PR.
As we are deploying changes more frequently, the instance is expected to be
vulnerable and can face crashes from time to time. Please reach out to us if you face any issues while testing with different `kci` tools.

## Going further

Now you can basically use the KernelCI API.  You can try a few things by hand,
such as subscribing to the pub/sub interface to get notified when some data
changes in the database.  A good place to take a look for ideas is the
[`kernelci-pipeline`](https://github.com/kernelci/kernelci-pipeline) repository
which contains a sample `pipeline.yaml` file used by the standard
`docker-compose` deployment.  You may also want to have a look at the rest of
the documention and the overall development [Roadmap on
GitHub](https://github.com/orgs/kernelci/projects/10/views/15).

If you're unsure what to do next, please feel free to get in touch as mentioned
at the top of this page by email, IRC or Slack.  Happy testing!

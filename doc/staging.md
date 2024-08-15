---
title: "Staging"
date: 2024-08-15
description: "Staging API"
weight: 5
---

Maestro has a staging instance running for development purposes.
It allows users to request an account on the new KernelCI API to give it a try. You can also enable your
trees, builds, and tests on it. Here is the
[developer documentation](https://docs.kernelci.org/maestro/pipeline/developer-documentation/) for the same.

[Staging
deployment](https://github.com/kernelci/kernelci-api/tree/main/kube/aks)
can already run a pipeline with KUnit, kselftest, kernel builds
and boot tests. So please give it a go and create issues on
GitHub and ask questions on the [mailing
list](mailto:kernelci@lists.linux.dev), IRC `#kernelci` on libera.chat
or [Slack](https://kernelci.slack.com) with whatever you may find.

## Requesting a user account

Anyone interested is very much encouraged to request an account.

It can be done in two simple steps:

* Create an "API Staging Access" [issue on
  GitHub](https://github.com/kernelci/kernelci-project/issues/new/choose)
* Wait for an email confirmation of your user account which should contain a
  randomly-generated password as well as an AzureFiles token

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

* Once you've received your confirmation email with your randomly-generated
  password, you should change it to use your own arbitrary one instead:

```sh
$ kci user password update <your-username>
Current password:
New password:
Retype new password:
```

* Then verify your email address by providing verification token
sent to your email:

```sh
$ kci user verify <your-email>
Sending verification token to <your-email>
Verification token: <verification-token>
Email verification successful!
```

* Then create an API token by providing your username and new
  password:

```sh
$ kci user token <your-username>
Password:
"<your-api-token-here>"
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

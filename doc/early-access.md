---
title: "Early Access"
date: 2023-09-04
description: "Beta-testing the new API"
weight: 2
---

As per the [API Transition
Timeline](https://kernelci.org/blog/posts/2023/api-timeline/), the
Early Access phase is from 4th September to 4th December 2023.  It
allows users to request an account on the new KernelCI API for
beta-testing purposes.

There are still lots of incomplete or missing features with the new
API & Pipeline.  It now has a [production-like
deployment](https://github.com/kernelci/kernelci-api/tree/main/kube/aks)
and can already run a minimalist pipeline with KUnit, a kernel build
and a boot test on QEMU.  The aim of the Early Access phase is to make
all the adjustments to the design that are necessary before reaching
full production status.  So please give it a go and create issues on
GitHub and ask questions on the [mailing
list](mailto:kernelci@lists.linux.dev), IRC `#kernelci` on libera.chat
or [Slack](https://kernelci.slack.com) with whatever you may find.

## Requesting a user account

The number of users and available resources are limited, so while we'll try and
provide an account for every request we can't give any guarantee at this stage.
Anyone interested is still very much encouraged to request an account of
course, the more users the better.

It can be done in two simple steps:

* Create an "API Early Access" [issue on
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
api = 'early-access'
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
$ kci user password update <your-user-name>
Current password:
New password:
Retype new password:
```

* Then create an API token by providing your username and new
  password:

```sh
$ kci user token <your-username>
Password:
{"access_token": "<your-api-token-here>", "token_type": "bearer"}
```

* Store your API token in a `kernelci.toml` file, for example:

```toml
[kci]
api = 'early-access'
indent = 4

[kci.secrets]
api.early-access.token = "<your-api-token-here>"
```

* To verify things are set up correctly:

```sh
$ kci user whoami
{
    "id": "64f4a0978326c545a780bffc",
    "active": true,
    "profile": {
        "username": "(your-username)",
        "hashed_password": "(password hash)",
        "groups": [],
        "email": "(email@something.com)"
    }
}
```

## Storage

File storage is managed separately from the API services.  As part of the Early
Access phase, an AzureFiles token is provided to each user to be able to upload
artifacts.  It is one of the storage solutions supported by KernelCI, you may
also use SSH or soon any S3-compatible storage.  There is a quota, currently
5TiB for all the Early Access files.  Old files will be deleted after a while
so please don't rely on it for any persistent storage.

Each user has a separate Azure File "share", so you need to add a YAML
configuration entry for your own storage.  This can be done by adding a file
such as `config/core/<your-username>.yaml`:

```yaml
storage:
  early-access-azure-<your-username>:
    storage_type: azure
    base_url: https://kciapistagingstorage1.file.core.windows.net/
    sas_public_token: "?sv=2022-11-02&ss=f&srt=sco&sp=r&se=2024-10-17T19:19:12Z&st=2023-10-17T11:19:12Z&spr=https&sig=sLmFlvZHXRrZsSGubsDUIvTiv%2BtzgDq6vALfkrtWnv8%3D"
    share: <your-username>
```

Then the token from your confirmation email needs to be stored in the
`kernelci.toml` settings file in order to make use of it.  Please note that
only the part of the URL with the arguments starting with the `?` needs to be
stored here, not the full URL.  It's convenient to also add the `storage`
config name to avoid having to pass `--storage` on the command line all the
time.  For example:

```toml
[kci]
api = "early-access"
storage = "early-access-azure-<your-username>"
indent = 4
config = ["config/core", "<your-username>.yaml"]

[kci.secrets]
api.early-access.token = "<your-api-token-here>"
storage.early-access-azure-<your-username>.credentials = "?sp=rcwdl&st=...<your-full-storage-token-here>"
```

Then here's a quick way to check it's working, still in the same container:

```sh
$ echo "your-username was here" > your-username.txt
$ kci storage upload your-username.txt
https://kciapistagingstorage1.file.core.windows.net/your-username/your-username.txt?sv=2022-11-02&ss=bfqt&srt=sco&sp=r&se=2123-07-20T22:00:00Z&st=2023-07-21T18:27:25Z&spr=https&sig=TDt3NorDXylmyUtBQnP1S5BZ3uywR06htEGTG%2BSxLWg%3D
$ curl "https://kciapistagingstorage1.file.core.windows.net/your-username/your-username.txt?sv=2022-11-02&ss=bfqt&srt=sco&sp=r&se=2123-07-20T22:00:00Z&st=2023-07-21T18:27:25Z&spr=https&sig=TDt3NorDXylmyUtBQnP1S5BZ3uywR06htEGTG%2BSxLWg%3D"
your-username was here
```

You can then use this kind of publicly-available URL to refer to files in the
data sent to API, or any URL from any arbitrary storage as long as it allows
download the file without additional authentication.  As per the help message:

```
Usage: kci storage upload [OPTIONS] FILENAME [PATH]
```

The `PATH` positional argument is optional, it's just to keep things tidy
within your own share and create a target directory where the file will get
uploaded.  For typical API data, the file names should contain unique object
IDs so there shouldn't be any collision anyway.

> **Note**: There's no way to list the files that have been uploaded via the
> `kci storage` tool yet so make sure you keep a copy of the URL.

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
at the top of this page by email, IRC or Slack.  Happy beta-testing!

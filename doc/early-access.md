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
  `kernelci.toml` which is specific to each user.  Here's a simple way to run a
  container with your own settings file:

```sh
$ mkdir kernelci
$ cd kernelci
$ echo -e "[DEFAULT]\napi_config = \"early-access\"" > kernelci.toml
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
$ kci user change_password --user <your-user-name>
Current password:
New password:
Retype new password:
```

* Then create an API token by providing your username and new
  password:

```sh
$ kci user get_token --username <your-username>
Password:
{"access_token": "<your-api-token-here>", "token_type": "bearer"}
```

* Store your API token in a `kernelci.toml` file, for example:

```toml
[DEFAULT]
api_config = "early-access"
indent = 4

[api.early_access]
api_token = "<your-api-token-here">
```

* To verify things are set up correctly:

```sh
$ kcu user whoami
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

The token from your confirmation email should also be stored in `kernelci.toml`
in order to make use of it, for example:

```toml
[DEFAULT]
api_config = "early-access"
storage_config = 'early-access-azure'
indent = 4

[api.early-access]
api_token = "your-api-token-here"

[storage.early-access-azure]
storage_cred = "your-azure-files-token-here"
```

Then here's a quick way to check it's working, still in the same container:

```sh
$ echo "your-username was here" > your-username.txt
$ kci storage upload your-username.txt --verbose --upload-path=your-username
https://kciapistagingstorage1.file.core.windows.net/early-access/your-username/your-username.txt?sv=2022-11-02&ss=bfqt&srt=sco&sp=r&se=2123-07-20T22:00:00Z&st=2023-07-21T18:27:25Z&spr=https&sig=TDt3NorDXylmyUtBQnP1S5BZ3uywR06htEGTG%2BSxLWg%3D
$ curl "https://kciapistagingstorage1.file.core.windows.net/early-access/your-username/your-username.txt?sv=2022-11-02&ss=bfqt&srt=sco&sp=r&se=2123-07-20T22:00:00Z&st=2023-07-21T18:27:25Z&spr=https&sig=TDt3NorDXylmyUtBQnP1S5BZ3uywR06htEGTG%2BSxLWg%3D"
your-username was here
```

You can then use this kind of publicly-available URL to refer to files in the
data sent to API, or any URL from any arbitrary storage as long as it allows
download the file without additional authentication.  The `--upload-path`
argument is optional, it's just to keep things tidy and not mix up your data
with other users.  For typical API data, the file names should contain unique
object IDs so there shouldn't be any collision anyway.

> **Note**: There's no way to list the files that have been uploaded via the
> `kci` tool yet so make sure you keep a copy of the URLs.  The `--verbose`
> argument is needed to get the URL after an upload.

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

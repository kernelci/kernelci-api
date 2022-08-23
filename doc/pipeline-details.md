---
title: "Pipeline details"
date: 2022-08-23
description: "KernelCI Pipeline design details"
weight: 4
---

## Pipeline detailed design

Below is the detailed pipeline flow diagram with associated node and pub/sub event:

```mermaid
flowchart
    start([Start]) --> trigger_service
    subgraph trigger_service[Trigger Service]
        trigger[Trigger] --> kernel_revision{New kernel <br/>revision ?}
        kernel_revision --> |No| trigger
        kernel_revision --> |Yes| checkout[Create 'checkout' node <br />state=available, result=None, set holdoff]
    end
    subgraph tarball_service[Tarball Service]
        checkout --> |event: <br />checkout created, state=available| tarball[Tarball]
        tarball --> tarball_node[Create 'tarball' node <br />state=running, result=None, holdoff=None <br />Update 'checkout' node <br />with describe and artifacts]
        tarball_node --> upload_tarball[Create and upload tarball to the storage <br />state=available, result=None, set holdoff]
    end
    subgraph runner_service[Runner Service]
        upload_tarball --> |event: <br />tarball updated <br />state=available| runner[Runner]
        runner --> runner_node[Create build/test node <br />state=running, result=None, holdoff=None]
    end
    subgraph Run Builds/Tests
        runner_node --> runtime[Runtime Environment]
        runtime --> set_available[Update node<br />state=available, result=None, set holdoff]
        set_available --> run_job[Run build/test job]
        run_job --> job_done{Job done?}       
        job_done --> |Yes| pass_runner_node[Update node<br />state=done, result=pass/fail/skip]
        job_done --> |No| run_job
    end
    subgraph set_completed_service[Set Completed Service]
        get_closing_parent_nodes[Get nodes <br /> with state=available]
        set_completed[Set Completed] --> get_closing_parent_nodes
        get_closing_parent_nodes --> hold_off_reached{Hold off reached?}
        hold_off_reached --> |Yes| node_completed{All child <br />nodes completed ?}
        node_completed --> |Yes| generate_completed[Set node <br />state=done, result=pass]
        node_completed --> |No| set_closing[Set node <br />state=closing]
    end
    subgraph test_report_service[Test Report Service]
        test_report[Test Report] --> email_report[Generate and <br />email test report <br />for tarball]
    end
    subgraph set_timeout_service[Set Timeout Service]
        set_timeout[Set Timeout] --> get_incomplete_nodes
        get_incomplete_nodes[Get nodes <br /> with state=closing] --> timeout
        timeout{Node timed out?} --> |Yes| set_incomplete[Set parent and closing child nodes <br /> state=done, result=incomplete]
        timeout --> |No| get_incomplete_nodes
    end
    generate_completed --> |event: <br />updated <br /> state=done| received_tarball
    set_incomplete --> |event: <br />updated <br /> state=done| received_tarball
    received_tarball{Received tarball node? } --> |Yes| test_report
    test_report_service --> stop([Stop])
```

Here's a description of each client script:

### Trigger

The pipeline starts with the trigger script.
The Trigger periodically checks whether a new kernel revision has appeared
on a git branch.  If so, it firsts checks if API has already created a node with
the record. If not, it then pushes one node named "checkout". The node's state will be "available" and the result is not defined yet. This will generate pub/sub event of node creation.

### Tarball

When the trigger pushes new revision node (checkout), the tarball receives a pub/sub event. A node named 'tarball' is pushed with the 'running' state. The tarball then updates a local git checkout of the full kernel source tree.  Then it makes a tarball with the source code and pushes it to the API storage. The state of the tarball node will be updated to 'available'. The URL of the tarball is also added to the artifacts of the revision node.

### Runner

The Runner step listens for pub/sub events about available tarball node.  It will then schedule some jobs (it can be any kind of job including build and test) to be run in various runtime environments as defined in the pipeline YAML configuration from the Core tools. A node is pushed to the API with "available" state e.g. "kunit" node. This will generate pub/sub event of build or test node creation.

### Runtime Environment

The jobs added by runner will be run in specified runtime environment i.e. shell, Kubernetes or LAVA lab.
Each environment needs to have its own API token set up locally to be able to submit the results to API. It updates the node with state "done" and result (pass, fail, or skip). This will generate pub/sub event of node update.

### Set Timeout

The set timeout service periodically checks all nodes' state. If a node is in "closing" state, then it checks whether the maximum wait time (timeout) is over. If so, it sets the node state of the node and all its child nodes to "done" and result to "incomplete". This will generate pub/sub event of node update.

### Set Completed

The set completed service typically listens to all closing or available nodes.
It checks whether the hold off time has been reached. If so, the parent node state will be set to "done" if all its child nodes are completed. If some of the child nodes are still in closing or available state, then the parent node state will be set to "closing".

### Test Report

The Test Report in its current state listens for completed tarball node. It then generates a test report with the child nodes' details of the parent node and sends the report over an email.

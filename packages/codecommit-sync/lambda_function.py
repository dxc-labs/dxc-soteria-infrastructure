#!/usr/bin/env python

import json
import os
import subprocess

import boto3

#############################################


def gen_response(status_code, body=None):
    if body:
        body = json.dumps(body)
    else:
        body = ""
    response = {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": body,
        "isBase64Encoded": False,
    }
    return response


#############################################


def lambda_handler(event, context):
    print(f"Received Event: {event}")

    body = event.get("body", None)
    if not isinstance(body, dict):
        try:
            body = json.loads(body)
        except AttributeError as err:
            response = f"bad input, expected dict -> {err}"
            return gen_response(400, response)
        except Exception as err:
            response = f"unknown error -> {err}"
            return gen_response(500, response)

    repository = body.get("repository", None)
    component = repository.get("name", None)
    owner = repository.get("owner", None)  # eg.'soteria'
    projectName = owner.get("name", None)  # eg.'tracing'

    # Dynamically build and writeout known_hosts
    with open("/tmp/known_hosts", "w+") as f:
        process = subprocess.run(
            ["bash", "-c", "ssh-keyscan -H github.dxc.com"],
            text=True,
            stdout=subprocess.PIPE,
        )
        f.write(process.stdout)

    # Extract Git SSH key from SSM and writeout to id_rsa
    # Important newline='\n'
    with open("/tmp/id_rsa", "w+", newline="\n") as f:
        ssm = boto3.client("ssm")
        parameter = ssm.get_parameter(
            Name=os.environ["ssh_key_name"], WithDecryption=True
        )
        f.write(parameter["Parameter"]["Value"])

    # https://git-scm.com/docs/git#Documentation/git.txt-codeGITSSHCOMMANDcode
    # Set environ var to tell git to use prebuild known_hosts and id_rsa
    os.environ[
        "GIT_SSH_COMMAND"
    ] = "ssh -o UserKnownHostsFile=/tmp/known_hosts -i /tmp/id_rsa"

    aws_region = os.environ["AWS_REGION"]
    origin = f"codecommit::{aws_region}://{projectName}-{component}"
    # ! I have tried using other alternatives for the sync
    # origin = f"ssh://git-codecommit.{aws_region}.amazonaws.com/v1/repos/{projectName}-{component}"
    # origin = f"https://git-codecommit.{aws_region}.amazonaws.com/v1/repos/{projectName}-{component}"
    repo_dir = f"/tmp/git-mirror/{component}"

    os.environ["HOME"] = "/tmp"
    commands = [
        # f"git config --global user.name 'Phillip Matheson'",
        # f"git config --global user.email 'pmatheson@dxc.com'",
        # f"git config --global credential.helper '!aws codecommit credential-helper $@'",
        # f"git config --global credential.UseHttpPath true",
        f"chmod 0600 /tmp/id_rsa",
        f"ls",
        f"git clone --mirror git@github.dxc.com:{projectName}/{component}.git {repo_dir}",
        f"ls {repo_dir}",
        f"git --git-dir {repo_dir} remote set-url --push origin {origin}",
        f"git --git-dir {repo_dir} fetch -p origin",
        f"git --git-dir {repo_dir} push --mirror",  #! Having problem with this command related to creds
        "rm -rf /tmp/*",
    ]

    for command in commands:
        print(f"Running command: {command}")
        subprocess.run(["bash", "-c", command], text=True)

    return gen_response(200, event)


# *#################################################

# Local testing -> Will remove after code review

if __name__ == "__main__":
    event = {
        "body": {"repository": {"name": "tracing", "owner": {"name": "soteria"},},},
    }
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ[
        "ssh_key_name"
    ] = "/soteria/pmatheson/sbx/git/ssh"  #!Remove after testing local

    lambda_handler(event, None)

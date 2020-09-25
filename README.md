# Soteria Infrastructure
Project Soteria has this common "infrastructure" component, with a single instance of it hosting "global" resources like domain names.

It is also home to the "devops" stack, which contains the external dependencies for continuous integration, delivery, and deployment (AWS CodeCommit, CodePipeline, CodeBuild, CodeDeploy). This is instantiated once for each component stack, including this infrastructure component. Think of it as the bootstrap for the rest of the component stacks.

![Animated GIF of Setup Process](https://github.dxc.com/soteria/infrastructure/blob/master/docs/images/soteria-setup.gif?raw=true)

## Utilities
These scripts assume you have checked out all the component repos into one project directory and are running them in-situ in the infrastructure component:

- `setup.sh` creates devops infrastructure (repos, buckets, etc) "outside" the component/s
- `mirror.sh` mirrors the component repo/s from GitHub Enterprise into CodeCommit
- `policy.sh` applies the stack policies for the specified component/s and environment/s

## FAQ

### Start here
- clone this (infrastructure) repo — it includes the devops infrastructure (/devops) and "globals" like domain names
- create an aws-cli profile for <project>-<tenant>-<environment> (e.g. soteria-dxc-dev) with access keys in ~/.aws/credentials

### How do I deploy a new tenant (e.g. dxc, sjohnston23)?
- Configure the TenantName in all.ini
- Run `setup.sh -e dev -a` to do [a]ll steps (deploy, set-stack-policy, enable-termination-protection) for all components.
- Repeat for other environments (e.g. stg, prd)
- Run `mirror.sh -e dev` to mirror repos into new environment, which will trigger the pipelines

### How do I deploy a new environment (e.g. dev)?
- add a CodePipeline/CloudFormation TemplateConfiguration (<env>.json) to /config in each component
- clone the most relevant devops CloudFormation template (devops/<env>.yaml) in infrastructure/component and adapt as required (i.e. add/remove approval steps)
- run ./setup.sh -e <env> (e.g. ./setup.sh -e sbx) to create the CloudFormation stack for each component in the new environment

### How do I add a component (e.g. tracing)?
- create source repo on e.g. GitHub Enterprise
- clone it to your machine (i.e. `git clone git@github.dxc.com:soteria/component.git`) and `cd` to it
- copy over files and folders from the skeleton component in [infrastructure/skeleton](https://github.dxc.com/soteria/infrastructure/tree/master/skeleton)
- add component name (e.g. mycomponent) to list in `devops/all.ini` in the infrastructure repo (send PR if required)
- run `setup.sh -a <component>` to deploy the devops infrastructure "outside" the component
- create a component CloudFormation stack at `<component>/cloudformation/index.yaml`
    - stack will be built in CodePipeline on git push to the `master` branch (dev) or `production` branch (stg/prd with approval).
- run `mirror.sh` to push the code into AWS CodeCommit which will trigger the pipeline/s for initial deployment
- open AWS console and observe CodePipeline doing the first build
    - note that you need to do a second push/trigger to populate the new `project-tenant-environment-component` because the stack hadn't created it on the first pass

### How do I change the domains?
- register new domain/s
- update the config files (config/dev.ini, config/stg.json, config.prd.json)
- get the nameserver information from the hosted zones (4 x FQDNs)
- delegate the registered domain/s to those nameservers
- push to `production` git branch to trigger the pipeline to deploy stg/prd

### What order should I deploy the components?
CloudFormation's usual dependency mechanisms only work within stacks, so it may be necessary to bring components up in a certain order. For example:
- infrastructure
- domains
- certificates
- distribution

[![CodeQL](https://github.com/aws-exporters/inspector/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/aws-exporters/inspector/actions/workflows/codeql-analysis.yml)
[![Test and Lint](https://github.com/aws-exporters/inspector/actions/workflows/test-and-lint.yaml/badge.svg)](https://github.com/aws-exporters/inspector/actions/workflows/test-and-lint.yaml)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/aws-exporters/inspector)
![GitHub](https://img.shields.io/github/license/aws-exporters/inspector)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)

# inspector
A Prometheus exporter for AWS Inspector

Current Status:
- [x] AWS_ECR_CONTAINER
- [ ] AMI
- [ ] AWS_EC2_INSTANCE
  - [ ] PACKAGE_VULNERABILITY
  - [ ] NETWORK_REACHABILITY

## Motivation
Inspector has a lot of useful information: scan results, EC2 instance
vulnerabilities, networking issues and AMI scan results. 

Information that might be useful to display on team based dashboards alongside
Kubernetes workload availability and Istio traffic metrics.

## Technical Design
This exporter makes use of `boto3` to query Inspector2 for finding aggregations.

To be kind to the AWS APIs, results are cached and refreshed in the background every
30 minutes (by default).

### Configuration
Configuration with environment variables:

| Variable | Description | Default | Example |
| -------- | ----------- | ------- | ------- |
| `APP_PORT` | The port to expose the exporter on | `9000` | `8080` |
| `APP_HOST` | The host to bind the application to | `0.0.0.0` | `localhost` |
| `CACHE_REFRESH_INTERVAL` | How many seconds to wait before refreshing caches in the background | `1800` | `3600` |
| `AWS_ACCOUNT_ID` | The ID of the AWS account to export metrics for | `current AWS account` | `112233445566` |
| `LOG_LEVEL` | How much or little logging do you want | `INFO` | `DEBUG` |

### Exported Metrics
The metrics currently exported are:

#### `aws_inspector_container_image_severity_count`
- **Type:** Gauge
- **Description:** Scan result counts per image/tag/by severity. The labels are
  almost identical to those exposed by the ECR exporter making moving from one to
  the other as simple as possible.
- **Example:**
```
# HELP aws_inspector_container_image_severity_count ECR image scan summary results
# TYPE aws_inspector_container_image_severity_count gauge
....
aws_inspector_container_image_severity_count{digest="sha256:0eb66119edb5484e846acb68ce60b02fb69aed204fd3dedb5277f8add881fcdb",image="112233445566.dkr.ecr.eu-west-1.amazonaws.com/robopig:e34c1c8f",name="robopig",registry_id="112233445566",severity="CRITICAL",tag="e34c1c8f"} 0.0
aws_inspector_container_image_severity_count{digest="sha256:0eb66119edb5484e846acb68ce60b02fb69aed204fd3dedb5277f8add881fcdb",image="112233445566.dkr.ecr.eu-west-1.amazonaws.com/robopig:e34c1c8f",name="robopig",registry_id="112233445566",severity="HIGH",tag="e34c1c8f"} 4.0
aws_inspector_container_image_severity_count{digest="sha256:0eb66119edb5484e846acb68ce60b02fb69aed204fd3dedb5277f8add881fcdb",image="112233445566.dkr.ecr.eu-west-1.amazonaws.com/robopig:e34c1c8f",name="robopig",registry_id="112233445566",severity="MEDIUM",tag="e34c1c8f"} 3.0
aws_inspector_container_image_severity_count{digest="sha256:0eb66119edb5484e846acb68ce60b02fb69aed204fd3dedb5277f8add881fcdb",image="112233445566.dkr.ecr.eu-west-1.amazonaws.com/robopig:e34c1c8f",name="robopig",registry_id="112233445566",severity="LOW",tag="e34c1c8f"} 3.0
aws_inspector_container_image_severity_count{digest="sha256:81de8eb8dfcb38c28d6ca0a8e4c9ad27bedc72e523f96d93c7cc365e62be5147",image="112233445566.dkr.ecr.eu-west-1.amazonaws.com/monkeytail:2b4692ee",name="monkeytail",registry_id="112233445566",severity="CRITICAL",tag="2b4692ee"} 3.0
aws_inspector_container_image_severity_count{digest="sha256:81de8eb8dfcb38c28d6ca0a8e4c9ad27bedc72e523f96d93c7cc365e62be5147",image="112233445566.dkr.ecr.eu-west-1.amazonaws.com/monkeytail:2b4692ee",name="monkeytail",registry_id="112233445566",severity="HIGH",tag="2b4692ee"} 6.0
aws_inspector_container_image_severity_count{digest="sha256:81de8eb8dfcb38c28d6ca0a8e4c9ad27bedc72e523f96d93c7cc365e62be5147",image="112233445566.dkr.ecr.eu-west-1.amazonaws.com/monkeytail:2b4692ee",name="monkeytail",registry_id="112233445566",severity="MEDIUM",tag="2b4692ee"} 15.0
aws_inspector_container_image_severity_count{digest="sha256:81de8eb8dfcb38c28d6ca0a8e4c9ad27bedc72e523f96d93c7cc365e62be5147",image="112233445566.dkr.ecr.eu-west-1.amazonaws.com/monkeytail:2b4692ee",name="monkeytail",registry_id="112233445566",severity="LOW",tag="2b4692ee"} 4.0
....
```

## Required IAM Permissions
Currently, the required IAM permissions are: 
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "inspector2:ListFindingAggregations",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```
You can omit the `sts:GetCallerIdentity` permission if you supply your account ID with the `AWS_ACCOUNT_ID` environment variable.

import boto3
import botocore
import logging
import json

from prometheus_client.core import InfoMetricFamily, GaugeMetricFamily
from cachetools import TTLCache
from datetime import timezone


def _inspector_client():
    boto_config = botocore.client.Config(
        connect_timeout=2, read_timeout=10, retries={"max_attempts": 2}
    )
    session = boto3.session.Session()
    return session.client("inspector2", config=boto_config)


class InspectorMetricsCollector:
    def __init__(self, account_id):
        self.logger = logging.getLogger()
        self.account_id = account_id or boto3.client("sts").get_caller_identity().get(
            "Account"
        )
        self.imagecache = TTLCache(10000, 86400)

    def collect(self):

        image_common_label_keys = ["name", "tag", "digest", "registry_id", "image"]

        container_image_findings = GaugeMetricFamily(
            "aws_inspector_container_image_severity_count",
            "ECR image scan summary results",
            labels=image_common_label_keys + ["severity"],
        )

        for repo in self.imagecache:
            images = self.imagecache.get(repo, [])

            for image in images:
                tags = image.get("imageTags")
                severity_counts = image["severityCounts"]
                if tags:
                    for tag in tags:
                        image_common_label_values = [
                            image["repositoryName"],
                            tag,
                            image["imageDigest"],
                            image["accountId"],
                            f'{image["repositoryUri"]}:{tag}',
                        ]
                        for severity in severity_counts:
                            container_image_findings.add_metric(
                                image_common_label_values + [severity],
                                int(severity_counts[severity]),
                            )

        return [
            container_image_findings,
        ]

    def refresh_image_cache(self):
        inspector_client = _inspector_client()
        self.logger.info("refreshing image cache")

        paginator = inspector_client.get_paginator("list_finding_aggregations")

        image_findings = paginator.paginate(
            accountIds=[
                {
                    "comparison": "EQUALS",
                    "value": self.account_id,
                }
            ],
            aggregationRequest={
                'awsEcrContainerAggregation': {
                    'sortBy': 'ALL',
                    'sortOrder': 'DESC'
                }
            },
            aggregationType="AWS_ECR_CONTAINER",
            PaginationConfig={"pageSize": 1000},
        ).build_full_result()
        
        for image_finding in image_findings["responses"]:
            repositoryName = image_finding["awsEcrContainerAggregation"]["repository"]

            image_to_cache = {
                "repositoryName": repositoryName,
                "accountId": image_finding["awsEcrContainerAggregation"]["accountId"],
                "imageTags": image_finding["awsEcrContainerAggregation"]["imageTags"],
                "imageDigest": image_finding["awsEcrContainerAggregation"]["imageSha"],
                "repositoryUri": self.get_repo_uri(
                    image_finding["awsEcrContainerAggregation"]["resourceId"],
                    repositoryName,
                ),
                "severityCounts": self.format_severity_counts(
                    image_finding["awsEcrContainerAggregation"]["severityCounts"]
                ),
            }

            if self.imagecache.get(repositoryName, None) is None:
                self.imagecache[repositoryName] = [image_to_cache.copy()]
            else:
                self.imagecache[repositoryName].append(image_to_cache.copy())

    def refresh_caches(self):
        self.refresh_image_cache()
        self.logger.info("cache refresh complete")

    @staticmethod
    def get_repo_uri(resource_id, repo_name):
        id_parts = resource_id.split(":")
        account_id = id_parts[4]
        region = id_parts[3]
        return f"{account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}"

    @staticmethod
    def format_severity_counts(severity_counts):
        return {
            "CRITICAL": severity_counts["critical"],
            "HIGH": severity_counts["high"],
            "MEDIUM": severity_counts["medium"],
            "LOW": severity_counts["all"]
            - severity_counts["critical"]
            - severity_counts["high"]
            - severity_counts["medium"],
        }

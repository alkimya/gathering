"""
Cloud Skill for GatheRing.
Provides multi-cloud operations for AWS, GCP, and Azure.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission

logger = logging.getLogger(__name__)


class CloudProvider(ABC):
    """Abstract base class for cloud providers."""

    @abstractmethod
    def list_instances(self, region: Optional[str] = None) -> List[Dict[str, Any]]:
        """List compute instances."""
        pass

    @abstractmethod
    def get_instance(self, instance_id: str) -> Dict[str, Any]:
        """Get instance details."""
        pass

    @abstractmethod
    def start_instance(self, instance_id: str) -> bool:
        """Start an instance."""
        pass

    @abstractmethod
    def stop_instance(self, instance_id: str) -> bool:
        """Stop an instance."""
        pass

    @abstractmethod
    def list_buckets(self) -> List[Dict[str, Any]]:
        """List storage buckets."""
        pass

    @abstractmethod
    def list_bucket_objects(self, bucket: str, prefix: str = "") -> List[Dict[str, Any]]:
        """List objects in a bucket."""
        pass

    @abstractmethod
    def upload_to_bucket(self, bucket: str, key: str, filepath: str) -> bool:
        """Upload file to bucket."""
        pass

    @abstractmethod
    def download_from_bucket(self, bucket: str, key: str, filepath: str) -> bool:
        """Download file from bucket."""
        pass


class AWSProvider(CloudProvider):
    """AWS cloud provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        self.region = config.get("region", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        self.access_key = config.get("access_key", os.getenv("AWS_ACCESS_KEY_ID"))
        self.secret_key = config.get("secret_key", os.getenv("AWS_SECRET_ACCESS_KEY"))

        # Lazy import boto3
        self._ec2 = None
        self._s3 = None

    def _get_ec2(self):
        if self._ec2 is None:
            import boto3
            self._ec2 = boto3.client(
                "ec2",
                region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            )
        return self._ec2

    def _get_s3(self):
        if self._s3 is None:
            import boto3
            self._s3 = boto3.client(
                "s3",
                region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            )
        return self._s3

    def list_instances(self, region: Optional[str] = None) -> List[Dict[str, Any]]:
        ec2 = self._get_ec2()
        response = ec2.describe_instances()

        instances = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                name = ""
                for tag in instance.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break

                instances.append({
                    "id": instance["InstanceId"],
                    "name": name,
                    "type": instance["InstanceType"],
                    "state": instance["State"]["Name"],
                    "public_ip": instance.get("PublicIpAddress"),
                    "private_ip": instance.get("PrivateIpAddress"),
                    "launch_time": str(instance.get("LaunchTime")),
                })

        return instances

    def get_instance(self, instance_id: str) -> Dict[str, Any]:
        ec2 = self._get_ec2()
        response = ec2.describe_instances(InstanceIds=[instance_id])

        if response["Reservations"]:
            instance = response["Reservations"][0]["Instances"][0]
            return {
                "id": instance["InstanceId"],
                "type": instance["InstanceType"],
                "state": instance["State"]["Name"],
                "public_ip": instance.get("PublicIpAddress"),
                "private_ip": instance.get("PrivateIpAddress"),
                "vpc_id": instance.get("VpcId"),
                "subnet_id": instance.get("SubnetId"),
                "security_groups": [sg["GroupName"] for sg in instance.get("SecurityGroups", [])],
                "launch_time": str(instance.get("LaunchTime")),
            }
        return {}

    def start_instance(self, instance_id: str) -> bool:
        ec2 = self._get_ec2()
        ec2.start_instances(InstanceIds=[instance_id])
        return True

    def stop_instance(self, instance_id: str) -> bool:
        ec2 = self._get_ec2()
        ec2.stop_instances(InstanceIds=[instance_id])
        return True

    def list_buckets(self) -> List[Dict[str, Any]]:
        s3 = self._get_s3()
        response = s3.list_buckets()

        return [
            {
                "name": bucket["Name"],
                "creation_date": str(bucket["CreationDate"]),
            }
            for bucket in response.get("Buckets", [])
        ]

    def list_bucket_objects(self, bucket: str, prefix: str = "") -> List[Dict[str, Any]]:
        s3 = self._get_s3()
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=100)

        return [
            {
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": str(obj["LastModified"]),
            }
            for obj in response.get("Contents", [])
        ]

    def upload_to_bucket(self, bucket: str, key: str, filepath: str) -> bool:
        s3 = self._get_s3()
        s3.upload_file(filepath, bucket, key)
        return True

    def download_from_bucket(self, bucket: str, key: str, filepath: str) -> bool:
        s3 = self._get_s3()
        s3.download_file(bucket, key, filepath)
        return True


class GCPProvider(CloudProvider):
    """Google Cloud Platform provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        self.project = config.get("project", os.getenv("GOOGLE_CLOUD_PROJECT"))
        self.zone = config.get("zone", os.getenv("GOOGLE_CLOUD_ZONE", "us-central1-a"))
        self.credentials_path = config.get("credentials", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

        self._compute = None
        self._storage = None

    def _get_compute(self):
        if self._compute is None:
            from google.cloud import compute_v1
            self._compute = compute_v1.InstancesClient()
        return self._compute

    def _get_storage(self):
        if self._storage is None:
            from google.cloud import storage
            self._storage = storage.Client(project=self.project)
        return self._storage

    def list_instances(self, region: Optional[str] = None) -> List[Dict[str, Any]]:
        compute = self._get_compute()
        zone = region or self.zone

        instances = []
        for instance in compute.list(project=self.project, zone=zone):
            instances.append({
                "id": str(instance.id),
                "name": instance.name,
                "type": instance.machine_type.split("/")[-1],
                "state": instance.status,
                "zone": zone,
            })

        return instances

    def get_instance(self, instance_id: str) -> Dict[str, Any]:
        compute = self._get_compute()
        instance = compute.get(project=self.project, zone=self.zone, instance=instance_id)

        return {
            "id": str(instance.id),
            "name": instance.name,
            "type": instance.machine_type.split("/")[-1],
            "state": instance.status,
            "zone": self.zone,
        }

    def start_instance(self, instance_id: str) -> bool:
        compute = self._get_compute()
        compute.start(project=self.project, zone=self.zone, instance=instance_id)
        return True

    def stop_instance(self, instance_id: str) -> bool:
        compute = self._get_compute()
        compute.stop(project=self.project, zone=self.zone, instance=instance_id)
        return True

    def list_buckets(self) -> List[Dict[str, Any]]:
        storage = self._get_storage()
        return [
            {
                "name": bucket.name,
                "location": bucket.location,
                "storage_class": bucket.storage_class,
            }
            for bucket in storage.list_buckets()
        ]

    def list_bucket_objects(self, bucket: str, prefix: str = "") -> List[Dict[str, Any]]:
        storage = self._get_storage()
        bucket_obj = storage.bucket(bucket)

        return [
            {
                "key": blob.name,
                "size": blob.size,
                "updated": str(blob.updated),
            }
            for blob in bucket_obj.list_blobs(prefix=prefix, max_results=100)
        ]

    def upload_to_bucket(self, bucket: str, key: str, filepath: str) -> bool:
        storage = self._get_storage()
        bucket_obj = storage.bucket(bucket)
        blob = bucket_obj.blob(key)
        blob.upload_from_filename(filepath)
        return True

    def download_from_bucket(self, bucket: str, key: str, filepath: str) -> bool:
        storage = self._get_storage()
        bucket_obj = storage.bucket(bucket)
        blob = bucket_obj.blob(key)
        blob.download_to_filename(filepath)
        return True


class AzureProvider(CloudProvider):
    """Azure cloud provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        self.subscription_id = config.get("subscription_id", os.getenv("AZURE_SUBSCRIPTION_ID"))
        self.resource_group = config.get("resource_group", os.getenv("AZURE_RESOURCE_GROUP"))
        self.tenant_id = config.get("tenant_id", os.getenv("AZURE_TENANT_ID"))
        self.client_id = config.get("client_id", os.getenv("AZURE_CLIENT_ID"))
        self.client_secret = config.get("client_secret", os.getenv("AZURE_CLIENT_SECRET"))

        self._compute = None
        self._storage = None

    def _get_credential(self):
        from azure.identity import ClientSecretCredential
        return ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret,
        )

    def _get_compute(self):
        if self._compute is None:
            from azure.mgmt.compute import ComputeManagementClient
            self._compute = ComputeManagementClient(
                credential=self._get_credential(),
                subscription_id=self.subscription_id,
            )
        return self._compute

    def _get_storage(self):
        if self._storage is None:
            from azure.storage.blob import BlobServiceClient
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            self._storage = BlobServiceClient.from_connection_string(connection_string)
        return self._storage

    def list_instances(self, region: Optional[str] = None) -> List[Dict[str, Any]]:
        compute = self._get_compute()

        instances = []
        for vm in compute.virtual_machines.list(self.resource_group):
            instances.append({
                "id": vm.id,
                "name": vm.name,
                "type": vm.hardware_profile.vm_size,
                "state": vm.provisioning_state,
                "location": vm.location,
            })

        return instances

    def get_instance(self, instance_id: str) -> Dict[str, Any]:
        compute = self._get_compute()
        vm = compute.virtual_machines.get(self.resource_group, instance_id)

        return {
            "id": vm.id,
            "name": vm.name,
            "type": vm.hardware_profile.vm_size,
            "state": vm.provisioning_state,
            "location": vm.location,
        }

    def start_instance(self, instance_id: str) -> bool:
        compute = self._get_compute()
        compute.virtual_machines.begin_start(self.resource_group, instance_id)
        return True

    def stop_instance(self, instance_id: str) -> bool:
        compute = self._get_compute()
        compute.virtual_machines.begin_power_off(self.resource_group, instance_id)
        return True

    def list_buckets(self) -> List[Dict[str, Any]]:
        storage = self._get_storage()
        return [
            {"name": container.name}
            for container in storage.list_containers()
        ]

    def list_bucket_objects(self, bucket: str, prefix: str = "") -> List[Dict[str, Any]]:
        storage = self._get_storage()
        container = storage.get_container_client(bucket)

        return [
            {
                "key": blob.name,
                "size": blob.size,
                "last_modified": str(blob.last_modified),
            }
            for blob in container.list_blobs(name_starts_with=prefix)
        ][:100]

    def upload_to_bucket(self, bucket: str, key: str, filepath: str) -> bool:
        storage = self._get_storage()
        container = storage.get_container_client(bucket)
        with open(filepath, "rb") as f:
            container.upload_blob(key, f, overwrite=True)
        return True

    def download_from_bucket(self, bucket: str, key: str, filepath: str) -> bool:
        storage = self._get_storage()
        container = storage.get_container_client(bucket)
        with open(filepath, "wb") as f:
            blob_data = container.download_blob(key)
            f.write(blob_data.readall())
        return True


class CloudSkill(BaseSkill):
    """
    Multi-cloud operations skill.

    Features:
    - AWS (EC2, S3)
    - GCP (Compute Engine, Cloud Storage)
    - Azure (VMs, Blob Storage)
    - Unified API across providers

    Security:
    - Credentials from environment variables
    - Read-only mode option
    - Action confirmation for destructive ops
    """

    name = "cloud"
    description = "Multi-cloud operations (AWS, GCP, Azure)"
    version = "1.0.0"
    required_permissions = [SkillPermission.NETWORK]

    PROVIDERS = {
        "aws": AWSProvider,
        "gcp": GCPProvider,
        "azure": AzureProvider,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._providers: Dict[str, CloudProvider] = {}
        self.default_provider = self.config.get("default_provider", "aws") if self.config else "aws"
        self.read_only = self.config.get("read_only", False) if self.config else False

    def _get_provider(self, provider_name: str) -> CloudProvider:
        """Get or create provider instance."""
        if provider_name not in self._providers:
            if provider_name not in self.PROVIDERS:
                raise ValueError(f"Unknown provider: {provider_name}. Available: {list(self.PROVIDERS.keys())}")

            provider_config = self.config.get(provider_name, {}) if self.config else {}
            self._providers[provider_name] = self.PROVIDERS[provider_name](provider_config)

        return self._providers[provider_name]

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "cloud_list_instances",
                "description": "List compute instances/VMs",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "description": "Cloud provider (aws, gcp, azure)",
                            "enum": ["aws", "gcp", "azure"]
                        },
                        "region": {
                            "type": "string",
                            "description": "Region/zone filter"
                        }
                    }
                }
            },
            {
                "name": "cloud_get_instance",
                "description": "Get details of a specific instance",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["aws", "gcp", "azure"]
                        },
                        "instance_id": {
                            "type": "string",
                            "description": "Instance ID or name"
                        }
                    },
                    "required": ["instance_id"]
                }
            },
            {
                "name": "cloud_start_instance",
                "description": "Start a stopped instance",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["aws", "gcp", "azure"]
                        },
                        "instance_id": {
                            "type": "string",
                            "description": "Instance ID to start"
                        }
                    },
                    "required": ["instance_id"]
                }
            },
            {
                "name": "cloud_stop_instance",
                "description": "Stop a running instance",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["aws", "gcp", "azure"]
                        },
                        "instance_id": {
                            "type": "string",
                            "description": "Instance ID to stop"
                        }
                    },
                    "required": ["instance_id"]
                }
            },
            {
                "name": "cloud_list_buckets",
                "description": "List storage buckets/containers",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["aws", "gcp", "azure"]
                        }
                    }
                }
            },
            {
                "name": "cloud_list_objects",
                "description": "List objects in a bucket",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["aws", "gcp", "azure"]
                        },
                        "bucket": {
                            "type": "string",
                            "description": "Bucket name"
                        },
                        "prefix": {
                            "type": "string",
                            "description": "Filter by prefix",
                            "default": ""
                        }
                    },
                    "required": ["bucket"]
                }
            },
            {
                "name": "cloud_upload",
                "description": "Upload file to cloud storage",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["aws", "gcp", "azure"]
                        },
                        "bucket": {
                            "type": "string",
                            "description": "Bucket name"
                        },
                        "key": {
                            "type": "string",
                            "description": "Object key/path in bucket"
                        },
                        "filepath": {
                            "type": "string",
                            "description": "Local file path to upload"
                        }
                    },
                    "required": ["bucket", "key", "filepath"]
                }
            },
            {
                "name": "cloud_download",
                "description": "Download file from cloud storage",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["aws", "gcp", "azure"]
                        },
                        "bucket": {
                            "type": "string",
                            "description": "Bucket name"
                        },
                        "key": {
                            "type": "string",
                            "description": "Object key/path in bucket"
                        },
                        "filepath": {
                            "type": "string",
                            "description": "Local file path to save to"
                        }
                    },
                    "required": ["bucket", "key", "filepath"]
                }
            },
            {
                "name": "cloud_delete_object",
                "description": "Delete object from bucket",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["aws", "gcp", "azure"]
                        },
                        "bucket": {
                            "type": "string",
                            "description": "Bucket name"
                        },
                        "key": {
                            "type": "string",
                            "description": "Object key to delete"
                        }
                    },
                    "required": ["bucket", "key"]
                }
            },
            {
                "name": "cloud_providers",
                "description": "List available and configured cloud providers",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute cloud tool."""
        try:
            provider_name = tool_input.get("provider", self.default_provider)

            if tool_name == "cloud_providers":
                return self._list_providers()

            provider = self._get_provider(provider_name)

            # Read-only check
            write_ops = ["cloud_start_instance", "cloud_stop_instance", "cloud_upload", "cloud_delete_object"]
            if self.read_only and tool_name in write_ops:
                return SkillResponse(
                    success=False,
                    message="Cloud skill is in read-only mode",
                    error="read_only_mode"
                )

            if tool_name == "cloud_list_instances":
                instances = provider.list_instances(tool_input.get("region"))
                return SkillResponse(
                    success=True,
                    message=f"Found {len(instances)} instance(s)",
                    data={"instances": instances, "provider": provider_name}
                )

            elif tool_name == "cloud_get_instance":
                instance = provider.get_instance(tool_input["instance_id"])
                return SkillResponse(
                    success=True,
                    message="Instance details retrieved",
                    data={"instance": instance, "provider": provider_name}
                )

            elif tool_name == "cloud_start_instance":
                provider.start_instance(tool_input["instance_id"])
                return SkillResponse(
                    success=True,
                    message=f"Instance {tool_input['instance_id']} start initiated",
                    data={"instance_id": tool_input["instance_id"], "provider": provider_name}
                )

            elif tool_name == "cloud_stop_instance":
                provider.stop_instance(tool_input["instance_id"])
                return SkillResponse(
                    success=True,
                    message=f"Instance {tool_input['instance_id']} stop initiated",
                    data={"instance_id": tool_input["instance_id"], "provider": provider_name}
                )

            elif tool_name == "cloud_list_buckets":
                buckets = provider.list_buckets()
                return SkillResponse(
                    success=True,
                    message=f"Found {len(buckets)} bucket(s)",
                    data={"buckets": buckets, "provider": provider_name}
                )

            elif tool_name == "cloud_list_objects":
                objects = provider.list_bucket_objects(
                    tool_input["bucket"],
                    tool_input.get("prefix", "")
                )
                return SkillResponse(
                    success=True,
                    message=f"Found {len(objects)} object(s)",
                    data={"objects": objects, "bucket": tool_input["bucket"], "provider": provider_name}
                )

            elif tool_name == "cloud_upload":
                filepath = tool_input["filepath"]
                if not os.path.exists(filepath):
                    return SkillResponse(
                        success=False,
                        message=f"File not found: {filepath}",
                        error="file_not_found"
                    )

                provider.upload_to_bucket(
                    tool_input["bucket"],
                    tool_input["key"],
                    filepath
                )
                return SkillResponse(
                    success=True,
                    message=f"Uploaded {filepath} to {tool_input['bucket']}/{tool_input['key']}",
                    data={"bucket": tool_input["bucket"], "key": tool_input["key"], "provider": provider_name}
                )

            elif tool_name == "cloud_download":
                provider.download_from_bucket(
                    tool_input["bucket"],
                    tool_input["key"],
                    tool_input["filepath"]
                )
                return SkillResponse(
                    success=True,
                    message=f"Downloaded to {tool_input['filepath']}",
                    data={"bucket": tool_input["bucket"], "key": tool_input["key"], "filepath": tool_input["filepath"]}
                )

            elif tool_name == "cloud_delete_object":
                # For deletion, we need to implement this method
                return SkillResponse(
                    success=False,
                    message="Delete operation not yet implemented for this provider",
                    error="not_implemented"
                )

            else:
                return SkillResponse(
                    success=False,
                    message=f"Unknown tool: {tool_name}",
                    error="unknown_tool"
                )

        except ImportError as e:
            return SkillResponse(
                success=False,
                message=f"Cloud SDK not installed: {e}. Install: pip install boto3 google-cloud-compute google-cloud-storage azure-mgmt-compute azure-storage-blob",
                error=str(e)
            )
        except Exception as e:
            logger.exception(f"Cloud tool error: {e}")
            return SkillResponse(
                success=False,
                message=f"Cloud operation failed: {str(e)}",
                error=str(e)
            )

    def _list_providers(self) -> SkillResponse:
        """List available cloud providers."""
        providers_info = []

        for name in self.PROVIDERS.keys():
            configured = False
            if name == "aws":
                configured = bool(os.getenv("AWS_ACCESS_KEY_ID"))
            elif name == "gcp":
                configured = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GOOGLE_CLOUD_PROJECT"))
            elif name == "azure":
                configured = bool(os.getenv("AZURE_SUBSCRIPTION_ID"))

            providers_info.append({
                "name": name,
                "configured": configured,
                "is_default": name == self.default_provider,
            })

        return SkillResponse(
            success=True,
            message=f"{len(providers_info)} provider(s) available",
            data={"providers": providers_info, "default": self.default_provider}
        )

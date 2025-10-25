import boto3
from botocore.exceptions import ClientError
import logging

log = logging.getLogger("create_ec2")

def validate_ec2_credentials(region, aws_access_key_id, aws_secret_access_key):
    """
    Validates AWS EC2 credentials by attempting a harmless API call
    (DescribeRegions) to ensure the credentials are valid and authorized.
    
    Raises:
        ValueError: If the credentials are invalid or unauthorized.
    """
    try:
        ec2 = boto3.client(
            "ec2",
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        
        # Simple, non-destructive API call
        ec2.describe_regions()
        log.info(f"✅ AWS EC2 credentials valid for region: {region}")
        return ec2

    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ["AuthFailure", "UnrecognizedClientException"]:
            raise ValueError("❌ Invalid or unauthorized AWS credentials.")
        elif code == "UnauthorizedOperation":
            raise ValueError("❌ AWS credentials are valid but lack EC2 permissions.")
        else:
            raise ValueError(f"❌ AWS EC2 validation failed: {e}")
    except Exception as e:
        raise ValueError(f"❌ Unexpected error during EC2 credential validation: {e}")


def get_latest_ubuntu_ami(region, 
                          release="jammy", 
                          arch="amd64", 
                          aws_access_key_id=None, 
                          aws_secret_access_key=None
):
    
    ec2 = boto3.client("ec2",
                        region_name=region,
                        aws_access_key_id = aws_access_key_id,
                        aws_secret_access_key = aws_secret_access_key
    )
    filters = [
        {"Name": "name", "Values": [f"ubuntu/images/hvm-ssd/ubuntu-{release}*-{arch}-server-*"]},
        {"Name": "root-device-type", "Values": ["ebs"]},
        {"Name": "virtualization-type", "Values": ["hvm"]},
    ]
    images = ec2.describe_images(Owners=["099720109477"], Filters=filters)["Images"]
    if not images:
        raise ValueError(f"No Ubuntu images found for region {region} and release {release}")
    latest = sorted(images, key=lambda x: x["CreationDate"], reverse=True)[0]
    return latest["ImageId"] #, latest["Name"]


def create_ec2_instance(region, 
                        instance_type, 
                        docker_image, 
                        key_name='default', 
                        security_group='default', 
                        user_data=None, 
                        aws_access_key_id=None, 
                        aws_secret_access_key=None
):
    
    """
    Creates an EC2 instance in the specified AWS region with given parameters.
    
    Parameters:
    - region (str): AWS region (e.g., "us-east-1")
    - instance_type (str): EC2 instance type (e.g., "t2.micro")
    - docker_image (str): Docker image to run on instance (e.g., "nginx:latest")
    - key_name (str, optional): SSH key name for instance access
    - security_group (str, optional): Security group name (default is 'default')
    - user_data (str, optional): Bash commands to execute during instance setup
    
    Returns:
    - str: EC2 instance ID
    """
    # Initialize EC2 client
    ec2 = validate_ec2_credentials(region=region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

    # ec2 = boto3.client(
    #     'ec2', 
    #     region_name=region,
    #     aws_access_key_id = aws_access_key_id,
    #     aws_secret_access_key = aws_secret_access_key,
    # )

    # Get default security group
    sg = ec2.describe_security_groups(GroupNames=['default'])['SecurityGroups'][0]
    sg_id = sg['GroupId']
    print("sg_id", sg_id)

    # Ensure SSH inbound is allowed
    try:
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[{
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }]
        )
    except ClientError as e:
        if "InvalidPermission.Duplicate" in str(e):
            pass  # SSH already allowed
        else:
            raise

    # Build user data script if provided
    if user_data:
        user_data_script = user_data
    else:
        user_data_script = f"""#!/bin/bash
    sudo apt update -y
    sudo apt install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo docker pull {docker_image}
    sudo docker run -d -p 80:80 {docker_image}
    """
    
    try:
        # Create EC2 instance
        ami_id = get_latest_ubuntu_ami(region, aws_access_key_id=aws_access_key_id,
                                    aws_secret_access_key=aws_secret_access_key)
        
        response = ec2.run_instances(
            ImageId=ami_id,
            MinCount=1,
            MaxCount=1,
            InstanceType=instance_type,
            KeyName=key_name,
            SecurityGroupIds=[sg_id],
            UserData=user_data_script
        )
        # Return the instance ID
        instance_id = response['Instances'][0]['InstanceId']
        log.info(f"Created EC2 instance with ID: {instance_id}")
        return instance_id

    except Exception as e:
        raise Exception(f"Error: {e}")

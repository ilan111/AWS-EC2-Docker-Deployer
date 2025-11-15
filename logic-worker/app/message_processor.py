import logging
from shared.db import SessionLocal
from shared.models import RequestStatus
from .ai_service import AIService
from .create_ec2 import create_ec2_instance
import json

log = logging.getLogger("message_processor")

class MessageProcessor:
    def __init__(self):
        self.ai_service = AIService()

    def process_request(self, text: str) -> str:
        log.info(f"Processing request: {text}")
        return self.ai_service.generate_response(text)
    
    def process_ec2_deployment(self, message_data: dict):
        """
        Handles EC2 deployment messages.
        Expected message format:
            {
                "request_id": "<uuid>",
                "region": "us-east-1",
                "instance_type": "t3.micro",
                "docker_image": "nginx:latest",
                "key_name": "my-key",
                "security_group": "my-sg",
                "aws_access_key": "<AWS_ACCESS_KEY>",
                "aws_secret_key": "<AWS_SECRET_KEY>"
            }
        """
        request_id = message_data.get("request_id")
        log.info(f"Processing EC2 deployment for request {request_id}")

        # Update DB
        with SessionLocal() as db:
            db_request = db.query(RequestStatus).filter(RequestStatus.id == request_id).first()
            if not db_request:
                log.warning(f"Request {request_id} not found in DB")
                return

            # Update status to "in_progress"
            db_request.status = "in_progress"
            db.commit()
            db.refresh(db_request)  

            try:
                region = message_data["region"]
                instance_type = message_data["instance_type"]
                docker_image = message_data["docker_image"]
                key_name = message_data.get("key_name")
                security_group = message_data.get("security_group", "default")
                aws_access_key = message_data["aws_access_key"]
                aws_secret_key = message_data["aws_secret_key"]
                
                instance_details_json = create_ec2_instance(
                    region=region, 
                    instance_type=instance_type, 
                    docker_image=docker_image, 
                    key_name=key_name, 
                    security_group=security_group,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key
                )

                # Update DB on success
                db_request.status = "deployed"
                result_json = json.dumps({
                    "public_ip": instance_details_json["public_ip"], 
                    "console_link": instance_details_json["console_link"]
                })
                db_request.result = result_json
                db.commit()
                db.refresh(db_request)  
                
                log.info(f"EC2 deployment complete for request {request_id}")
                log.info(f"Result stored: {result_json}")  

            except Exception as e:
                log.error(f"EC2 deployment failed for {request_id}: {e}")
                db_request.status = "failed"
                error_json = json.dumps({"error": str(e)})
                db_request.result = error_json
                db.commit()
                db.refresh(db_request)  

    def handle_message(self, topic, message_data: dict):
        try:
            if topic == "user_requests":
                    request_id = message_data["request_id"]
                    text = message_data["text"]

                    log.info(f"Received request {request_id}: {text}")

                    result = self.process_request(text)

                    with SessionLocal() as db:
                        db_request = db.query(RequestStatus).filter(RequestStatus.id == request_id).first()
                        if db_request:
                            db_request.status = "done"
                            db_request.result = result
                            db.commit()
                            log.info(f"Completed request {request_id}")
                        else:
                            log.warning(f"Request {request_id} not found in database")

            elif topic == "ec2_deployments":
                    self.process_ec2_deployment(message_data)

            else:
                log.warning(f"Unknown topic: {topic}")

        except Exception as e:
            log.error(f"Error handling message: {e}")
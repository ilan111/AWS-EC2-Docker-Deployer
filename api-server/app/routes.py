import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from shared.db import SessionLocal
from shared.models import RequestStatus
from .kafka_producer import send_message

import json
from fastapi import Body

log = logging.getLogger("api")
router = APIRouter()

class UserRequest(BaseModel):
    text: str

class RequestResponse(BaseModel):
    request_id: int

class ResultResponse(BaseModel):
    status: str
    result: str = None

@router.post("/request", response_model=RequestResponse)
def send_user_request(request: UserRequest):
    with SessionLocal() as db:

        db_request = RequestStatus(status="in_progress")
        db.add(db_request)
        db.commit()
        db.refresh(db_request)

        send_message("user_requests", {
            "request_id": db_request.id,
            "text": request.text
        })

        return RequestResponse(request_id=db_request.id)

@router.get("/result/{request_id}", response_model=ResultResponse)
def get_request_result(request_id: int):
    try:
        with SessionLocal() as db:
            db.expire_all()
            db_request = db.query(RequestStatus).filter(RequestStatus.id == request_id).first()

            if not db_request:
                return JSONResponse(status_code=404, content={"error": "Request not found"})
            
            # Refresh to get latest data
            db.refresh(db_request)

            if db_request.status == "failed":
                try:
                    result_data = json.loads(db_request.result) if db_request.result else {}
                except Exception:
                    result_data = {"error": db_request.result or "Unknown error"}
                return ResultResponse(status="failed", result=json.dumps(result_data))

            elif db_request.status == "done":
                result = json.loads(db_request.result) if db_request.result else {}
                return ResultResponse(status="done", result=str(result.get("ai_message", "")))

            elif db_request.status == "deployed":
                # ← FIX: Return the result field with deployment details!
                return ResultResponse(
                    status="deployed", 
                    result=db_request.result  # This contains the JSON string with public_ip and console_link
                )

            elif db_request.status in ("in_progress", "deploying"):
                return ResultResponse(status=db_request.status)

            else:
                # Fallback for any other status
                return ResultResponse(status=db_request.status, result=db_request.result)

    except Exception as e:
        log.exception(f"Error fetching result for request {request_id}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
       

class EC2Credentials(BaseModel):
    request_id: int
    aws_access_key: str
    aws_secret_key: str


@router.post("/create-ec2")
def create_ec2_instance(req: EC2Credentials):
    """
    Trigger EC2 creation task for a confirmed request.
    The actual EC2 creation is handled by the worker via Kafka.
    """
    try:
        with SessionLocal() as db:
            db_request = db.query(RequestStatus).filter(RequestStatus.id == req.request_id).first()
            log.info("db_request: ", db_request)

            if not db_request:
                raise HTTPException(status_code=404, detail="Request not found")

            if db_request.status != "done":
                raise HTTPException(status_code=400, detail="Request is not ready for deployment yet")

            if not db_request.result:
                raise HTTPException(status_code=400, detail="No configuration found in result field")

            # Parse AI result JSON stored in DB
            config = json.loads(db_request.result)

            # Construct Kafka message for the worker
            message = {
                "type": "create_ec2",
                "request_id": req.request_id,
                "aws_access_key": req.aws_access_key,
                "aws_secret_key": req.aws_secret_key,
                "region": config.get("region"),
                "instance_type": config.get("instance_type"),
                "docker_image": config.get("docker_image"),
                "key_name": config.get("key_name"),
                "security_group": config.get("security_group", "default"),
                "user_data": config.get("user_data")
            }

            # Send to Kafka topic for the worker
            send_message("ec2_deployments", message)
            log.info(f"Sent EC2 deployment request to Kafka: {message}")

            # Update status
            db_request.status = "deploying"
            db.commit()

            return ResultResponse(status="deploying", result="Deployment request sent successfully")
        
    except Exception as e:
        log.error(f"Error sending EC2 deployment task: {e}")
        db_request = RequestStatus(status="failed")
        # db.add(db_request)
        db.commit()
        return ResultResponse(status="failed", result={e})

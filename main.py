from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import uuid
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
# Serve React app at root
@app.get("/")
async def serve_spa():
    return FileResponse('static/index.html')


# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage using dictionaries
services_db: Dict[str, dict] = {}
incidents_db: Dict[str, dict] = {}

# Pydantic models for request validation
class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str

class Service(ServiceBase):
    id: str
    last_updated: str

class IncidentBase(BaseModel):
    service_id: str
    title: str
    description: str
    status: str

class Incident(IncidentBase):
    id: str
    created_at: str

# Service endpoints
@app.get("/services", response_model=List[Service])
async def get_services():
    return list(services_db.values())

@app.post("/services", response_model=Service)
async def create_service(service: ServiceBase):
    # Check if service with same name exists
    if any(s['name'] == service.name for s in services_db.values()):
        raise HTTPException(
            status_code=400,
            detail="Service with this name already exists"
        )
    
    service_id = str(uuid.uuid4())
    current_time = datetime.now().isoformat()
    
    new_service = {
        "id": service_id,
        "name": service.name,
        "description": service.description,
        "status": service.status,
        "last_updated": current_time
    }
    
    services_db[service_id] = new_service
    return new_service

@app.put("/services/{service_id}", response_model=Service)
async def update_service(service_id: str, service: ServiceBase):
    if service_id not in services_db:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Check if updated name conflicts with another service
    if any(s['name'] == service.name and s['id'] != service_id 
           for s in services_db.values()):
        raise HTTPException(
            status_code=400,
            detail="Service with this name already exists"
        )
    
    current_time = datetime.now().isoformat()
    
    updated_service = {
        "id": service_id,
        "name": service.name,
        "description": service.description,
        "status": service.status,
        "last_updated": current_time
    }
    
    services_db[service_id] = updated_service
    return updated_service

@app.get("/services/{service_id}", response_model=Service)
async def get_service(service_id: str):
    if service_id not in services_db:
        raise HTTPException(status_code=404, detail="Service not found")
    return services_db[service_id]

# Incident endpoints
@app.get("/incidents", response_model=List[Incident])
async def get_incidents():
    return sorted(
        list(incidents_db.values()),
        key=lambda x: x['created_at'],
        reverse=True
    )

@app.post("/incidents", response_model=Incident)
async def create_incident(incident: IncidentBase):
    # Verify service exists
    if incident.service_id not in services_db:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )
    
    incident_id = str(uuid.uuid4())
    current_time = datetime.now().isoformat()
    
    new_incident = {
        "id": incident_id,
        "service_id": incident.service_id,
        "title": incident.title,
        "description": incident.description,
        "status": incident.status,
        "created_at": current_time
    }
    
    incidents_db[incident_id] = new_incident
    
    # Update service status based on incident
    service = services_db[incident.service_id]
    if incident.status in ['investigating', 'identified']:
        service['status'] = 'degraded'
    elif incident.status == 'resolved':
        service['status'] = 'operational'
    service['last_updated'] = current_time
    
    return new_incident

@app.get("/incidents/{incident_id}", response_model=Incident)
async def get_incident(incident_id: str):
    if incident_id not in incidents_db:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incidents_db[incident_id]

# Add some sample data
@app.on_event("startup")
async def startup_event():
    # Add sample services
    service1_id = str(uuid.uuid4())
    service2_id = str(uuid.uuid4())
    current_time = datetime.now().isoformat()
    
    services_db[service1_id] = {
        "id": service1_id,
        "name": "Website",
        "description": "Main company website",
        "status": "operational",
        "last_updated": current_time
    }
    
    services_db[service2_id] = {
        "id": service2_id,
        "name": "API Service",
        "description": "REST API endpoints",
        "status": "operational",
        "last_updated": current_time
    }
    
    # Add sample incident
    incident_id = str(uuid.uuid4())
    incidents_db[incident_id] = {
        "id": incident_id,
        "service_id": service1_id,
        "title": "High Latency Issues",
        "description": "Users experiencing slower response times",
        "status": "resolved",
        "created_at": current_time
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


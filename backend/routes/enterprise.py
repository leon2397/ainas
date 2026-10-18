"""
Enterprise API Routes
V6.0 Phase 4: Enterprise Features API
SSO, Multi-tenant, Audit Analytics
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel

from core.auth import get_current_user

router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])


# ============ Models ============

class AuditReportRequest(BaseModel):
    start_date: str
    end_date: str
    format: str = "json"
    tenant_id: Optional[str] = None


# ============ SSO Routes ============

@router.get("/sso/status")
async def get_sso_status(current_user: Dict = Depends(get_current_user)):
    """Get SSO status"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    from enterprise.sso import get_sso_manager
    manager = get_sso_manager()
    return manager.get_status()


@router.post("/sso/configure")
async def configure_sso(
    provider: str,
    config_data: dict,
    current_user: Dict = Depends(get_current_user)
):
    """Configure SSO"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    from enterprise.sso import get_sso_manager, SSOProvider
    manager = get_sso_manager()
    
    provider_map = {
        "oidc": SSOProvider.OIDC,
        "azure_ad": SSOProvider.AZURE_AD,
        "ldap": SSOProvider.LDAP
    }
    
    sso_provider = provider_map.get(provider)
    if not sso_provider:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    
    if manager.configure(sso_provider, config_data):
        return {"message": "SSO configured", "provider": provider}
    raise HTTPException(status_code=500, detail="SSO config failed")


@router.post("/sso/enable")
async def enable_sso(current_user: Dict = Depends(get_current_user)):
    """Enable SSO"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    from enterprise.sso import get_sso_manager
    manager = get_sso_manager()
    if manager.enable():
        return {"message": "SSO enabled"}
    raise HTTPException(status_code=400, detail="Enable failed")


@router.post("/sso/disable")
async def disable_sso(current_user: Dict = Depends(get_current_user)):
    """Disable SSO"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    from enterprise.sso import get_sso_manager
    manager = get_sso_manager()
    if manager.disable():
        return {"message": "SSO disabled"}
    raise HTTPException(status_code=400, detail="Disable failed")


# ============ Multi-Tenant Routes ============

@router.get("/tenants")
async def list_tenants(
    status: Optional[str] = Query(None),
    current_user: Dict = Depends(get_current_user)
):
    """List tenants"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    from enterprise.multitenant import get_tenant_context, TenantStatus
    context = get_tenant_context()
    status_enum = TenantStatus(status) if status else None
    tenants = context.list_tenants(status_enum)
    
    return {
        "tenants": [t.to_dict() for t in tenants],
        "total": len(tenants)
    }


@router.get("/tenants/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get tenant details"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    from enterprise.multitenant import get_tenant_context
    context = get_tenant_context()
    tenant = context.get_tenant(tenant_id)
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return tenant.to_dict()


@router.post("/tenants")
async def create_tenant(
    name: str,
    slug: str,
    plan: str = "free",
    current_user: Dict = Depends(get_current_user)
):
    """Create tenant"""
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin required")
    
    from enterprise.multitenant import get_tenant_context
    context = get_tenant_context()
    
    if context.get_tenant_by_slug(slug):
        raise HTTPException(status_code=400, detail="Slug already exists")
    
    tenant = context.create_tenant(name, slug, plan)
    return {"message": "Tenant created", "tenant": tenant.to_dict()}


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Delete tenant"""
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin required")
    
    from enterprise.multitenant import get_tenant_context
    context = get_tenant_context()
    
    if context.delete_tenant(tenant_id):
        return {"message": "Tenant deleted"}
    raise HTTPException(status_code=404, detail="Tenant not found")


# ============ Audit Analytics Routes ============

@router.get("/audit/summary")
async def get_audit_summary(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    current_user: Dict = Depends(get_current_user)
):
    """Get audit summary"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    from enterprise.audit_analytics import get_audit_analytics
    analytics = get_audit_analytics()
    
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    
    summary = analytics.get_summary(start, end)
    
    return {
        "total_events": summary.total_events,
        "events_by_level": summary.events_by_level,
        "events_by_category": summary.events_by_category,
        "error_rate": summary.error_rate,
        "security_alerts": summary.security_alerts,
        "top_users": summary.top_users,
        "top_actions": summary.top_actions
    }


@router.get("/audit/alerts")
async def get_security_alerts(
    start_date: str = Query(...),
    end_date: str = Query(...),
    current_user: Dict = Depends(get_current_user)
):
    """Get security alerts"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    from enterprise.audit_analytics import get_audit_analytics
    analytics = get_audit_analytics()
    
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    
    alerts = analytics.detect_anomalies(start, end)
    
    return {
        "alerts": [
            {
                "id": a.id,
                "type": a.type,
                "severity": a.severity,
                "description": a.description,
                "user": a.user,
                "ip_address": a.ip_address,
                "timestamp": a.timestamp.isoformat(),
                "details": a.details
            }
            for a in alerts
        ],
        "total": len(alerts)
    }


@router.post("/audit/report")
async def generate_audit_report(
    data: AuditReportRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Generate audit report"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    from enterprise.audit_analytics import get_audit_analytics
    analytics = get_audit_analytics()
    
    start = datetime.fromisoformat(data.start_date)
    end = datetime.fromisoformat(data.end_date)
    
    report = analytics.generate_report(start, end, data.format)
    return report

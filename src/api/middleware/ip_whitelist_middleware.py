"""
IP Whitelist Middleware for Admin Endpoints

Restricts admin endpoints to whitelisted IP addresses and CIDR ranges.
Supports X-Forwarded-For header for cloud deployments.

Phase 2 - Task Group 5: IP-Based Access Controls
"""

from typing import List, Optional
from ipaddress import ip_address, ip_network, AddressValueError
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import get_settings
from src.observability import get_logger
from src.observability.audit_logger import AuditLogger


logger = get_logger("ip_whitelist_middleware")
settings = get_settings()


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.

    Checks X-Forwarded-For header first (for cloud deployments),
    then falls back to request.client.host.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address as string
    """
    # Check X-Forwarded-For header (cloud deployments)
    # Format: "client, proxy1, proxy2"
    # We take the FIRST IP (leftmost) which is the original client
    x_forwarded_for = request.headers.get("x-forwarded-for")

    if x_forwarded_for:
        # Take first IP from comma-separated list
        client_ip = x_forwarded_for.split(",")[0].strip()
        return client_ip

    # Fallback to direct connection IP
    if request.client and request.client.host:
        return request.client.host

    # Last resort fallback
    return "unknown"


class IPWhitelistMiddleware:
    """
    IP Whitelist Middleware for admin endpoint protection.

    Features:
    - Whitelist admin endpoints to specific IP ranges
    - CIDR notation support (e.g., 192.168.1.0/24)
    - X-Forwarded-For header support for cloud deployments
    - Clear 403 error messages
    - Audit logging for rejected access attempts
    - IPv4 and IPv6 support

    Protected endpoints:
    - /api/v1/admin/*

    Configuration:
    - ADMIN_IP_WHITELIST: Comma-separated IPs and CIDR ranges
    - Empty whitelist = all IPs allowed (IP restriction disabled)
    """

    def __init__(self):
        """Initialize IP whitelist middleware."""
        self.whitelist = self._parse_whitelist()

        if not self.whitelist:
            logger.warning(
                "ADMIN_IP_WHITELIST is empty - IP restriction disabled. "
                "All IPs can access admin endpoints."
            )
        else:
            logger.info(
                f"IP whitelist initialized with {len(self.whitelist)} entries"
            )

    def _parse_whitelist(self) -> List:
        """
        Parse ADMIN_IP_WHITELIST into list of IP addresses and networks.

        Returns:
            List of ip_address and ip_network objects
        """
        whitelist_str = settings.ADMIN_IP_WHITELIST.strip()

        # Empty whitelist = all allowed
        if not whitelist_str:
            return []

        whitelist = []

        for entry in whitelist_str.split(","):
            entry = entry.strip()

            if not entry:
                continue

            try:
                # Check if CIDR notation (contains /)
                if "/" in entry:
                    # Parse as network (CIDR)
                    network = ip_network(entry, strict=False)
                    whitelist.append(network)
                    logger.debug(f"Added CIDR range to whitelist: {entry}")
                else:
                    # Parse as individual IP
                    addr = ip_address(entry)
                    whitelist.append(addr)
                    logger.debug(f"Added IP to whitelist: {entry}")

            except (AddressValueError, ValueError) as e:
                logger.error(
                    f"Invalid IP/CIDR in ADMIN_IP_WHITELIST: {entry} - {str(e)}"
                )
                # Skip invalid entries but continue parsing

        return whitelist

    def is_ip_whitelisted(self, client_ip: str) -> bool:
        """
        Check if client IP is in whitelist.

        Args:
            client_ip: Client IP address string

        Returns:
            True if IP is whitelisted or whitelist is empty, False otherwise
        """
        # Empty whitelist = all allowed
        if not self.whitelist:
            return True

        try:
            # Parse client IP
            client_addr = ip_address(client_ip)

            # Check against whitelist
            for entry in self.whitelist:
                # Check if entry is network (CIDR) or individual IP
                if hasattr(entry, 'num_addresses'):
                    # It's a network (CIDR range)
                    if client_addr in entry:
                        return True
                else:
                    # It's an individual IP
                    if client_addr == entry:
                        return True

            # IP not in whitelist
            return False

        except (AddressValueError, ValueError) as e:
            logger.error(f"Invalid client IP address: {client_ip} - {str(e)}")
            # Reject invalid IPs for security
            return False


# Global middleware instance
_ip_whitelist_middleware: Optional[IPWhitelistMiddleware] = None


def get_ip_whitelist_middleware() -> IPWhitelistMiddleware:
    """
    Get global IPWhitelistMiddleware instance (singleton).

    Returns:
        IPWhitelistMiddleware instance
    """
    global _ip_whitelist_middleware

    if _ip_whitelist_middleware is None:
        _ip_whitelist_middleware = IPWhitelistMiddleware()

    return _ip_whitelist_middleware


async def check_ip_whitelist(request: Request):
    """
    Dependency function to check IP whitelist for admin endpoints.

    Raises:
        HTTPException: 403 if IP is not whitelisted for admin endpoint
    """
    # Only check admin endpoints
    if not request.url.path.startswith("/api/v1/admin"):
        return

    # Get client IP
    client_ip = get_client_ip(request)

    # Get middleware instance
    middleware = get_ip_whitelist_middleware()

    # Check whitelist
    if not middleware.is_ip_whitelisted(client_ip):
        # Get correlation ID for logging
        correlation_id = getattr(request.state, 'correlation_id', None)

        # Log rejected admin access attempt
        await AuditLogger.log_event(
            user_id=None,  # User not authenticated yet
            action="admin_access_denied_ip",
            result="denied",
            resource_type="admin_endpoint",
            resource_id=None,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "endpoint": request.url.path,
                "reason": "IP not in whitelist"
            },
            correlation_id=correlation_id
        )

        logger.warning(
            f"Admin access denied for IP {client_ip} - not in whitelist",
            extra={
                "ip_address": client_ip,
                "endpoint": request.url.path,
                "correlation_id": correlation_id
            }
        )

        # Return 403 with clear error message
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Your IP address is not authorized to access admin endpoints."
        )


class IPWhitelistHTTPMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware wrapper for IP whitelist checking.

    Can be added to FastAPI app with:
        app.add_middleware(IPWhitelistHTTPMiddleware)
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and check IP whitelist for admin endpoints."""
        # Check IP whitelist (raises HTTPException if blocked)
        await check_ip_whitelist(request)

        # Continue to next middleware/endpoint
        response = await call_next(request)
        return response

#!/usr/bin/env python3
"""
MCP Search Server

This MCP server provides tools for searching products using the Particular Audience Search API.
The server exposes three main tools:
- search: Basic product search with optional filters
- filtered_search: Search with required filters
- sorted_search: Search with custom sorting options

Usage:
    python mcp_search_server.py

Configuration:
    Set the following environment variables in a .env file:
    - AUTH_ENDPOINT: Authentication endpoint 
    - SEARCH_API_ENDPOINT: Search API endpoint 
    - CLIENT_ID: Client ID for authentication (required)
    - CLIENT_SHORTCODE: Client shortcode (required)
    - CLIENT_SECRET: Client secret for authentication (required)
    - HOST: Server host (default: 0.0.0.0)
    - PORT: Server port (default: 3000)
    - MESSAGE_PATH: Path for MCP messages (default: /mcp/messages/)
"""

import os
import time
import logging
import json
from typing import Dict, Any, List, Optional
import traceback
from contextlib import asynccontextmanager

import requests
from fastapi import HTTPException
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP, Context

# Import dotenv for environment variable loading
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_search_server")

# Service configuration from environment variables
AUTH_ENDPOINT = os.environ.get("AUTH_ENDPOINT")
SEARCH_API_ENDPOINT = os.environ.get("SEARCH_API_ENDPOINT")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SHORTCODE = os.environ.get("CLIENT_SHORTCODE")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")

# Server configuration from environment variables
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 3000))
MESSAGE_PATH = os.environ.get("MESSAGE_PATH", "/mcp/messages/")

# Token cache
token_cache = {}

# Validate required environment variables
if not CLIENT_ID:
    raise ValueError("CLIENT_ID environment variable is required")
if not CLIENT_SHORTCODE:
    raise ValueError("CLIENT_SHORTCODE environment variable is required")
if not CLIENT_SECRET:
    raise ValueError("CLIENT_SECRET environment variable is required")

# Core models
class FilterSpec(BaseModel):
    field: str
    value: Any
    operator: str = "eq"

class SortSpec(BaseModel):
    field: str
    order: str = "desc"
    type: str = "number"

# Search response models
class PaginationInfo(BaseModel):
    current_page: int
    total_pages: int
    total_results: int
    page_size: int

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    pagination: PaginationInfo
    aggregations: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None
    redirect_url: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None

# Auth function
async def get_auth_token(client_id: str = None) -> str:
    """
    Get authentication token from the auth service.
    
    Parameters:
    - client_id: Optional client ID, defaults to CLIENT_ID from environment
    
    Returns:
    - Access token string
    
    Raises:
    - HTTPException: If authentication fails
    """
    client_id = client_id or CLIENT_ID
    client_secret = CLIENT_SECRET
    
    if not client_id:
        raise HTTPException(status_code=400, detail="Client ID is required")
    
    current_time = time.time()
    
    # Use cached token if valid
    if client_id in token_cache and token_cache[client_id].get("expires_at", 0) > current_time:
        return token_cache[client_id]["access_token"]
    
    # Fetch new token
    logger.info(f"Fetching new auth token for client {client_id}")
    try:
        form_data = {
            'client_id': client_id,
            'grant_type': 'client_credentials'
        }
        
        if client_secret:
            form_data['client_secret'] = client_secret
        
        response = requests.post(
            AUTH_ENDPOINT,
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)
        token_type = data.get("token_type", "Bearer")
        
        # Cache token with 5-min safety margin
        token_cache[client_id] = {
            "access_token": access_token,
            "token_type": token_type,
            "expires_at": current_time + expires_in - 300
        }
        
        return access_token
        
    except Exception as e:
        logger.error(f"Auth token request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get auth token: {e}")

# Search API function
async def perform_search(
    query: str,
    start: int = 0,
    size: int = 20,
    filters: List[FilterSpec] = None,
    sort_fields: List[SortSpec] = None
) -> SearchResponse:
    """
    Perform product search using the Search API.
    
    Parameters:
    - query: Search query string
    - start: Starting position for pagination (0-based)
    - size: Number of results to return per page
    - filters: Optional list of FilterSpec objects for narrowing results
    - sort_fields: Optional list of SortSpec objects for custom sorting
    
    Returns:
    - SearchResponse object containing search results and metadata
    
    Raises:
    - HTTPException: If search operation fails
    """
    logger.info(f"Searching for '{query}' on website {CLIENT_ID}")
    
    # Generate scope dictionary from filters
    scope = {}
    if filters:
        for filter_spec in filters:
            field = filter_spec.field
            value = filter_spec.value
            operator = filter_spec.operator
            # Handle different operator types
            if operator == "eq":
                # Direct mapping for equality filters
                scope[field] = value
            elif operator == "range":
                # For range filters, create or update min/max values
                if field not in scope:
                    scope[field] = {}                
                # Handle range as dictionary with min/max keys
                if isinstance(value, dict):
                    if "min" in value:
                        scope[field]["min"] = value["min"]
                    if "max" in value:
                        scope[field]["max"] = value["max"]
                # Handle individual gte/lte operators
                elif operator == "gte":
                    scope[field]["min"] = value
                elif operator == "lte":
                    scope[field]["max"] = value
        logger.debug(f"Generated scope from filters: {scope}")

    if sort_fields:
        sort_fields_list = [{sort_field.field: {"order": sort_field.order, "type": sort_field.type}} for sort_field in sort_fields]
        logger.info(f"Sort fields: {sort_fields_list}")
    else:
        sort_fields_list = None
    
    # Build search request based on sample-body.json format
    search_request = {
        "q": query,
        "website_id": str(CLIENT_ID).lower(),
        "client": CLIENT_SHORTCODE,
        "size": size,
        "start": start,
        "scope": scope
    }
    if sort_fields_list:
        search_request["sort_fields"] = sort_fields_list
    
    # Call Search API
    start_time = time.time()
    max_retries = 3
    for attempt in range(max_retries):
        try:
            token = await get_auth_token(client_id=CLIENT_ID)
            logger.info(f"Sending search request (attempt {attempt+1}): {json.dumps(search_request)[:500]}...")
            response = requests.post(
                SEARCH_API_ENDPOINT,
                json=search_request,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=15
            )
            if response.status_code == 401:
                logger.warning(f"Received 401 Unauthorized from search API (attempt {attempt+1}). Invalidating token cache and retrying...")
                # Invalidate token cache for this client
                if CLIENT_ID in token_cache:
                    del token_cache[CLIENT_ID]
                if attempt < max_retries - 1:
                    continue  # Try again with a new token
                else:
                    response.raise_for_status()  # Will raise HTTPError
            response.raise_for_status()
            data = response.json()
            payload = data.get("payload")
            logger.info(f"Search API response: {payload}")
            execution_time_ms = int((time.time() - start_time) * 1000)
            total_results = payload.get("total_results", 0)
            page_size = size
            total_pages = max(1, (total_results + page_size - 1) // page_size)
            current_page = start // page_size + 1
            pagination = PaginationInfo(
                current_page=current_page,
                total_pages=total_pages,
                total_results=total_results,
                page_size=page_size
            )
            return SearchResponse(
                results=payload.get("results", []),
                pagination=pagination,
                aggregations=payload.get("aggregations"),
                suggestions=payload.get("suggestions", {}).get("fuzzy_suggestions", []),
                redirect_url=payload.get("redirect_url"),
                execution_time_ms=execution_time_ms
            )
        except requests.HTTPError as e:
            if hasattr(e.response, 'status_code') and e.response.status_code == 401:
                logger.warning(f"HTTPError 401 on attempt {attempt+1}: {e}")
                if CLIENT_ID in token_cache:
                    del token_cache[CLIENT_ID]
                if attempt < max_retries - 1:
                    continue
            logger.error(f"Search failed with HTTPError: {e}")
            raise HTTPException(status_code=500, detail=f"Search operation failed: {e}")
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise HTTPException(status_code=500, detail=f"Search operation failed: {e}")
    # If we exit the loop, all retries failed
    raise HTTPException(status_code=500, detail="Search operation failed after multiple retries due to authentication errors.")

# Create FastMCP server with SSE settings
mcp_server = FastMCP(
    name="MCP Search Server",
    host=HOST,
    port=PORT,
    message_path=MESSAGE_PATH,
    debug=True,
    log_level="INFO"
)

# Register MCP tools
@mcp_server.tool("search")
async def search(
    query: str, 
    start: int = 0, 
    size: int = 20,
    filters: List[FilterSpec] = None,
    ctx: Context = None
) -> SearchResponse:
    """
    Execute a product search with optional filters.
    
    Parameters:
    - query: The search query text (e.g., "blue shirts", "tires", "dress")
    - start: Starting position for pagination (0-based index)
    - size: Number of results to return per page
    - filters: Optional list of filters to narrow search results
      Format: [{"field": "color", "value": "blue", "operator": "eq"}]
      Supported operators: 
        - "eq" (equals): {"field": "color", "value": "blue", "operator": "eq"}
        - "range" (for min/max values): {"field": "price", "value": {"min": 20, "max": 100}, "operator": "range"}
    
    Returns:
    - SearchResponse object containing results, pagination info, and optional metadata
      
    Authentication is handled automatically using environment variables.
    """
    # Log the search request
    if ctx:
        await ctx.info(f"Searching for '{query}' on website: {CLIENT_ID}")
    
    return await perform_search(
        query=query,
        start=start,
        size=size,
        filters=filters
    )

# Add specialized search tool
@mcp_server.tool("filtered_search")
async def filtered_search(
    query: str,
    filters: List[FilterSpec],
    start: int = 0,
    size: int = 20,
    ctx: Context = None
) -> SearchResponse:
    """
    Search products with specific filters.
    
    Parameters:
    - query: The search query text (can be empty if using filters only)
    - filters: List of filters to narrow search results
      Format: [{"field": "field_name", "value": value, "operator": "eq"}]
      Examples:
        - Category filter: {"field": "product_category", "value": "Clothing > Shirts", "operator": "eq"}
        - Color filter: {"field": "color", "value": "blue", "operator": "eq"}
        - Price range: {"field": "price", "value": {"min": 20, "max": 100}, "operator": "range"}
    - start: Starting position for pagination (0-based index)
    - size: Number of results to return per page
    
    Returns:
    - SearchResponse object containing results, pagination info, and optional metadata
    """
    if ctx:
        await ctx.info(f"Filtered search for '{query}' with filters: {filters}")
    
    return await perform_search(
        query=query,
        start=start,
        size=size,
        filters=filters
    )

# Add sorted search tool
@mcp_server.tool("sorted_search")
async def sorted_search(
    query: str,
    sort: List[SortSpec],
    start: int = 0,
    size: int = 20,
    filters: List[FilterSpec] = None,
    ctx: Context = None
) -> SearchResponse:
    """
    Search products with custom sorting options.
    
    Parameters:
    - query: The search query text (can be empty if using filters only)
    - sort: List of sort specifications to order results
      Format: [{"field": "field_name", "order": "asc|desc", "type": "number|text|date"}]
      Examples:
        - Price (lowest first): {"field": "price", "order": "asc", "type": "number"}
        - Popularity (highest first): {"field": "popularity", "order": "desc", "type": "number"}
        - Name (alphabetical): {"field": "title", "order": "asc", "type": "text"}
    - start: Starting position for pagination (0-based index)
    - size: Number of results to return per page
    - filters: Optional list of filters to narrow search results
      Same format as the 'filters' parameter in the search and filtered_search tools
    
    Returns:
    - SearchResponse object containing results, pagination info, and optional metadata
    """
    if ctx:
        await ctx.info(f"Sorted search for '{query}' with sort: {sort}")
    
    return await perform_search(
        query=query,
        start=start,
        size=size,
        filters=filters or [],
        sort_fields=sort
    )


# Register resources
@mcp_server.resource(
    uri="resource://search/docs",
    name="Search Documentation",
    description="Documentation for the product search API",
    mime_type="application/json",
)
async def search_docs_resource() -> str:
    """
    Provides comprehensive documentation about the search tools with parameter descriptions and examples.
    This resource includes details on all available search tools, parameter formats, and usage examples.
    
    Returns:
    - JSON string containing search API documentation
    """
    
    docs = {
        "name": "search",
        "description": "Execute a product search against the Search API with optional filters",
        "parameters": {
            "query": {
                "type": "string",
                "description": "The search query string (e.g., 'blue shirts', 'tires')"
            },
            "start": {
                "type": "integer",
                "description": "Starting position for results (0-based)",
                "default": 0
            },
            "size": {
                "type": "integer",
                "description": "Number of results per page",
                "default": 20
            },
            "filters": {
                "type": "array",
                "description": "Optional filters to narrow search results",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {
                            "type": "string", 
                            "description": "Field name to filter on (e.g., 'color', 'price', 'product_category')"
                        },
                        "value": {
                            "type": ["string", "number", "object"],
                            "description": "Filter value - can be string/number for equality or object with min/max for ranges" 
                        },
                        "operator": {
                            "type": "string",
                            "enum": ["eq", "range", "gte", "lte"],
                            "description": "Filter operator - 'eq' for equality, 'range' for min/max values",
                            "default": "eq"
                        }
                    },
                    "required": ["field", "value"]
                }
            }
        },
        "tools": {
            "search": {
                "description": "Basic search with optional filters",
                "parameters": ["query", "start", "size", "filters"]
            },
            "filtered_search": {
                "description": "Search with mandatory filters",
                "parameters": ["query", "filters", "start", "size"]
            },
            "sorted_search": {
                "description": "Search with custom sorting options",
                "parameters": ["query", "sort", "start", "size", "filters"]
            }
        },
        "sorting": {
            "description": "Sorting specifications for sorted_search tool",
            "sort_spec": {
                "field": {
                    "type": "string",
                    "description": "Field name to sort by (e.g., 'price', 'popularity')"
                },
                "order": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "description": "Sort order - 'asc' for ascending, 'desc' for descending",
                    "default": "desc"
                },
                "type": {
                    "type": "string",
                    "enum": ["number", "text", "date"],
                    "description": "Type of the field being sorted",
                    "default": "number"
                }
            },
            "sort_examples": [
                {
                    "description": "Sort by price (lowest first)",
                    "sort": {"field": "price", "order": "asc", "type": "number"}
                },
                {
                    "description": "Sort by popularity (highest first)",
                    "sort": {"field": "popularity", "order": "desc", "type": "number"}
                },
                {
                    "description": "Sort by name (alphabetical)",
                    "sort": {"field": "title", "order": "asc", "type": "text"}
                }
            ]
        },
        "internal_configuration": {
            "website_id": CLIENT_ID,
            "client_shortcode": CLIENT_SHORTCODE
        },
        "filter_examples": [
            {
                "description": "Filter by color (equality)",
                "filter": {"field": "color", "value": "blue", "operator": "eq"}
            },
            {
                "description": "Filter by category (equality)",
                "filter": {"field": "product_category", "value": "Clothing > Shirts", "operator": "eq"}
            },
            {
                "description": "Filter by price range",
                "filter": {"field": "price", "value": {"min": 20, "max": 100}, "operator": "range"}
            }
        ],
        "search_examples": [
            {
                "description": "Basic search",
                "params": {
                    "query": "dress",
                    "start": 0,
                    "size": 20
                }
            },
            {
                "description": "Search for tyres with pagination",
                "params": {
                    "query": "tyres tires wheels",
                    "start": 10,
                    "size": 15
                }
            },
            {
                "description": "Search with color filter",
                "params": {
                    "query": "shirts",
                    "filters": [
                        {"field": "color", "value": "blue", "operator": "eq"}
                    ]
                }
            },
            {
                "description": "Category search with price range",
                "params": {
                    "query": "",
                    "filters": [
                        {"field": "product_category", "value": "Clothing > Shirts", "operator": "eq"},
                        {"field": "price", "value": {"min": 20, "max": 100}, "operator": "range"}
                    ]
                }
            }
        ]
    }
    return json.dumps(docs, indent=2)

@mcp_server.resource(
    uri="resource://search/response-schema",
    name="Search Response Schema",
    description="Schema describing the format of search response",
    mime_type="application/json",
)
async def search_response_schema_resource() -> str:
    """
    Provides the JSON schema for search response objects.
    This resource documents the structure of responses returned by all search tools.
    
    Returns:
    - JSON string containing the search response schema
    """
    
    schema = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "description": "List of product results",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": "Product properties vary based on search results with no enforced schema"
                    }
                }
            },
            "pagination": {
                "type": "object",
                "properties": {
                    "current_page": {"type": "integer", "description": "Current page number"},
                    "total_pages": {"type": "integer", "description": "Total number of pages"},
                    "total_results": {"type": "integer", "description": "Total number of results"},
                    "page_size": {"type": "integer", "description": "Number of results per page"}
                }
            },
            "aggregations": {
                "type": "object",
                "description": "Aggregation information for filtering"
            },
            "suggestions": {
                "type": "array",
                "description": "Search suggestions if query has few results",
                "items": {
                    "type": "string"
                }
            },
            "redirect_url": {
                "type": "object",
                "description": "URL information for redirects on specific queries"
            },
            "execution_time_ms": {
                "type": "integer",
                "description": "Time taken to execute the search in milliseconds"
            }
        }
    }
    
    return json.dumps(schema, indent=2)

@mcp_server.resource(
    uri="resource://search/examples",
    name="Search Examples",
    description="Examples of different search patterns",
    mime_type="application/json",
)
async def search_examples_resource() -> str:
    """
    Provides ready-to-use example search requests for common use cases.
    This resource includes complete examples for all search tools with various parameter combinations.
    
    Returns:
    - JSON string containing practical search examples
    """
    examples = {
        "basic_search": {
            "description": "Basic product search",
            "tool": "search",
            "parameters": {
                "query": "blue shirt",
                "start": 0,
                "size": 20
            }
        },
        "filtered_category_search": {
            "description": "Search for products in a specific category",
            "tool": "filtered_search",
            "parameters": {
                "query": "",
                "filters": [
                    {"field": "product_category", "value": "Clothing > Shirts", "operator": "eq"}
                ],
                "start": 0,
                "size": 20
            }
        },
        "price_range_search": {
            "description": "Search for products within a price range",
            "tool": "filtered_search",
            "parameters": {
                "query": "dress",
                "filters": [
                    {"field": "price", "value": {"min": 29.99, "max": 99.99}, "operator": "range"}
                ],
                "start": 0,
                "size": 20
            }
        },
        "tyres_search": {
            "description": "Search for tyres/tires with multiple filters",
            "tool": "filtered_search",
            "parameters": {
                "query": "tyres tires wheels",
                "filters": [
                    {"field": "product_category", "value": "Automotive > Tires", "operator": "eq"},
                    {"field": "size", "value": "205/55R16", "operator": "eq"}
                ],
                "start": 0,
                "size": 15
            }
        },
        "sorted_price_search": {
            "description": "Search for products sorted by price (lowest first)",
            "tool": "sorted_search",
            "parameters": {
                "query": "laptop",
                "sort": [
                    {"field": "price", "order": "asc", "type": "number"}
                ],
                "start": 0,
                "size": 20
            }
        },
        "sorted_filtered_search": {
            "description": "Search with both filters and custom sorting",
            "tool": "sorted_search",
            "parameters": {
                "query": "sneakers",
                "sort": [
                    {"field": "popularity", "order": "desc", "type": "number"}
                ],
                "filters": [
                    {"field": "brand", "value": "Nike", "operator": "eq"},
                    {"field": "price", "value": {"min": 50, "max": 150}, "operator": "range"}
                ],
                "start": 0,
                "size": 20
            }
        },
        "multiple_sort_fields": {
            "description": "Search with multiple sort fields (primary and secondary ordering)",
            "tool": "sorted_search",
            "parameters": {
                "query": "shoes",
                "sort": [
                    {"field": "price", "order": "asc", "type": "number"},
                    {"field": "rating", "order": "desc", "type": "number"}
                ],
                "start": 0,
                "size": 20
            }
        }
    }
    return json.dumps(examples, indent=2)

# Add a simple lifespan function to handle server startup
@asynccontextmanager
async def server_lifespan(app: FastMCP):
    """
    Lifespan handler for the FastMCP server to manage startup and shutdown operations.
    
    On startup:
    - Verifies the authentication service is working
    - Pre-fetches a token for faster initial requests
    
    Parameters:
    - app: The FastMCP server instance
    """
    logger.info("Server starting up")
    
    # Pre-fetch a token to verify auth service is working
    try:
        await get_auth_token()
        logger.info("Auth service verified successfully")
    except Exception as e:
        logger.error(f"Auth service check failed: {e}")
    
    yield  # Server runs
    
    logger.info("Server shutting down")

# Assign lifespan
mcp_server.settings.lifespan = server_lifespan

# Main entry point: run via SSE
if __name__ == "__main__":
    logger.info(f"Starting MCP Search Server on http://{HOST}:{PORT}")
    mcp_server.run() 
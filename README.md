# Adaptive Transformer Search MCP Server

This MCP (Model Context Protocol) server provides access to [Particular Audience's Adaptive Transformer Search (ATS)](https://particularaudience.com/search/) - an AI-powered eCommerce search solution that harnesses the power of Large Language Models to understand customer search intent and eliminate zero search results.

## What is Adaptive Transformer Search?

Adaptive Transformer Search (ATS) represents a revolutionary leap beyond traditional keyword-based search and basic catalog browsing. Unlike conventional search that relies on exact token matching, ATS uses the same transformer technology behind OpenAI's GPT and Google's translation systems to understand the semantic meaning and intent behind customer queries. This enables the system to understand the difference between "chocolate milk" and "milk chocolate," handle natural language queries, and provide relevant results even when exact keyword matches don't exist.

### Benefits Over Traditional Search

ATS addresses the $300 billion search problem in eCommerce by eliminating the need for manual synonym rules, redirects, and ongoing search maintenance. Traditional keyword search requires extensive manual configuration and often fails when customers use natural language or misspellings. ATS automatically understands customer intent, reducing zero search results by up to 70% while increasing search revenue by 20% and eliminating 99% of manual search management work.

### Merchandising Control for Retailers

One of the key advantages of ATS is the ability for retailers to maintain merchandising control over how LLMs interpret and rank search results. Retailers can boost specific products, brands, or categories within search results based on promotional campaigns, inventory levels, or margin objectives. This ensures that while the AI provides intelligent, relevant results, retailers retain the ability to influence discovery in alignment with their business goals.

### Enabling Retail Media in LLM Discovery

ATS seamlessly integrates retail media capabilities into the search experience, allowing sponsored products to be intelligently woven into search results. This creates new revenue opportunities for retailers while maintaining relevance and user experience. The system can prioritize sponsored products when they genuinely match customer intent, creating a win-win scenario for retailers, advertisers, and customers.

## Features

This MCP server provides three main search tools that interface with the Particular Audience Search API, giving you access to all ATS capabilities:

- **Search**: Adaptive Transformer Search with natural language understanding, optional filters, and pagination
- **Filtered Search**: ATS search with required filters to narrow results while maintaining semantic understanding
- **Sorted Search**: ATS search with custom sorting options (price, popularity, etc.) and merchandising control

The server handles authentication automatically and provides comprehensive error handling and retry logic. All searches benefit from ATS's transformer technology, eliminating zero search results and providing intelligent, relevant product matches.

## ATS Capabilities Available Through This MCP Server

When you use this MCP server, you get access to all Adaptive Transformer Search capabilities:

### Natural Language Understanding
- Understands semantic meaning behind queries (e.g., "chocolate milk" vs "milk chocolate")
- Handles natural language queries like "comfortable shoes for walking under $100"
- Processes misspellings and variations automatically

### Intelligent Search Results
- Eliminates zero search results by up to 70%
- Provides relevant results even when exact keyword matches don't exist
- Understands product relationships and context

### Merchandising Control
- Boost specific products, brands, or categories in search results
- Control ranking based on promotional campaigns, inventory, or margin objectives
- Maintain business control while leveraging AI intelligence

### Retail Media Integration
- Seamlessly integrate sponsored products into search results
- Maintain relevance while creating revenue opportunities
- Intelligent placement of retail media content

### Zero Manual Maintenance
- No need for synonym rules, redirects, or manual search configuration
- Automatically adapts to changes in user behavior and catalog data
- Reduces manual search management work by 99%

## Connecting to Onsite LLM/Chat Agents

This MCP server enables seamless integration of ATS into your existing LLM-powered chat agents and discovery experiences. By connecting this server to your onsite AI assistant, customers can now search your product catalog using natural language through chat interfaces. The AI can understand complex queries like "show me comfortable shoes for walking that are under $100" and return relevant results, even if the customer doesn't use exact product names or categories. This creates a more intuitive, conversational shopping experience that feels natural to customers while driving higher conversion rates.

## Prerequisites

- Python 3.11 or higher
- [UV](https://github.com/astral-sh/uv) package manager
- Docker (optional, for containerized deployment)

## Configuration

Create a `.env` file with the following content (or set environment variables directly):

```
# Authentication settings
AUTH_ENDPOINT=AUTHENTICATION_ENDPOINT
SEARCH_API_ENDPOINT=SEARCH_ENDPOINT
CLIENT_ID=your_client_id_here
CLIENT_SHORTCODE=your_client_shortcode_here
CLIENT_SECRET=your_client_secret_here

# Server settings
HOST=0.0.0.0
PORT=3000
MESSAGE_PATH=/mcp/messages/
```

## Deployment Options

### Option 1: Direct UV Run

Run directly with UV (assuming UV is pre-installed):

```bash
# Simple run
uv run mcp_search_server.py

# Or with inline environment variables
AUTH_ENDPOINT=AUTHENTICATION_ENDPOINT \
SEARCH_API_ENDPOINT=SEARCH_ENDPOINT \
CLIENT_ID=your_id \
CLIENT_SHORTCODE=your_code \
CLIENT_SECRET=your_secret \
uv run mcp_search_server.py
```

### Option 2: Docker Deployment

Build and run using Docker:

```bash
# Build
docker build -t mcp-search-server .

# Run with env file
docker run -p 3000:3000 --env-file .env mcp-search-server

# Or run with inline environment variables
docker run -p 3000:3000 \
  -e AUTH_ENDPOINT=AUTHENTICATION_ENDPOINT \
  -e SEARCH_API_ENDPOINT=SEARCH_ENDPOINT \
  -e CLIENT_ID=your_id \
  -e CLIENT_SHORTCODE=your_code \
  -e CLIENT_SECRET=your_secret \
  mcp-search-server
```

## MCP Client Configuration

You can configure AI assistants like Claude Desktop or VS Code Copilot to use this MCP Search Server.

### Integration with Claude Desktop

To configure Claude Desktop:

1. Specify your API credentials
2. Retrieve your `uv` command full path (e.g. `which uv`)
3. Edit the Claude Desktop configuration file (location varies by OS:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`)

#### Local UV Configuration

```json
{
  "mcpServers": {
    "uv-search-server": {
      "command": "/path/to/your/uv",
      "args": [
        "--directory",
        "/path/to/your/project/directory",
        "run",
        "mcp_search_server.py"
      ],
      "env": {
        "AUTH_ENDPOINT": "AUTHENTICATION_ENDPOINT",
        "SEARCH_API_ENDPOINT": "SEARCH_ENDPOINT",
        "CLIENT_ID": "your_client_id",
        "CLIENT_SHORTCODE": "your_client_shortcode",
        "CLIENT_SECRET": "your_client_secret",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

#### Docker Configuration

```json
{
  "mcpServers": {
    "uv-search-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--name",
        "mcp-search-server",
        "-p",
        "3000:3000",
        "-i",
        "-e", "AUTH_ENDPOINT",
        "-e", "SEARCH_API_ENDPOINT",
        "-e", "CLIENT_ID",
        "-e", "CLIENT_SHORTCODE",
        "-e", "CLIENT_SECRET",
        "-e", "PYTHONUNBUFFERED",
        "mcp-search-server"
      ],
      "env": {
        "AUTH_ENDPOINT": "AUTHENTICATION_ENDPOINT",
        "SEARCH_API_ENDPOINT": "SEARCH_ENDPOINT",
        "CLIENT_ID": "your_client_id",
        "CLIENT_SHORTCODE": "your_client_shortcode",
        "CLIENT_SECRET": "your_client_secret",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### Integration with VS Code

For VS Code integration:

1. Enable agent mode tools in your `settings.json`:
   ```json
   {
     "chat.agent.enabled": true
   }
   ```

2. Configure the Search Server in your `.vscode/mcp.json` or in VS Code's `settings.json`:
   ```json
   // Example .vscode/mcp.json
   {
     "servers": {
       "uv-search-server": {
         "type": "stdio",
         "command": "/path/to/your/uv",
         "args": [
           "--directory",
           "/path/to/your/project/directory",
           "run",
           "mcp_search_server.py"
         ],
         "env": {
           "AUTH_ENDPOINT": "AUTHENTICATION_ENDPOINT",
           "SEARCH_API_ENDPOINT": "SEARCH_ENDPOINT",
           "CLIENT_ID": "your_client_id",
           "CLIENT_SHORTCODE": "your_client_shortcode",
           "CLIENT_SECRET": "your_client_secret",
           "PYTHONUNBUFFERED": "1"
         }
       }
     }
   }
   ```

### Troubleshooting

For Claude Desktop, you can check logs with:
```bash
tail -f ~/Library/Logs/Claude/mcp-server-uv-search-server.log
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 
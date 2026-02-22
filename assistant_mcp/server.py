from fastmcp import FastMCP
from app.tools import check_availability_tool, send_notification_tool, search_flights_tool, show_calendar_tool, web_search_tool

mcp = FastMCP("personal-assistant-mcp")

@mcp.tool(name="check_availability_tool")
def check_availability(date: str, start_time: str, end_time: str, urgent: bool=False):
    return check_availability_tool.func(date, start_time, end_time, urgent)

@mcp.tool(name="send_notification_tool")
def send_notification(message: str):
    return send_notification_tool.func(message)

@mcp.tool(name="search_flights_tool")
def flights(origin: str, destination: str, date: str):
    return search_flights_tool.func(origin, destination, date)

@mcp.tool(name="show_calendar_tool")
def show_calendar(date: str):
    return show_calendar_tool.func(date)

@mcp.tool(name="web_search_tool")
def web_search(query: str):
    return web_search_tool.func(query)

if __name__ == "__main__":
    mcp.run(transport="http", port=8002)


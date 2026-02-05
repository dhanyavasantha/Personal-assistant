from fastmcp import FastMCP
from app.tools import check_availability_tool, send_notification_tool

mcp = FastMCP("personal-assistant-mcp")

@mcp.tool(name="check_availability_tool")
def check_availability(date: str, start_time: str, end_time: str, urgent: bool=False):
    return check_availability_tool.func(date, start_time, end_time, urgent)

@mcp.tool(name="send_notification_tool")
def send_notification(message: str):
    return send_notification_tool.func(message)

if __name__ == "__main__":
    mcp.run(transport="http", port=8002)


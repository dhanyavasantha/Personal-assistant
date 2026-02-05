from fastmcp import Client

# Port must match server
mcp_client = Client("http://localhost:8002/mcp")


async def mcp_check_availability(date, start, end, urgent=False):
    async with mcp_client:
        return await mcp_client.call_tool(
            "check_availability_tool",
            {
                "date": date,
                "start_time": start,
                "end_time": end,
                "urgent": urgent
            }
        )


async def mcp_send_notification(message):
    async with mcp_client:
        return await mcp_client.call_tool(
            "send_notification_tool",
            {
                "message": message
            }
        )


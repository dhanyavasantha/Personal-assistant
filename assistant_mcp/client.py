from fastmcp import Client

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
            {"message": message}
        )

async def mcp_search_flights(origin, destination, date):
    async with mcp_client:
        return await mcp_client.call_tool(
            "search_flights_tool",
            {
                "origin": origin,
                "destination": destination,
                "date": date
            }
        )

async def mcp_show_calendar(date: str):
    async with mcp_client:
        return await mcp_client.call_tool(
            "show_calendar_tool",
            {
                "date": date
            }
        )

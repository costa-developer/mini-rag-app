from mcp.server.fastmcp import FastMCP
from datetime import datetime
import pytz

# Create the MCP server with a name
mcp = FastMCP("Football Time Server")


@mcp.tool()
def get_current_time(timezone: str = "UTC") -> str:
    """
    Get the current date and time.
    
    Args:
        timezone: Timezone name e.g. 'UTC', 'Europe/London', 'America/New_York'
    
    Returns:
        Current date and time as a string
    """
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        return now.strftime(f"%Y-%m-%d %H:%M:%S {timezone}")
    except Exception:
        now = datetime.utcnow()
        return now.strftime("%Y-%m-%d %H:%M:%S UTC")


@mcp.tool()
def get_match_duration(kickoff_time: str) -> str:
    """
    Calculate how long a football match has been going.
    
    Args:
        kickoff_time: Kickoff time in format 'HH:MM' (24 hour, today)
    
    Returns:
        How many minutes the match has been going
    """
    try:
        now = datetime.now()
        kickoff = datetime.strptime(kickoff_time, "%H:%M")
        kickoff = kickoff.replace(
            year=now.year,
            month=now.month,
            day=now.day
        )
        diff = now - kickoff
        minutes = int(diff.total_seconds() / 60)

        if minutes < 0:
            return "Match has not started yet."
        elif minutes <= 45:
            return f"First half - minute {minutes}"
        elif minutes <= 60:
            return f"Half time / early second half - minute {minutes}"
        elif minutes <= 90:
            return f"Second half - minute {minutes}"
        elif minutes <= 105:
            return f"First period of extra time - minute {minutes}"
        elif minutes <= 120:
            return f"Second period of extra time - minute {minutes}"
        else:
            return f"Match finished - lasted {minutes} minutes total"
    except Exception as e:
        return f"Error calculating duration: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")